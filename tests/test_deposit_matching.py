from __future__ import annotations

from datetime import date

import pytest

from src.db import dao
from src.ton.payments import generate_deposit_link


def test_generate_deposit_link_format():
    link = generate_deposit_link("UQtestaddr123", 2.0, 42)
    assert link == "ton://transfer/UQtestaddr123?amount=2000000000&text=booking-42"


def test_deposit_amount_conversion():
    link = generate_deposit_link("UQx", 0.5, 1)
    assert "amount=500000000" in link

    link = generate_deposit_link("UQx", 10.0, 2)
    assert "amount=10000000000" in link


def test_deposit_link_comment_format():
    link = generate_deposit_link("UQx", 1.0, 999)
    assert "text=booking-999" in link


@pytest.mark.asyncio
async def test_deposit_matching_updates_booking(session):
    booking = await dao.create_booking(
        session,
        restaurant_id=1,
        table_id=1,
        time_slot_id=1,
        date=date(2026, 4, 10),
        guest_telegram_id=555555,
        party_size=2,
        status="confirmed",
    )
    await session.commit()

    updated = await dao.mark_deposit_paid(
        session, booking.id, "test_tx_hash_abc", 2.0
    )
    await session.commit()

    assert updated is not None
    assert updated.status == "deposit_paid"
    assert updated.deposit_tx_hash == "test_tx_hash_abc"
    assert updated.deposit_amount == 2.0
