from __future__ import annotations

from datetime import date, time

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.client import AIClient
from src.ai.intent import classify_and_respond
from src.bot.keyboards import (
    confirm_keyboard,
    date_keyboard,
    party_size_keyboard,
    time_slots_keyboard,
)
from src.bot.states import BookingStates
from src.config import settings
from src.db import dao

router = Router()

WELCOME_MESSAGE = (
    "Welcome to Lobster Cave! I'm ClawBot, your AI concierge.\n\n"
    "I can help you:\n"
    "- Book a table\n"
    "- Answer questions about our restaurant\n"
    "- Manage your reservations\n\n"
    "Just send me a message in any language!"
)


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(WELCOME_MESSAGE)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "How to use ClawBot:\n\n"
        'Send a message like "Table for 4 tonight at 8pm"\n'
        'Or just say "I want to book a table"\n\n'
        "Commands:\n"
        "/start - Start over\n"
        "/help - Show this help\n"
        "/mybookings - View your bookings\n"
        "/cancel - Cancel a booking"
    )


@router.message(Command("mybookings"))
async def cmd_my_bookings(
    message: Message, session: AsyncSession
) -> None:
    bookings = await dao.get_bookings_by_telegram_id(
        session, message.from_user.id
    )
    if not bookings:
        await message.answer("You have no active bookings.")
        return

    lines = ["Your active bookings:\n"]
    for b in bookings:
        slot_label = b.time_slot.label if b.time_slot else "?"
        lines.append(
            f"#{b.id} | {b.date.strftime('%d %b')} {slot_label} | "
            f"Party of {b.party_size} | Status: {b.status}"
        )
    await message.answer("\n".join(lines))


@router.message(Command("cancel"))
async def cmd_cancel(
    message: Message, session: AsyncSession
) -> None:
    bookings = await dao.get_bookings_by_telegram_id(
        session, message.from_user.id
    )
    if not bookings:
        await message.answer("You have no active bookings to cancel.")
        return

    booking = bookings[0]
    await dao.cancel_booking(session, booking.id)
    slot_label = booking.time_slot.label if booking.time_slot else "?"
    await message.answer(
        f"Booking #{booking.id} cancelled.\n"
        f"({booking.date.strftime('%d %b')} {slot_label}, party of {booking.party_size})"
    )


@router.message(~F.text)
async def non_text_handler(message: Message) -> None:
    await message.answer("I can only understand text messages. Please type your request!")


@router.message()
async def catch_all_message(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    ai_client: AIClient,
) -> None:
    current_state = await state.get_state()
    if current_state is not None:
        return

    text = message.text or ""
    logger.info(f"Message from {message.from_user.id}: {text[:100]}")

    # Build FAQ context for the AI (loaded once, could be cached)
    faqs = await dao.get_faq_responses(session, restaurant_id=1)
    faq_data = "FAQ:\n" + "\n".join(f"- {f.answer}" for f in faqs) if faqs else ""

    # SINGLE AI call: classify intent + generate response
    result = await classify_and_respond(ai_client, text, faq_data=faq_data)
    logger.info(f"Intent: {result.intent}, lang: {result.detected_language}")

    if result.intent == "new_booking":
        await _handle_new_booking(message, state, session, result)
    elif result.intent == "cancel_booking":
        await cmd_cancel(message, session)
    elif result.intent == "check_status":
        await cmd_my_bookings(message, session)
    else:
        # FAQ, greeting, other — AI already generated the response
        if result.response:
            await message.answer(result.response)
        else:
            await message.answer("I can help you book a table or answer questions about Lobster Cave!")


async def _handle_new_booking(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    result,
) -> None:
    existing = await dao.get_bookings_by_telegram_id(session, message.from_user.id)
    if len(existing) >= settings.MAX_BOOKINGS_PER_USER:
        await message.answer(
            f"You already have {len(existing)} active booking(s). "
            f"Please cancel one before making a new reservation.\n"
            f"Use /mybookings to view or /cancel to cancel."
        )
        return

    state_data = {"language": result.detected_language}

    if result.has_all_booking_entities:
        state_data["date"] = result.date
        state_data["time"] = result.time
        state_data["party_size"] = result.party_size
        if result.special_requests:
            state_data["special_requests"] = result.special_requests

        slots = await dao.get_time_slots(session, restaurant_id=1)
        matched_slot = _match_time_to_slot(result.time, slots)
        if matched_slot:
            state_data["time_slot_id"] = matched_slot.id
            tables = await dao.get_available_tables(
                session, 1, date.fromisoformat(result.date),
                matched_slot.id, result.party_size,
            )
            if tables:
                state_data["table_id"] = tables[0].id
                await state.set_data(state_data)
                await state.set_state(BookingStates.awaiting_confirmation)
                summary = (
                    f"Booking summary:\n"
                    f"Date: {result.date}\n"
                    f"Time: {matched_slot.label}\n"
                    f"Party size: {result.party_size}\n"
                )
                if result.special_requests:
                    summary += f"Requests: {result.special_requests}\n"
                await message.answer(summary, reply_markup=confirm_keyboard())
                return
            else:
                await message.answer(
                    "Sorry, no tables available for that time. Let me show you other options."
                )

    # Step-by-step flow
    if result.date:
        state_data["date"] = result.date
    if result.party_size:
        state_data["party_size"] = result.party_size

    await state.set_data(state_data)

    if result.date and result.party_size and not result.time:
        available = await dao.get_available_time_slots(
            session, 1, date.fromisoformat(result.date), result.party_size
        )
        if available:
            await state.set_state(BookingStates.awaiting_time)
            await message.answer(
                "Choose a time slot:", reply_markup=time_slots_keyboard(available)
            )
        else:
            await message.answer(
                "No availability for that date. Try another date:",
                reply_markup=date_keyboard(),
            )
            await state.set_state(BookingStates.awaiting_date)
    elif result.date and not result.party_size:
        await state.set_state(BookingStates.awaiting_party_size)
        await message.answer(
            "How many guests?", reply_markup=party_size_keyboard()
        )
    else:
        await state.set_state(BookingStates.awaiting_date)
        await message.answer(
            "When would you like to dine?", reply_markup=date_keyboard()
        )


def _match_time_to_slot(time_str: str, slots) -> object | None:
    if not time_str:
        return None
    try:
        parts = time_str.split(":")
        h, m = int(parts[0]), int(parts[1])
        target = time(h, m)
    except (ValueError, IndexError):
        return None

    for slot in slots:
        if slot.slot_start <= target < slot.slot_end:
            return slot
        if slot.slot_end <= slot.slot_start and (target >= slot.slot_start or target < slot.slot_end):
            return slot
    best = None
    best_diff = float("inf")
    for slot in slots:
        diff = abs(
            (slot.slot_start.hour * 60 + slot.slot_start.minute)
            - (h * 60 + m)
        )
        if diff < best_diff:
            best_diff = diff
            best = slot
    return best
