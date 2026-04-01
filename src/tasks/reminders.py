from __future__ import annotations

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.db import dao


async def check_and_send_reminders(
    bot: Bot, session_factory: async_sessionmaker
) -> None:
    async with session_factory() as session:
        bookings = await dao.get_pending_reminders(session)

        for booking in bookings:
            slot_label = booking.time_slot.label if booking.time_slot else "?"
            try:
                await bot.send_message(
                    chat_id=booking.guest_telegram_id,
                    text=(
                        f"Reminder: Your table at Lobster Cave is coming up!\n\n"
                        f"Date: {booking.date.strftime('%A %d %B')}\n"
                        f"Time: {slot_label}\n"
                        f"Party: {booking.party_size}\n\n"
                        f"Lobster Cave, Cannes - La Croisette\n"
                        f"See you soon!"
                    ),
                )
                booking.reminder_sent = True
                logger.info(f"Reminder sent for booking #{booking.id}")
            except Exception as e:
                logger.error(f"Failed to send reminder for booking #{booking.id}: {e}")

        await session.commit()


def setup_scheduler(
    bot: Bot, session_factory: async_sessionmaker
) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="Europe/Paris")
    scheduler.add_job(
        check_and_send_reminders,
        trigger="interval",
        minutes=15,
        args=[bot, session_factory],
        id="booking_reminders",
        replace_existing=True,
    )
    return scheduler
