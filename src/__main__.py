import asyncio
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from loguru import logger

from src.ai.client import AIClient
from src.bot.handlers import setup_routers
from src.bot.middleware.db_session import DbSessionMiddleware
from src.config import settings
from src.db.database import async_session_factory, create_tables
from src.db.seed import seed_database
from src.tasks.reminders import setup_scheduler
from src.ton.monitor import DepositMonitor


async def main() -> None:
    logger.info("ClawBot starting...")

    # Ensure data directory exists
    Path("data").mkdir(exist_ok=True)

    # Database setup
    await create_tables()
    async with async_session_factory() as session:
        await seed_database(session)
    logger.info("Database ready.")

    # AI client
    ai_client = AIClient(
        groq_api_key=settings.GROQ_API_KEY,
        grok_api_key=settings.GROK_API_KEY,
        anthropic_api_key=settings.ANTHROPIC_API_KEY,
        libertai_api_key=settings.LIBERTAI_API_KEY,
        ollama_url=settings.OLLAMA_URL,
        ollama_model=settings.OLLAMA_MODEL,
        chaingpt_api_key=settings.CHAINGPT_API_KEY,
    )
    logger.info(f"AI client initialized (primary: {ai_client.active_provider}).")

    # Bot setup
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=None),
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Middleware
    dp.update.middleware(DbSessionMiddleware(async_session_factory))

    # Make ai_client available to handlers via dispatcher data
    dp["ai_client"] = ai_client

    # Routers
    dp.include_router(setup_routers())

    # TON deposit monitor
    monitor = DepositMonitor(
        wallet_address=settings.TON_WALLET_ADDRESS,
        api_key=settings.TON_API_KEY,
        base_url=settings.ton_api_base_url,
        session_factory=async_session_factory,
        bot=bot,
    )
    monitor_task = asyncio.create_task(monitor.start())
    logger.info("Deposit monitor started.")

    # Booking reminders scheduler
    scheduler = setup_scheduler(bot, async_session_factory)
    scheduler.start()
    logger.info("Reminder scheduler started.")

    logger.info("Bot starting polling...")
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        monitor.stop()
        monitor_task.cancel()
        await ai_client.close()
        logger.info("ClawBot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
