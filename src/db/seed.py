from __future__ import annotations

import asyncio
import json
from datetime import time
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import FaqResponse, Restaurant, Table, TimeSlot


SEED_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "seed.json"


def _parse_time(s: str) -> time:
    parts = s.split(":")
    h, m = int(parts[0]), int(parts[1])
    if h == 24:
        h = 0
    return time(h, m)


async def seed_database(session: AsyncSession) -> None:
    # Check if already seeded
    result = await session.execute(select(Restaurant).limit(1))
    if result.scalar_one_or_none() is not None:
        return

    data = json.loads(SEED_FILE.read_text())

    # Restaurant
    r = data["restaurant"]
    restaurant = Restaurant(
        name=r["name"],
        telegram_handle=r["telegram_handle"],
        ton_wallet_address=r["ton_wallet_address"],
        timezone=r["timezone"],
        opening_time=_parse_time(r["opening_time"]),
        closing_time=_parse_time(r["closing_time"]),
        deposit_amount_ton=r["deposit_amount_ton"],
    )
    session.add(restaurant)
    await session.flush()

    # Tables
    for t in data["tables"]:
        session.add(
            Table(
                restaurant_id=restaurant.id,
                name=t["name"],
                capacity=t["capacity"],
                location=t["location"],
            )
        )

    # Time slots
    for ts in data["time_slots"]:
        session.add(
            TimeSlot(
                restaurant_id=restaurant.id,
                slot_start=_parse_time(ts["slot_start"]),
                slot_end=_parse_time(ts["slot_end"]),
            )
        )

    # FAQ responses
    for faq in data["faq_responses"]:
        session.add(
            FaqResponse(
                restaurant_id=restaurant.id,
                question_pattern=faq["question_pattern"],
                answer=faq["answer"],
            )
        )

    await session.commit()


async def run_seed() -> None:
    from src.db.database import async_session_factory, create_tables

    await create_tables()
    async with async_session_factory() as session:
        await seed_database(session)
    print("Database seeded successfully.")


if __name__ == "__main__":
    asyncio.run(run_seed())
