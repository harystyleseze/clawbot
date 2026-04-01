from __future__ import annotations

from datetime import date, timedelta

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.db import dao

router = Router()


def _is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids


@router.message(Command("today"))
async def cmd_today(message: Message, session: AsyncSession) -> None:
    if not _is_admin(message.from_user.id):
        await message.answer("Admin only command.")
        return

    today = date.today()
    bookings = await dao.get_bookings_for_date(session, 1, today)

    if not bookings:
        await message.answer(f"No bookings for today ({today.strftime('%d %b')}).")
        return

    lines = [f"Bookings for today ({today.strftime('%A %d %b')}):\n"]
    for b in bookings:
        slot_label = b.time_slot.label if b.time_slot else "?"
        table_name = b.table.name if b.table else "?"
        deposit = f" [TON deposit]" if b.status == "deposit_paid" else ""
        guest = b.guest_name or b.guest_telegram_username or f"ID:{b.guest_telegram_id}"
        lines.append(
            f"  {slot_label} | {table_name} | {guest} | "
            f"Party of {b.party_size} | {b.status}{deposit}"
        )

    lines.append(f"\nTotal: {len(bookings)} bookings")
    await message.answer("\n".join(lines))


@router.message(Command("week"))
async def cmd_week(message: Message, session: AsyncSession) -> None:
    if not _is_admin(message.from_user.id):
        await message.answer("Admin only command.")
        return

    today = date.today()
    end = today + timedelta(days=7)
    bookings = await dao.get_bookings_for_range(session, 1, today, end)

    if not bookings:
        await message.answer("No bookings for the next 7 days.")
        return

    # Group by date
    by_date: dict[date, list] = {}
    for b in bookings:
        by_date.setdefault(b.date, []).append(b)

    lines = ["Bookings for the next 7 days:\n"]
    for d in sorted(by_date.keys()):
        lines.append(f"\n{d.strftime('%A %d %b')} ({len(by_date[d])} bookings):")
        for b in by_date[d]:
            slot_label = b.time_slot.label if b.time_slot else "?"
            guest = b.guest_name or b.guest_telegram_username or f"ID:{b.guest_telegram_id}"
            lines.append(f"  {slot_label} | {guest} | Party of {b.party_size} | {b.status}")

    lines.append(f"\nTotal: {len(bookings)} bookings")
    await message.answer("\n".join(lines))
