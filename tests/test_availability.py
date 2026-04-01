from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from src.db import dao


@pytest.mark.asyncio
async def test_all_tables_available_when_no_bookings(session):
    tables = await dao.get_available_tables(
        session, restaurant_id=1, booking_date=date(2026, 4, 5),
        time_slot_id=1, party_size=1,
    )
    assert len(tables) == 10


@pytest.mark.asyncio
async def test_table_unavailable_after_booking(session):
    tables_before = await dao.get_available_tables(
        session, restaurant_id=1, booking_date=date(2026, 4, 5),
        time_slot_id=1, party_size=2,
    )
    first_table = tables_before[0]

    await dao.create_booking(
        session,
        restaurant_id=1,
        table_id=first_table.id,
        time_slot_id=1,
        date=date(2026, 4, 5),
        guest_telegram_id=111111,
        party_size=2,
        status="confirmed",
    )
    await session.commit()

    tables_after = await dao.get_available_tables(
        session, restaurant_id=1, booking_date=date(2026, 4, 5),
        time_slot_id=1, party_size=2,
    )
    booked_ids = {t.id for t in tables_after}
    assert first_table.id not in booked_ids
    assert len(tables_after) == len(tables_before) - 1


@pytest.mark.asyncio
async def test_double_booking_prevented(session):
    await dao.create_booking(
        session,
        restaurant_id=1,
        table_id=1,
        time_slot_id=2,
        date=date(2026, 4, 6),
        guest_telegram_id=222222,
        party_size=2,
        status="confirmed",
    )
    await session.commit()

    with pytest.raises(IntegrityError):
        await dao.create_booking(
            session,
            restaurant_id=1,
            table_id=1,
            time_slot_id=2,
            date=date(2026, 4, 6),
            guest_telegram_id=333333,
            party_size=2,
            status="confirmed",
        )


@pytest.mark.asyncio
async def test_party_size_filters_tables(session):
    tables = await dao.get_available_tables(
        session, restaurant_id=1, booking_date=date(2026, 4, 7),
        time_slot_id=1, party_size=9,
    )
    # Only tables with capacity >= 9: Table 10 (10-seat)
    assert all(t.capacity >= 9 for t in tables)
    assert len(tables) == 1


@pytest.mark.asyncio
async def test_cancelled_booking_frees_table(session):
    booking = await dao.create_booking(
        session,
        restaurant_id=1,
        table_id=1,
        time_slot_id=3,
        date=date(2026, 4, 8),
        guest_telegram_id=444444,
        party_size=2,
        status="confirmed",
    )
    await session.commit()

    tables_while_booked = await dao.get_available_tables(
        session, restaurant_id=1, booking_date=date(2026, 4, 8),
        time_slot_id=3, party_size=1,
    )
    booked_ids = {t.id for t in tables_while_booked}
    assert 1 not in booked_ids

    await dao.cancel_booking(session, booking.id)
    await session.commit()

    tables_after_cancel = await dao.get_available_tables(
        session, restaurant_id=1, booking_date=date(2026, 4, 8),
        time_slot_id=3, party_size=1,
    )
    freed_ids = {t.id for t in tables_after_cancel}
    assert 1 in freed_ids
