from __future__ import annotations

import asyncio
import json
from datetime import date, time
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.db.models import Base, FaqResponse, Restaurant, Table, TimeSlot


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine) -> AsyncSession:
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as sess:
        # Seed data
        restaurant = Restaurant(
            id=1,
            name="Lobster Cave",
            telegram_handle="@LobsterCaveBot",
            ton_wallet_address="TEST_WALLET",
            timezone="Europe/Paris",
            opening_time=time(12, 0),
            closing_time=time(23, 0),
            deposit_amount_ton=2.0,
        )
        sess.add(restaurant)
        await sess.flush()

        seed_file = Path(__file__).resolve().parent.parent / "data" / "seed.json"
        data = json.loads(seed_file.read_text())

        for t in data["tables"]:
            sess.add(
                Table(
                    restaurant_id=1,
                    name=t["name"],
                    capacity=t["capacity"],
                    location=t["location"],
                )
            )

        for ts in data["time_slots"]:
            parts_start = ts["slot_start"].split(":")
            parts_end = ts["slot_end"].split(":")
            h_end = int(parts_end[0])
            if h_end == 24:
                h_end = 0
            sess.add(
                TimeSlot(
                    restaurant_id=1,
                    slot_start=time(int(parts_start[0]), int(parts_start[1])),
                    slot_end=time(h_end, int(parts_end[1])),
                )
            )

        for faq in data["faq_responses"]:
            sess.add(
                FaqResponse(
                    restaurant_id=1,
                    question_pattern=faq["question_pattern"],
                    answer=faq["answer"],
                )
            )

        await sess.commit()
        yield sess
