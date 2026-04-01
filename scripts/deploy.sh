#!/usr/bin/env bash
# ============================================
# ClawBot Docker Deployment
# Usage: ./scripts/deploy.sh
# ============================================
set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "🦞 ClawBot Docker Deployment"
echo "============================"

# 1. Prerequisites
echo ""
echo "[1/4] Checking prerequisites..."
if ! command -v docker &>/dev/null; then
    echo -e "${RED}Docker not found. Install from https://docker.com${NC}"
    exit 1
fi
if [ ! -f ".env" ]; then
    echo -e "${RED}.env not found. Run: cp .env.example .env${NC}"
    exit 1
fi
echo -e "${GREEN}OK${NC}"

# 2. Build
echo ""
echo "[2/4] Building Docker image..."
docker compose build 2>&1 | tail -3
echo -e "${GREEN}OK${NC}"

# 3. Deploy
echo ""
echo "[3/4] Starting ClawBot..."
docker compose down 2>/dev/null || true
docker compose up -d
echo "Waiting 5 seconds for startup..."
sleep 5
echo -e "${GREEN}OK${NC}"

# 4. Verify
echo ""
echo "[4/4] Verifying..."
CONTAINER=$(docker compose ps -q bot 2>/dev/null)
STATUS=$(docker inspect --format='{{.State.Status}}' "$CONTAINER" 2>/dev/null)
if [ "$STATUS" = "running" ]; then
    echo -e "${GREEN}Container running${NC}"
else
    echo -e "${RED}Container status: $STATUS${NC}"
    docker compose logs bot --tail 10
    exit 1
fi

echo ""
echo "Recent logs:"
docker compose logs bot --tail 8 2>&1
echo ""

echo "============================"
echo -e "${GREEN}ClawBot deployed!${NC}"
echo ""
echo "Commands:"
echo "  docker compose logs bot -f                              # Follow logs"
echo "  docker compose exec bot python scripts/test_health.py   # Health check"
echo "  docker compose restart bot                               # Restart"
echo "  docker compose down                                      # Stop"
