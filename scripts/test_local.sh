#!/usr/bin/env bash
# ============================================
# ClawBot Local Test Suite
# Run this BEFORE deploying to verify everything works.
# Usage: ./scripts/test_local.sh
# ============================================
set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok() { echo -e "${GREEN}PASS${NC} $1"; }
fail() { echo -e "${RED}FAIL${NC} $1"; }

echo "🦞 ClawBot Local Test Suite"
echo "==========================="

ERRORS=0

# 1. Unit tests
echo ""
echo "[1/3] Unit Tests (pytest)..."
if source .venv/bin/activate 2>/dev/null && pytest tests/ -q --tb=short 2>&1; then
    ok "All unit tests passed"
else
    fail "Unit tests failed"
    ERRORS=$((ERRORS + 1))
fi

# 2. Health check (config, DB, AI, TON, Telegram)
echo ""
echo "[2/3] Integration Health Check..."
if python scripts/test_health.py 2>&1; then
    ok "Health check passed"
else
    fail "Health check failed"
    ERRORS=$((ERRORS + 1))
fi

# 3. Import check
echo ""
echo "[3/3] Module Import Check..."
if python -c "
from src.config import settings
from src.db.models import Base
from src.ai.client import AIClient
from src.bot.handlers import setup_routers
from src.ton.payments import generate_deposit_link
from src.ton.monitor import DepositMonitor
from src.tasks.reminders import setup_scheduler
print('All modules imported OK')
" 2>&1; then
    ok "All modules import cleanly"
else
    fail "Module import failed"
    ERRORS=$((ERRORS + 1))
fi

# Summary
echo ""
echo "==========================="
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}ALL TESTS PASSED${NC} — safe to deploy!"
    echo ""
    echo "Next: ./scripts/deploy.sh"
else
    echo -e "${RED}$ERRORS TEST(S) FAILED${NC} — fix before deploying"
    exit 1
fi
