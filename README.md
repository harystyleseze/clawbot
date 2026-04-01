# ClawBot -- Lobster Cave AI Booking Agent

Telegram-native AI concierge for restaurant booking management, powered by TON blockchain.

## What It Does

ClawBot autonomously handles restaurant bookings via Telegram:

- **AI-powered booking** -- understands natural language in any language ("table pour 4 ce soir a 20h")
- **Smart entity extraction** -- extracts date, time, party size from a single message
- **Real-time availability** -- prevents double bookings with database-enforced constraints
- **TON deposits** -- generates `ton://` payment links to reduce no-shows
- **Deposit monitoring** -- polls TON blockchain and auto-confirms payments
- **Booking reminders** -- 2-hour-before reminders via scheduled tasks
- **Admin dashboard** -- `/today` and `/week` commands for staff
- **Multi-language** -- responds in the customer's language (French, English, Russian, etc.)
- **Multi-AI fallback** -- Groq (primary) -> LibertAI -> Anthropic -> Ollama

## Architecture

```
Telegram Customer <-> Bot API <-> ClawBot
                                    |
                    +---------------+---------------+
                    v               v               v
               AI Engine       Booking DB      TON Monitor
            (Groq/LibertAI)   (SQLite)       (TON Center)
```

**Core principle:** AI handles language only. Database is the single source of truth. Zero hallucination risk.

## Quick Start

```bash
./setup.sh              # Setup venv, deps, DB
nano .env               # Add GROQ_API_KEY + BOT_TOKEN
python -m src           # Run
```

See [QUICKSTART.md](QUICKSTART.md) for detailed instructions.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `BOT_TOKEN` | Yes | Telegram bot token from @BotFather |
| `ADMIN_IDS` | Yes | Your Telegram user ID |
| `GROQ_API_KEY` | * | Free at console.groq.com (sub-second!) |
| `LIBERTAI_API_KEY` | * | -|
| `GROK_API_KEY` | * | - |
| `ANTHROPIC_API_KEY` | * | Paid fallback |
| `CHAINGPT_API_KEY` | No | - |
| `TON_API_KEY` | No | From @tonapibot |
| `TON_WALLET_ADDRESS` | No | Your TON wallet for deposits |
| `TON_TESTNET` | No | true=testnet, false=mainnet |
| `REQUIRE_DEPOSIT` | No | true=no skip button (production) |

\* At least one AI provider required: Groq -> Grok -> LibertAI -> Anthropic -> Ollama.

## Testing

```bash
pytest tests/ -v                    # 15 unit tests
./scripts/test_local.sh             # Full local test suite
python scripts/test_health.py       # Integration health check
```

## Deploy

```bash
./scripts/deploy.sh                 # Docker deploy (one command)
```
## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 |
| Bot | aiogram 3.x |
| AI  | Groq (Llama 3.3 70B, 700+ tok/s, free) |
| AI  | LibertAI (decentralized, free hackathon credits) |
| AI  | ChainGPT  |
| Database | SQLAlchemy 2.0 async + SQLite |
| TON | httpx + TON Center API + ton:// deep links |
| Scheduling | APScheduler |

## Sponsor Integrations

- **TON** -- Core payment infrastructure (deposits, on-chain verification)
- **LibertAI / Aleph Cloud** -- Decentralized AI inference + hosting
- **ChainGPT** -- Blockchain-specific queries
- **Ogment** -- Agent security layer (scoped permissions)

## Permissions & Control

- **Admin vs Customer**: `ADMIN_IDS` controls who sees /today, /week
- **Rate limiting**: `MAX_BOOKINGS_PER_USER`, `MAX_PARTY_SIZE`
- **Deposit control**: `REQUIRE_DEPOSIT=true` removes skip option in production
- **TON safety**: Bot only RECEIVES deposits. Never sends TON.
- **AI guardrails**: AI classifies intent only. Database = source of truth.
- **DB constraints**: `UNIQUE(table_id, time_slot_id, date)` prevents double bookings.

## License

MIT