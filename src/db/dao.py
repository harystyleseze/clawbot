from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.models import (
    Booking,
    FaqResponse,
    Restaurant,
    Table,
    TimeSlot,
    UpsellPackage,
)


async def get_restaurant(session: AsyncSession, restaurant_id: int = 1) -> Restaurant | None:
    result = await session.execute(
        select(Restaurant).where(Restaurant.id == restaurant_id)
    )
    return result.scalar_one_or_none()


async def get_available_tables(
    session: AsyncSession,
    restaurant_id: int,
    booking_date: date,
    time_slot_id: int,
    party_size: int,
) -> list[Table]:
    booked_table_ids = (
        select(Booking.table_id).where(
            Booking.restaurant_id == restaurant_id,
            Booking.date == booking_date,
            Booking.time_slot_id == time_slot_id,
            Booking.status.in_(["pending", "confirmed", "deposit_paid"]),
        )
    )
    result = await session.execute(
        select(Table).where(
            Table.restaurant_id == restaurant_id,
            Table.capacity >= party_size,
            Table.is_active == True,
            ~Table.id.in_(booked_table_ids),
        ).order_by(Table.capacity.asc())
    )
    return list(result.scalars().all())


async def get_time_slots(
    session: AsyncSession, restaurant_id: int
) -> list[TimeSlot]:
    result = await session.execute(
        select(TimeSlot).where(
            TimeSlot.restaurant_id == restaurant_id,
            TimeSlot.is_active == True,
        ).order_by(TimeSlot.slot_start)
    )
    return list(result.scalars().all())


async def get_available_time_slots(
    session: AsyncSession,
    restaurant_id: int,
    booking_date: date,
    party_size: int,
) -> list[TimeSlot]:
    all_slots = await get_time_slots(session, restaurant_id)
    available = []
    for slot in all_slots:
        tables = await get_available_tables(
            session, restaurant_id, booking_date, slot.id, party_size
        )
        if tables:
            available.append(slot)
    return available


async def create_booking(session: AsyncSession, **kwargs) -> Booking:
    booking = Booking(**kwargs)
    session.add(booking)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        raise
    return booking


async def get_booking(session: AsyncSession, booking_id: int) -> Booking | None:
    result = await session.execute(
        select(Booking)
        .options(selectinload(Booking.table), selectinload(Booking.time_slot))
        .where(Booking.id == booking_id)
    )
    return result.scalar_one_or_none()


async def get_bookings_by_telegram_id(
    session: AsyncSession, telegram_id: int, active_only: bool = True
) -> list[Booking]:
    query = (
        select(Booking)
        .options(selectinload(Booking.table), selectinload(Booking.time_slot))
        .where(Booking.guest_telegram_id == telegram_id)
    )
    if active_only:
        query = query.where(
            Booking.status.in_(["pending", "confirmed", "deposit_paid"])
        )
    query = query.order_by(Booking.date.desc(), Booking.created_at.desc())
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_bookings_for_date(
    session: AsyncSession, restaurant_id: int, booking_date: date
) -> list[Booking]:
    result = await session.execute(
        select(Booking)
        .options(selectinload(Booking.table), selectinload(Booking.time_slot))
        .where(
            Booking.restaurant_id == restaurant_id,
            Booking.date == booking_date,
            Booking.status.in_(["pending", "confirmed", "deposit_paid"]),
        )
        .order_by(Booking.time_slot_id, Booking.created_at)
    )
    return list(result.scalars().all())


async def get_bookings_for_range(
    session: AsyncSession,
    restaurant_id: int,
    start_date: date,
    end_date: date,
) -> list[Booking]:
    result = await session.execute(
        select(Booking)
        .options(selectinload(Booking.table), selectinload(Booking.time_slot))
        .where(
            Booking.restaurant_id == restaurant_id,
            Booking.date >= start_date,
            Booking.date <= end_date,
            Booking.status.in_(["pending", "confirmed", "deposit_paid"]),
        )
        .order_by(Booking.date, Booking.time_slot_id)
    )
    return list(result.scalars().all())


async def update_booking_status(
    session: AsyncSession, booking_id: int, status: str, **kwargs
) -> Booking | None:
    booking = await get_booking(session, booking_id)
    if booking is None:
        return None
    booking.status = status
    booking.updated_at = datetime.now(UTC)
    for key, value in kwargs.items():
        if hasattr(booking, key):
            setattr(booking, key, value)
    await session.flush()
    return booking


async def cancel_booking(session: AsyncSession, booking_id: int) -> Booking | None:
    return await update_booking_status(session, booking_id, "cancelled")


async def mark_deposit_paid(
    session: AsyncSession, booking_id: int, tx_hash: str, amount: float
) -> Booking | None:
    return await update_booking_status(
        session,
        booking_id,
        "deposit_paid",
        deposit_tx_hash=tx_hash,
        deposit_amount=amount,
    )


async def get_pending_reminders(
    session: AsyncSession, now: datetime | None = None
) -> list[Booking]:
    if now is None:
        now = datetime.now(UTC)
    today = now.date()
    reminder_window = now + timedelta(hours=2)

    result = await session.execute(
        select(Booking)
        .options(selectinload(Booking.time_slot))
        .where(
            Booking.date == today,
            Booking.status.in_(["confirmed", "deposit_paid"]),
            Booking.reminder_sent == False,
        )
    )
    bookings = list(result.scalars().all())
    # Filter by time window in Python (SQLite doesn't do time math well)
    pending = []
    for b in bookings:
        slot_dt = datetime.combine(b.date, b.time_slot.slot_start)
        # Make both naive for comparison (SQLite stores naive datetimes)
        now_naive = now.replace(tzinfo=None) if now.tzinfo else now
        window_naive = reminder_window.replace(tzinfo=None) if reminder_window.tzinfo else reminder_window
        if now_naive <= slot_dt <= window_naive:
            pending.append(b)
    return pending


async def get_faq_responses(
    session: AsyncSession, restaurant_id: int
) -> list[FaqResponse]:
    result = await session.execute(
        select(FaqResponse).where(FaqResponse.restaurant_id == restaurant_id)
    )
    return list(result.scalars().all())


async def get_upsell_packages(
    session: AsyncSession, restaurant_id: int
) -> list[UpsellPackage]:
    result = await session.execute(
        select(UpsellPackage).where(
            UpsellPackage.restaurant_id == restaurant_id,
            UpsellPackage.is_active == True,
        )
    )
    return list(result.scalars().all())
