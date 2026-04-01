#!/usr/bin/env bash
# ============================================
# ClawBot Setup Script
# ============================================
set -e

echo "🦞 ClawBot Setup"
echo "================"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ok() { echo -e "${GREEN}✓${NC} $1"; }
warn() { echo -e "${YELLOW}!${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; exit 1; }

# 1. Python
echo ""
echo "Checking dependencies..."
if command -v python3.12 &>/dev/null; then
    PYTHON=python3.12
    ok "Python 3.12 found"
elif command -v python3 &>/dev/null; then
    PYTHON=python3
    ok "Python $($PYTHON --version 2>&1) found"
else
    fail "Python 3.10+ required. Install from https://python.org"
fi

# 2. Virtual environment
echo ""
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    $PYTHON -m venv .venv
    ok "Virtual environment created"
else
    ok "Virtual environment exists"
fi
source .venv/bin/activate
ok "Virtual environment activated"

# 3. Dependencies
echo ""
echo "Installing dependencies..."
pip install -q -r requirements.txt
ok "Dependencies installed"

# 4. Environment file
echo ""
if [ ! -f ".env" ]; then
    cp .env.example .env
    ok "Created .env from .env.example"
    warn "Edit .env with your actual keys before running!"
else
    ok ".env file exists"
fi

# 5. Data directory + database
mkdir -p data
ok "Data directory ready"

echo ""
echo "Setting up database..."
python -c "
import asyncio
from src.db.seed import run_seed
asyncio.run(run_seed())
"
ok "Database created and seeded"

# 6. Run tests
echo ""
echo "Running tests..."
if pytest tests/ -q 2>&1 | tail -1 | grep -q "passed"; then
    ok "All tests passing"
else
    warn "Some tests failed"
fi

# 7. Summary
echo ""
echo "============================================"
echo "🦞 ClawBot setup complete!"
echo "============================================"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your keys"
echo "  2. Run: python -m src"
echo ""
echo "Required (at minimum):"
echo "  • BOT_TOKEN      — from @BotFather on Telegram"
echo "  • GROQ_API_KEY   — FREE at https://console.groq.com"
echo ""
echo "Recommended (sponsor integration):"
echo "  • LIBERTAI_API_KEY — free \$20 credits from hackathon"
echo "  • CHAINGPT_API_KEY — blockchain queries"
echo "  • TON_API_KEY + TON_WALLET_ADDRESS — deposits"
echo ""
