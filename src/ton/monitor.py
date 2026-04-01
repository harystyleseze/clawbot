from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
from aiogram import Bot
from loguru import logger
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.db import dao

LAST_LT_FILE = Path("data/last_lt.txt")


class DepositMonitor:
    def __init__(
        self,
        wallet_address: str,
        api_key: str,
        base_url: str,
        session_factory: async_sessionmaker,
        bot: Bot,
    ) -> None:
        self.wallet_address = wallet_address
        self.api_key = api_key
        self.base_url = base_url
        self.session_factory = session_factory
        self.bot = bot
        self._client = httpx.AsyncClient(timeout=15.0)
        self._last_lt = self._load_last_lt()
        self._running = False

    def _load_last_lt(self) -> int:
        try:
            return int(LAST_LT_FILE.read_text().strip())
        except (FileNotFoundError, ValueError):
            return 0

    def _save_last_lt(self, lt: int) -> None:
        LAST_LT_FILE.write_text(str(lt))

    async def start(self) -> None:
        self._running = True
        logger.info(f"Deposit monitor started (wallet: {self.wallet_address[:20]}...)")
        while self._running:
            try:
                await self._check_transactions()
            except Exception as e:
                logger.error(f"Deposit monitor error: {e}")
            await asyncio.sleep(5)

    def stop(self) -> None:
        self._running = False

    async def _check_transactions(self) -> None:
        if not self.wallet_address or self.wallet_address == "PLACEHOLDER":
            return

        params = {
            "address": self.wallet_address,
            "limit": 50,
        }

        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        try:
            response = await self._client.get(
                f"{self.base_url}/getTransactions",
                params=params,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            logger.debug(f"TON API request failed: {e}")
            return

        if not data.get("ok") or not data.get("result"):
            return

        transactions = data["result"]
        new_lt = self._last_lt

        for tx in transactions:
            tx_lt = int(tx.get("transaction_id", {}).get("lt", 0))
            if tx_lt <= self._last_lt:
                continue

            in_msg = tx.get("in_msg", {})
            value = int(in_msg.get("value", 0))
            comment = in_msg.get("message", "")

            if value > 0 and comment.startswith("booking-"):
                try:
                    booking_id = int(comment.split("-", 1)[1])
                    amount_ton = value / 1_000_000_000
                    tx_hash = tx.get("transaction_id", {}).get("hash", "")
                    await self._confirm_deposit(booking_id, tx_hash, amount_ton)
                except (ValueError, IndexError) as e:
                    logger.warning(f"Could not parse booking from comment '{comment}': {e}")

            if tx_lt > new_lt:
                new_lt = tx_lt

        if new_lt > self._last_lt:
            self._last_lt = new_lt
            self._save_last_lt(new_lt)

    async def _confirm_deposit(
        self, booking_id: int, tx_hash: str, amount_ton: float
    ) -> None:
        async with self.session_factory() as session:
            booking = await dao.get_booking(session, booking_id)
            if not booking:
                logger.warning(f"Deposit for unknown booking #{booking_id}")
                return

            if booking.status == "deposit_paid":
                logger.info(f"Booking #{booking_id} already has deposit")
                return

            await dao.mark_deposit_paid(session, booking_id, tx_hash, amount_ton)
            await session.commit()

            logger.info(f"Deposit confirmed for booking #{booking_id}: {amount_ton} TON")

            # Notify customer
            slot_label = booking.time_slot.label if booking.time_slot else "?"
            try:
                await self.bot.send_message(
                    chat_id=booking.guest_telegram_id,
                    text=(
                        f"Deposit received! {amount_ton:.2f} TON\n\n"
                        f"Your booking #{booking.id} is fully secured.\n"
                        f"Date: {booking.date.strftime('%A %d %B')}\n"
                        f"Time: {slot_label}\n"
                        f"Party: {booking.party_size}\n\n"
                        f"The deposit will be applied to your bill.\n"
                        f"See you at Lobster Cave!"
                    ),
                )
            except Exception as e:
                logger.error(f"Failed to notify guest: {e}")

    async def close(self) -> None:
        self.stop()
        await self._client.aclose()
