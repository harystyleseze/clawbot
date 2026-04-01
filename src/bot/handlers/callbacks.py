from __future__ import annotations

from datetime import date

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards import (
    confirm_keyboard,
    date_keyboard,
    deposit_keyboard,
    party_size_keyboard,
    time_slots_keyboard,
)
from src.bot.states import BookingStates
from src.config import settings
from src.db import dao
from src.ton.payments import generate_deposit_link

router = Router()


# --- Date selection ---
@router.callback_query(F.data.startswith("date:"))
async def on_date_selected(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    date_str = callback.data.split(":", 1)[1]
    data = await state.get_data()
    data["date"] = date_str
    await state.set_data(data)
    await callback.answer()

    party_size = data.get("party_size")
    if party_size:
        available = await dao.get_available_time_slots(
            session, 1, date.fromisoformat(date_str), party_size
        )
        if available:
            await state.set_state(BookingStates.awaiting_time)
            await callback.message.edit_text(
                f"Date: {date_str}\nChoose a time slot:",
                reply_markup=time_slots_keyboard(available),
            )
        else:
            await callback.message.edit_text(
                "No availability for that date. Try another:",
                reply_markup=date_keyboard(),
            )
    else:
        await state.set_state(BookingStates.awaiting_party_size)
        await callback.message.edit_text(
            f"Date: {date_str}\nHow many guests?",
            reply_markup=party_size_keyboard(),
        )


# --- Time slot selection ---
@router.callback_query(F.data.startswith("timeslot:"))
async def on_time_selected(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    slot_id = int(callback.data.split(":", 1)[1])
    data = await state.get_data()
    data["time_slot_id"] = slot_id
    await state.set_data(data)
    await callback.answer()

    if not data.get("party_size"):
        await state.set_state(BookingStates.awaiting_party_size)
        await callback.message.edit_text(
            "How many guests?", reply_markup=party_size_keyboard()
        )
    else:
        # Check availability and show confirmation
        booking_date = date.fromisoformat(data["date"])
        tables = await dao.get_available_tables(
            session, 1, booking_date, slot_id, data["party_size"]
        )
        if tables:
            data["table_id"] = tables[0].id
            await state.set_data(data)
            await state.set_state(BookingStates.awaiting_confirmation)

            slot = None
            slots = await dao.get_time_slots(session, restaurant_id=1)
            for s in slots:
                if s.id == slot_id:
                    slot = s
                    break
            slot_label = slot.label if slot else "?"

            summary = (
                f"Booking summary:\n"
                f"Date: {booking_date.strftime('%A %d %B')}\n"
                f"Time: {slot_label}\n"
                f"Party size: {data['party_size']}\n"
            )
            await callback.message.edit_text(summary, reply_markup=confirm_keyboard())
        else:
            await callback.message.edit_text(
                "Sorry, no tables available for that slot. Try another time:",
                reply_markup=date_keyboard(),
            )
            await state.set_state(BookingStates.awaiting_date)


# --- Party size selection ---
@router.callback_query(F.data.startswith("party:"))
async def on_party_selected(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    size = int(callback.data.split(":", 1)[1])
    data = await state.get_data()
    data["party_size"] = size
    await state.set_data(data)
    await callback.answer()

    if not data.get("date"):
        await state.set_state(BookingStates.awaiting_date)
        await callback.message.edit_text(
            f"Party of {size}. When would you like to dine?",
            reply_markup=date_keyboard(),
        )
    elif not data.get("time_slot_id"):
        booking_date = date.fromisoformat(data["date"])
        available = await dao.get_available_time_slots(
            session, 1, booking_date, size
        )
        if available:
            await state.set_state(BookingStates.awaiting_time)
            await callback.message.edit_text(
                f"Party of {size} on {data['date']}.\nChoose a time:",
                reply_markup=time_slots_keyboard(available),
            )
        else:
            await callback.message.edit_text(
                "No availability for that date and party size. Try another date:",
                reply_markup=date_keyboard(),
            )
            await state.set_state(BookingStates.awaiting_date)
    else:
        # Have all data — check availability
        booking_date = date.fromisoformat(data["date"])
        tables = await dao.get_available_tables(
            session, 1, booking_date, data["time_slot_id"], size
        )
        if tables:
            data["table_id"] = tables[0].id
            await state.set_data(data)
            await state.set_state(BookingStates.awaiting_confirmation)

            slot = None
            slots = await dao.get_time_slots(session, restaurant_id=1)
            for s in slots:
                if s.id == data["time_slot_id"]:
                    slot = s
                    break
            slot_label = slot.label if slot else "?"

            summary = (
                f"Booking summary:\n"
                f"Date: {booking_date.strftime('%A %d %B')}\n"
                f"Time: {slot_label}\n"
                f"Party size: {size}\n"
            )
            await callback.message.edit_text(summary, reply_markup=confirm_keyboard())
        else:
            await callback.message.edit_text(
                "No tables available. Try a different time:",
                reply_markup=date_keyboard(),
            )
            await state.set_state(BookingStates.awaiting_date)


# --- Confirmation ---
@router.callback_query(F.data.startswith("confirm:"))
async def on_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    action = callback.data.split(":", 1)[1]
    await callback.answer()

    if action == "yes":
        await _do_confirm_booking(callback.message, state, session)
    elif action == "change_date":
        await state.set_state(BookingStates.awaiting_date)
        await callback.message.edit_text(
            "Choose a new date:", reply_markup=date_keyboard()
        )
    elif action == "change_time":
        data = await state.get_data()
        if data.get("date") and data.get("party_size"):
            available = await dao.get_available_time_slots(
                session, 1, date.fromisoformat(data["date"]), data["party_size"]
            )
            await state.set_state(BookingStates.awaiting_time)
            await callback.message.edit_text(
                "Choose a new time:", reply_markup=time_slots_keyboard(available)
            )
        else:
            await state.set_state(BookingStates.awaiting_date)
            await callback.message.edit_text(
                "Let's start over. Choose a date:", reply_markup=date_keyboard()
            )
    elif action == "cancel":
        await state.clear()
        await callback.message.edit_text("Booking cancelled. Send me a message anytime to start again!")


async def _do_confirm_booking(
    message: Message,
    state: FSMContext,
    session: AsyncSession | None,
) -> None:
    data = await state.get_data()

    # Get session from middleware if not provided (called from text handler)
    if session is None:
        logger.warning("No session in confirm — booking not saved")
        await message.answer("Please use the confirm button.")
        return

    try:
        booking = await dao.create_booking(
            session,
            restaurant_id=1,
            table_id=data["table_id"],
            time_slot_id=data["time_slot_id"],
            date=date.fromisoformat(data["date"]),
            guest_name=message.chat.first_name or "Guest",
            guest_telegram_id=message.chat.id,
            guest_telegram_username=message.chat.username,
            party_size=data["party_size"],
            status="confirmed",
            special_requests=data.get("special_requests"),
            language=data.get("language", "en"),
        )
        await session.commit()
    except Exception as e:
        logger.error(f"Failed to create booking: {e}")
        await state.clear()
        await message.answer(
            "Sorry, that slot was just taken! Please try again."
        )
        return

    # Send deposit offer
    restaurant = await dao.get_restaurant(session)
    deposit_amount = restaurant.deposit_amount_ton if restaurant else settings.DEPOSIT_AMOUNT_TON
    wallet = restaurant.ton_wallet_address if restaurant else settings.TON_WALLET_ADDRESS

    ton_link = generate_deposit_link(wallet, deposit_amount, booking.id)

    await state.set_state(BookingStates.awaiting_deposit)
    await state.update_data(booking_id=booking.id)

    try:
        await message.edit_text(
            f"Booking #{booking.id} confirmed!\n\n"
            f"To secure your table, send a {deposit_amount} TON deposit.\n"
            f"It will be applied to your bill.",
            reply_markup=deposit_keyboard(ton_link, booking.id, allow_skip=not settings.REQUIRE_DEPOSIT),
        )
    except Exception:
        await message.answer(
            f"Booking #{booking.id} confirmed!\n\n"
            f"To secure your table, send a {deposit_amount} TON deposit.\n"
            f"It will be applied to your bill.",
            reply_markup=deposit_keyboard(ton_link, booking.id, allow_skip=not settings.REQUIRE_DEPOSIT),
        )


# --- Skip deposit ---
@router.callback_query(F.data.startswith("skip_deposit:"))
async def on_skip_deposit(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    booking_id = int(callback.data.split(":", 1)[1])
    await callback.answer()

    if settings.REQUIRE_DEPOSIT:
        await callback.message.answer("A deposit is required to secure your table. Please complete the payment.")
        return

    await state.clear()

    booking = await dao.get_booking(session, booking_id)
    if booking:
        slot_label = booking.time_slot.label if booking.time_slot else "?"
        await callback.message.edit_text(
            f"You're all set! Booking #{booking.id}\n\n"
            f"Date: {booking.date.strftime('%A %d %B')}\n"
            f"Time: {slot_label}\n"
            f"Party: {booking.party_size}\n\n"
            f"Lobster Cave, Cannes - La Croisette\n"
            f"See you there!"
        )
    else:
        await callback.message.edit_text("Booking confirmed! See you at Lobster Cave!")
