# ClawBot -- Lobster Cave AI Booking Agent

Telegram-native AI concierge that autonomously manages restaurant bookings, handles TON crypto deposits, and responds in any language. Built for the [OpenClaw Lobster Cave Cannes Hackathon](https://identityhub.app/contests/openclaw-eth-cc) (TON Track).

**Live Bot:** [@LobsterCaveBot](https://t.me/LobsterCaveBot)
**Deployed on:** [Aleph Cloud](https://smoke-chapter-potato-estate.2n6.me) (decentralized infrastructure)
**Repo:** [github.com/harystyleseze/clawbot](https://github.com/harystyleseze/clawbot)

## The Problem

Restaurant staff at Lobster Cave spend 2-4 hours daily answering booking messages manually. Double bookings happen. No-shows cost 15-25% of revenue. Language barriers with international tourists cause miscommunication.

## The Solution

ClawBot handles 80-90% of booking interactions autonomously:

```
Customer messages bot -> AI understands intent in any language ->
Checks real-time availability -> Confirms booking ->
Collects TON deposit -> Sends reminders -> Done. Zero human input.
```

### Core Features
- **AI-powered booking** -- "table pour 4 ce soir a 20h" works instantly
- **Smart entity extraction** -- extracts date, time, party size from one message
- **Double-booking prevention** -- database-enforced UNIQUE constraints
- **TON deposits** -- `ton://` deep links reduce no-shows by 60-80%
- **Auto deposit verification** -- polls TON blockchain, confirms in seconds
- **Multi-language** -- French, English, Russian, Arabic (AI auto-detects)
- **Admin dashboard** -- `/today`, `/week` for staff oversight
- **Booking reminders** -- automated 2hr-before notifications

## Revenue Model

### Working Now (implemented)
- **TON deposit collection** -- restaurant collects 2 TON deposit per booking via on-chain payments. Deposits reduce no-shows by 60-80%, saving 65-95 EUR per prevented no-show.
- **Upsell infrastructure** -- database supports upsell packages (drinks, events, premium tables). Upsells increase average check by 40-80 EUR.

### Revenue Roadmap (next iteration)
- **Per-booking commission** -- 0.1 TON per confirmed booking (smart contract)
- **Deposit fee** -- 2% platform fee on deposits collected
- **SaaS subscription** -- 50 TON/month per restaurant for hosted bot
- **Upsell commission** -- 5% of prepaid package revenue

**Growth path:** Lobster Cave (Cannes) -> other Cannes restaurants -> French Riviera -> European tourist cities.

**Unit economics:** Each no-show costs 65-95 EUR. A 2 TON deposit prevents most no-shows. The bot pays for itself in week 1 through reduced no-shows alone.

## Architecture

```
Telegram Customer <-> Bot API (aiogram 3) <-> ClawBot Core
                                                  |
                           +----------------------+----------------------+
                           v                      v                      v
                      AI Engine              Booking DB            TON Monitor
                   (Groq / LibertAI)     (SQLAlchemy + SQLite)   (TON Center API)
                           |                      |                      |
                     Intent + Response      Availability +          Deposit Detection
                     in any language        Double-booking          + Auto-confirm
                                            prevention
```

**AI never invents availability.** AI handles language (intent classification + response generation). Database is the single source of truth. Zero hallucination risk for booking data.

## Limits, Permissions & Risk Controls

| Control | Implementation | Purpose |
|---------|---------------|---------|
| **Admin access** | `ADMIN_IDS` env var | Only admins see /today, /week, all bookings |
| **Booking rate limit** | `MAX_BOOKINGS_PER_USER=3` | Prevents spam/abuse |
| **Party size limit** | `MAX_PARTY_SIZE=20` | Validates against restaurant capacity |
| **Booking window** | `BOOKING_WINDOW_DAYS=30` | Limits how far ahead users can book |
| **Deposit enforcement** | `REQUIRE_DEPOSIT=true` | Production: no skip option, deposit required |
| **TON receive-only** | Bot monitors wallet, never holds private keys for sending | Cannot lose funds |
| **Double-booking prevention** | `UNIQUE(table_id, time_slot_id, date)` DB constraint | Impossible at database level |
| **AI guardrails** | AI classifies intent only, DB decides availability | No hallucinated bookings |
| **Provider fallback** | Groq -> LibertAI -> Anthropic -> Ollama | Never goes down |

## Sponsor Integrations

- **TON** -- Core payment layer. `ton://` deep links for deposits, TON Center API for on-chain verification, testnet/mainnet toggle.
- **LibertAI / Aleph Cloud** -- Decentralized AI inference + hosting.
- **ChainGPT** -- Blockchain-specific queries (TON info, crypto questions). Separate from booking AI.
- **Ogment** -- Agent security model: scoped permissions (read bookings, create bookings, but never delete or send funds).

## Deployment

ClawBot is deployed on **Aleph Cloud** (decentralized infrastructure)

### Local Development

```bash
./setup.sh              # Setup venv, deps, DB
nano .env               # Add GROQ_API_KEY + BOT_TOKEN
python -m src           # Run
```

See [QUICKSTART.md](QUICKSTART.md) for detailed setup and testing instructions.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 |
| Bot Framework | aiogram 3.x (async, FSM, inline keyboards) |
| AI (primary) | Groq -- Llama 3.3 70B, 700+ tok/s, free tier |
| AI (sponsor) | LibertAI -- decentralized inference |
| AI (sponsor) | ChainGPT -- blockchain queries |
| Database | SQLAlchemy 2.0 async + SQLite (6 tables, 15 DAO functions) |
| TON | httpx + TON Center API + ton:// deep links |
| Scheduling | APScheduler (reminders) |
| Config | Pydantic Settings |
| Testing | pytest (15 tests: availability, booking flow, deposits) |

## Project Structure

```
src/
├── __main__.py          # Entry point
├── config.py            # All settings via Pydantic
├── ai/                  # Multi-provider AI (Groq/LibertAI/Anthropic/Ollama)
├── bot/handlers/        # /start, booking FSM, admin, callbacks
├── bot/middleware/       # DB session injection
├── db/                  # 6 ORM models, 15 DAO functions, seed data
├── ton/                 # Payment links + deposit monitor
└── tasks/               # Booking reminders (APScheduler)
```

## Testing

```bash
pytest tests/ -v                    # 15 unit tests
./scripts/test_local.sh             # Full test suite + health check
python scripts/test_health.py       # Integration verification
```

## License

MIT
