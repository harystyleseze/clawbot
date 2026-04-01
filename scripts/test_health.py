"""
Health check script — run after deployment to verify everything works.
Usage: python scripts/test_health.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


async def main() -> None:
    errors = []
    warnings = []

    print("ClawBot Health Check")
    print("=" * 40)

    # 1. Config
    print("\n[1] Configuration...")
    try:
        from src.config import settings
        assert settings.BOT_TOKEN != "your_bot_token_from_botfather", "BOT_TOKEN not set"
        print(f"  BOT_TOKEN: ...{settings.BOT_TOKEN[-6:]}")
        print(f"  ADMIN_IDS: {settings.admin_ids}")

        # Show AI provider priority
        providers = []
        if settings.GROQ_API_KEY: providers.append("Groq")
        if settings.GROK_API_KEY: providers.append("Grok")
        if settings.LIBERTAI_API_KEY: providers.append("LibertAI")
        if settings.ANTHROPIC_API_KEY: providers.append("Anthropic")
        if settings.OLLAMA_URL: providers.append("Ollama")
        if providers:
            print(f"  AI Providers: {' -> '.join(providers)}")
        else:
            errors.append("No AI provider configured")

        if settings.CHAINGPT_API_KEY:
            print(f"  ChainGPT: configured (blockchain queries)")

        if settings.TON_WALLET_ADDRESS:
            print(f"  TON Wallet: {settings.TON_WALLET_ADDRESS[:20]}...")
            print(f"  TON Network: {'testnet' if settings.TON_TESTNET else 'MAINNET'}")
            print(f"  Require Deposit: {settings.REQUIRE_DEPOSIT}")
        else:
            warnings.append("TON_WALLET_ADDRESS not set — deposits disabled")

        print("  OK")
    except Exception as e:
        errors.append(f"Config: {e}")
        print(f"  FAIL: {e}")

    # 2. Database
    print("\n[2] Database...")
    try:
        from src.db.database import async_session_factory, create_tables
        from src.db import dao

        await create_tables()
        async with async_session_factory() as session:
            restaurant = await dao.get_restaurant(session)
            assert restaurant is not None, "Restaurant not seeded"
            print(f"  Restaurant: {restaurant.name}")
            print(f"  Wallet in DB: {restaurant.ton_wallet_address[:20] if restaurant.ton_wallet_address else 'NOT SET'}...")

            tables = await dao.get_available_tables(
                session, 1, __import__("datetime").date.today(), 1, 2
            )
            print(f"  Available tables: {len(tables)}")

            slots = await dao.get_time_slots(session, 1)
            print(f"  Time slots: {len(slots)}")

            faqs = await dao.get_faq_responses(session, 1)
            print(f"  FAQ entries: {len(faqs)}")

        print("  OK")
    except Exception as e:
        errors.append(f"Database: {e}")
        print(f"  FAIL: {e}")

    # 3. AI Provider
    print("\n[3] AI Provider...")
    try:
        from src.ai.client import AIClient

        client = AIClient(
            groq_api_key=settings.GROQ_API_KEY,
            grok_api_key=settings.GROK_API_KEY,
            libertai_api_key=settings.LIBERTAI_API_KEY,
            anthropic_api_key=settings.ANTHROPIC_API_KEY,
            ollama_url=settings.OLLAMA_URL,
            ollama_model=settings.OLLAMA_MODEL,
            chaingpt_api_key=settings.CHAINGPT_API_KEY,
        )
        print(f"  Primary: {client.active_provider}")

        import time
        t0 = time.time()
        response = await client.chat(
            system="Reply with exactly: OK",
            user_message="Say OK",
            max_tokens=10,
        )
        elapsed = time.time() - t0
        print(f"  Response: {response.strip()[:50]} ({elapsed:.1f}s)")
        await client.close()
        print("  OK")
    except Exception as e:
        errors.append(f"AI Provider: {e}")
        print(f"  FAIL: {e}")

    # 4. TON API
    print("\n[4] TON API...")
    if settings.TON_API_KEY and settings.TON_WALLET_ADDRESS:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as http:
                resp = await http.get(
                    f"{settings.ton_api_base_url}/getTransactions",
                    params={"address": settings.TON_WALLET_ADDRESS, "limit": 1},
                    headers={"X-API-Key": settings.TON_API_KEY},
                )
                data = resp.json()
                assert data.get("ok"), f"TON API error: {data}"
                print(f"  Wallet transactions: {len(data.get('result', []))}")
            print("  OK")
        except Exception as e:
            errors.append(f"TON API: {e}")
            print(f"  FAIL: {e}")
    else:
        warnings.append("TON API not configured — skipped")
        print("  SKIPPED (no TON_API_KEY or TON_WALLET_ADDRESS)")

    # 5. Telegram Bot
    print("\n[5] Telegram Bot...")
    try:
        from aiogram import Bot
        bot = Bot(token=settings.BOT_TOKEN)
        me = await bot.get_me()
        print(f"  Bot: @{me.username} ({me.first_name})")
        await bot.session.close()
        print("  OK")
    except Exception as e:
        errors.append(f"Telegram Bot: {e}")
        print(f"  FAIL: {e}")

    # 6. Payment Link
    print("\n[6] Payment Link...")
    try:
        from src.ton.payments import generate_deposit_link
        link = generate_deposit_link(
            settings.TON_WALLET_ADDRESS or "UQtest", 2.0, 1
        )
        assert link.startswith("ton://transfer/")
        assert "amount=2000000000" in link
        print(f"  Link: {link[:60]}...")
        print("  OK")
    except Exception as e:
        errors.append(f"Payment link: {e}")
        print(f"  FAIL: {e}")

    # Summary
    print("\n" + "=" * 40)
    if errors:
        print(f"ERRORS: {len(errors)}")
        for e in errors:
            print(f"  - {e}")
    if warnings:
        print(f"WARNINGS: {len(warnings)}")
        for w in warnings:
            print(f"  - {w}")
    if not errors:
        print("ALL CHECKS PASSED")
    print("=" * 40)

    return len(errors) == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
