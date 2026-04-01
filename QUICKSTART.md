# ClawBot Quickstart Guide

## 1. Setup (2 minutes)

```bash
./setup.sh
```

Or manually:
```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m src.db.seed
```

## 2. Get Your Keys

### Telegram Bot Token (REQUIRED)
1. Open Telegram, message `@BotFather`
2. Send `/newbot`, choose a name and username
3. Copy the token -> `.env` as `BOT_TOKEN`

### Your Telegram User ID (for admin)
1. Message `@userinfobot` or `@raw_` on Telegram
2. Copy your ID -> `.env` as `ADMIN_IDS`

### AI Provider (at least one REQUIRED)

**Groq (Recommended -- FREE, sub-second responses)**
1. Go to https://console.groq.com
2. Sign up (no credit card needed)
3. Create API Key
4. Paste in `.env` as `GROQ_API_KEY`

**LibertAI (Sponsor -- $20 free hackathon credits)**
1. Get credits at https://openclaw-lobster-cannes.libertai.io/
2. Get API key from dashboard
3. Paste in `.env` as `LIBERTAI_API_KEY`

**xAI Grok ($25 free credits)**
1. Go to https://x.ai/api
2. Sign up, get API key
3. Paste in `.env` as `GROK_API_KEY`

**ChainGPT (Sponsor -- blockchain queries only)**
1. Go to https://app.chaingpt.org
2. Create API key
3. Paste in `.env` as `CHAINGPT_API_KEY`
4. For free credits: https://forms.gle/93eseeJiqgUtmaAK9

### TON Blockchain (for deposits)

**TON Center API Key:**
1. Message `@tonapibot` on Telegram
2. Paste key in `.env` as `TON_API_KEY`

**TON Testnet Wallet:**
1. Install Tonkeeper (https://tonkeeper.com)
2. Settings -> Network -> Testnet
3. Copy address -> `.env` as `TON_WALLET_ADDRESS`

**Get Testnet TON:**
- `@testgiver_ton_bot` on Telegram (2 TON / 60 min)
- https://faucet.chainstack.com/ton-testnet-faucet (1 TON / 24h)

## 3. Run

```bash
source .venv/bin/activate
python -m src
```

Expected output:
```
ClawBot starting...
Database ready.
AI client initialized (primary: Groq).
Deposit monitor started.
Reminder scheduler started.
Bot starting polling...
```

## 4. Test

1. `/start` -> welcome message
2. `Table for 4 tonight at 8pm` -> booking flow
3. Tap Confirm -> deposit offer
4. `/mybookings` -> view bookings
5. `/today` -> admin view
6. `Bonjour, vous etes ouvert quand?` -> French FAQ response
7. `/cancel` -> cancel booking

## 5. Deploy

### Docker (any VPS)
```bash
./scripts/deploy.sh
```

### Production Settings
```bash
# In .env:
TON_TESTNET=false          # Mainnet
REQUIRE_DEPOSIT=true       # No skip button
LOG_LEVEL=INFO
```

## 6. Permissions & Control

| Setting | Default | Description |
|---------|---------|-------------|
| `REQUIRE_DEPOSIT` | false | true = no "Skip Deposit" button |
| `MAX_BOOKINGS_PER_USER` | 3 | Max active bookings per user |
| `MAX_PARTY_SIZE` | 20 | Max guests per booking |
| `ADMIN_IDS` | - | Who can use /today, /week |

**AI Priority:** Groq -> Grok -> LibertAI -> Anthropic -> Ollama (auto-fallback)

**TON Safety:** Bot only monitors for incoming deposits. Never sends funds.

**DB Safety:** `UNIQUE(table_id, time_slot_id, date)` prevents double bookings at the database level.
