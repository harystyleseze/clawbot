from __future__ import annotations

from datetime import date

from aiogram import F, Router
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


@router.message(BookingStates.awaiting_date)
async def handle_date_text(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    ai_client: AIClient,
) -> None:
    text = message.text or ""
    # Try AI to parse the date
    result = await classify_and_respond(ai_client, text)
    if result.date:
        data = await state.get_data()
        data["date"] = result.date
        if result.party_size:
            data["party_size"] = result.party_size
        await state.set_data(data)

        party_size = data.get("party_size", 2)
        available = await dao.get_available_time_slots(
            session, 1, date.fromisoformat(result.date), party_size
        )
        if available:
            await state.set_state(BookingStates.awaiting_time)
            await message.answer(
                "Choose a time slot:", reply_markup=time_slots_keyboard(available)
            )
        else:
            await message.answer(
                "No availability for that date. Try another:",
                reply_markup=date_keyboard(),
            )
    else:
        await message.answer(
            "I couldn't understand that date. Please pick one:",
            reply_markup=date_keyboard(),
        )


@router.message(BookingStates.awaiting_time)
async def handle_time_text(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    ai_client: AIClient,
) -> None:
    text = message.text or ""
    result = await classify_and_respond(ai_client, text)
    if result.time:
        from src.bot.handlers.start import _match_time_to_slot

        data = await state.get_data()
        slots = await dao.get_time_slots(session, restaurant_id=1)
        matched = _match_time_to_slot(result.time, slots)
        if matched:
            data["time_slot_id"] = matched.id
            await state.set_data(data)
            if not data.get("party_size"):
                await state.set_state(BookingStates.awaiting_party_size)
                await message.answer(
                    "How many guests?", reply_markup=party_size_keyboard()
                )
            else:
                await _check_and_confirm(message, state, session, data)
            return

    data = await state.get_data()
    booking_date = data.get("date", date.today().isoformat())
    party_size = data.get("party_size", 2)
    available = await dao.get_available_time_slots(
        session, 1, date.fromisoformat(booking_date), party_size
    )
    await message.answer(
        "Please pick a time slot:", reply_markup=time_slots_keyboard(available)
    )


@router.message(BookingStates.awaiting_party_size)
async def handle_party_size_text(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    text = (message.text or "").strip()
    try:
        size = int(text)
        if 1 <= size <= settings.MAX_PARTY_SIZE:
            data = await state.get_data()
            data["party_size"] = size
            await state.set_data(data)
            await _check_and_confirm(message, state, session, data)
            return
    except ValueError:
        pass
    await message.answer(
        f"Please enter a number (1-{settings.MAX_PARTY_SIZE}):",
        reply_markup=party_size_keyboard(),
    )


@router.message(BookingStates.awaiting_confirmation)
async def handle_confirmation_text(
    message: Message, state: FSMContext
) -> None:
    text = (message.text or "").lower()
    if any(w in text for w in ["yes", "confirm", "oui", "da"]):
        # Treat as confirm
        from src.bot.handlers.callbacks import _do_confirm_booking

        await _do_confirm_booking(message, state, None)
    else:
        await message.answer(
            "Please use the buttons below to confirm or change your booking:",
            reply_markup=confirm_keyboard(),
        )


async def _check_and_confirm(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    data: dict,
) -> None:
    booking_date = date.fromisoformat(data["date"])
    time_slot_id = data["time_slot_id"]
    party_size = data["party_size"]

    tables = await dao.get_available_tables(
        session, 1, booking_date, time_slot_id, party_size
    )

    if not tables:
        await message.answer(
            "Sorry, no tables available for that combination. "
            "Try a different time:",
            reply_markup=date_keyboard(),
        )
        await state.set_state(BookingStates.awaiting_date)
        return

    data["table_id"] = tables[0].id
    await state.set_data(data)
    await state.set_state(BookingStates.awaiting_confirmation)

    slot = None
    slots = await dao.get_time_slots(session, restaurant_id=1)
    for s in slots:
        if s.id == time_slot_id:
            slot = s
            break
    slot_label = slot.label if slot else "?"

    summary = (
        f"Booking summary:\n"
        f"Date: {booking_date.strftime('%A %d %B')}\n"
        f"Time: {slot_label}\n"
        f"Party size: {party_size}\n"
    )
    if data.get("special_requests"):
        summary += f"Requests: {data['special_requests']}\n"

    await message.answer(summary, reply_markup=confirm_keyboard())
