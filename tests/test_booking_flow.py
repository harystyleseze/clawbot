from __future__ import annotations

from datetime import date

import pytest

from src.db import dao


@pytest.mark.asyncio
async def test_full_booking_flow(session):
    # 1. Check availability
    tables = await dao.get_available_tables(
        session, 1, date(2026, 4, 15), time_slot_id=3, party_size=4
    )
    assert len(tables) > 0

    # 2. Create booking
    booking = await dao.create_booking(
        session,
        restaurant_id=1,
        table_id=tables[0].id,
        time_slot_id=3,
        date=date(2026, 4, 15),
        guest_telegram_id=100001,
        guest_name="Test Guest",
        party_size=4,
        status="confirmed",
        language="en",
    )
    await session.commit()

    assert booking.id is not None
    assert booking.status == "confirmed"
    assert booking.party_size == 4

    # 3. Verify booking is retrievable
    fetched = await dao.get_booking(session, booking.id)
    assert fetched is not None
    assert fetched.guest_telegram_id == 100001

    # 4. Verify it shows in user's bookings
    user_bookings = await dao.get_bookings_by_telegram_id(session, 100001)
    assert len(user_bookings) >= 1
    assert any(b.id == booking.id for b in user_bookings)

    # 5. Verify it shows in date bookings
    date_bookings = await dao.get_bookings_for_date(session, 1, date(2026, 4, 15))
    assert any(b.id == booking.id for b in date_bookings)


@pytest.mark.asyncio
async def test_booking_when_full(session):
    # Book ALL 2-capacity tables for a specific slot
    tables = await dao.get_available_tables(
        session, 1, date(2026, 4, 20), time_slot_id=4, party_size=2
    )
    for t in tables:
        await dao.create_booking(
            session,
            restaurant_id=1,
            table_id=t.id,
            time_slot_id=4,
            date=date(2026, 4, 20),
            guest_telegram_id=200000 + t.id,
            party_size=2,
            status="confirmed",
        )
    await session.commit()

    # Should be zero tables available
    remaining = await dao.get_available_tables(
        session, 1, date(2026, 4, 20), time_slot_id=4, party_size=1
    )
    assert len(remaining) == 0


@pytest.mark.asyncio
async def test_cancel_frees_slot(session):
    booking = await dao.create_booking(
        session,
        restaurant_id=1,
        table_id=3,
        time_slot_id=5,
        date=date(2026, 4, 22),
        guest_telegram_id=300001,
        party_size=4,
        status="confirmed",
    )
    await session.commit()

    # Table 3 should be unavailable
    tables = await dao.get_available_tables(
        session, 1, date(2026, 4, 22), time_slot_id=5, party_size=1
    )
    assert all(t.id != 3 for t in tables)

    # Cancel
    await dao.cancel_booking(session, booking.id)
    await session.commit()

    # Table 3 should be available again
    tables = await dao.get_available_tables(
        session, 1, date(2026, 4, 22), time_slot_id=5, party_size=1
    )
    assert any(t.id == 3 for t in tables)


@pytest.mark.asyncio
async def test_get_available_time_slots(session):
    slots = await dao.get_available_time_slots(
        session, 1, date(2026, 4, 25), party_size=2
    )
    # All 6 slots should be available (no bookings)
    assert len(slots) == 6


@pytest.mark.asyncio
async def test_faq_responses_loaded(session):
    faqs = await dao.get_faq_responses(session, 1)
    assert len(faqs) == 8
    patterns = [f.question_pattern for f in faqs]
    assert any("hours" in p for p in patterns)
    assert any("location" in p for p in patterns)


@pytest.mark.asyncio
async def test_booking_range_query(session):
    await dao.create_booking(
        session,
        restaurant_id=1,
        table_id=5,
        time_slot_id=1,
        date=date(2026, 4, 28),
        guest_telegram_id=400001,
        party_size=3,
        status="confirmed",
    )
    await session.commit()

    bookings = await dao.get_bookings_for_range(
        session, 1, date(2026, 4, 27), date(2026, 4, 30)
    )
    assert len(bookings) >= 1
    assert any(b.guest_telegram_id == 400001 for b in bookings)
