#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "============================================"
echo "  E-Room Development Launcher"
echo "============================================"
echo ""

# ── Step 1: Check .env ──────────────────────────
echo -e "[1/6] Checking .env..."
if [ ! -f backend/.env ]; then
    cp backend/.env.example backend/.env
    echo -e "      ${YELLOW}Created backend/.env${NC} — edit LLM_BASE_URL before starting."
else
    echo "      .env already exists, skipping."
fi

# ── Step 2: Docker infra ────────────────────────
echo "[2/6] Checking Docker infrastructure..."
if ! docker ps --format "{{.Names}}" 2>/dev/null | grep -q "e_room_tidb"; then
    echo "      Starting Docker services: tidb, redis, minio, livekit, coturn..."
    docker compose up -d tidb redis minio livekit coturn || {
        echo -e "      ${RED}[ERROR] Docker failed to start.${NC}"
        exit 1
    }
    echo "      Waiting for TiDB to be ready (may take 20-30s first time)..."
    sleep 5
    docker compose exec tidb mysql -h 127.0.0.1 -P 4000 -u root -e "SELECT 1" 2>/dev/null || sleep 15
else
    echo "      Docker services already running."
fi

# ── Step 3: Backend dependencies ────────────────
echo "[3/6] Installing backend dependencies..."
cd backend
uv sync 2>/dev/null || echo -e "      ${YELLOW}[WARN] uv sync failed.${NC}"
cd "$PROJECT_DIR"

# ── Step 4: Frontend dependencies ───────────────
echo "[4/6] Installing frontend dependencies..."
cd frontend
npm install 2>/dev/null || echo -e "      ${YELLOW}[WARN] npm install failed.${NC}"
cd "$PROJECT_DIR"

# ── Step 5: Start services ──────────────────────
echo "[5/6] Starting servers..."

# Detect terminal emulator
TERMINAL_CMD=""
for term in gnome-terminal konsole xterm; do
    if command -v "$term" &>/dev/null; then
        TERMINAL_CMD="$term"
        break
    fi
done

run_in_terminal() {
    local title="$1"
    local cmd="$2"
    if [ -n "$TERMINAL_CMD" ]; then
        case "$TERMINAL_CMD" in
            gnome-terminal)  gnome-terminal --title="$title" -- bash -c "$cmd; exec bash" ;;
            konsole)         konsole --new-tab -p tab-title="$title" -e bash -c "$cmd; exec bash" ;;
            xterm)           xterm -title "$title" -e bash -c "$cmd; exec bash" ;;
        esac
    else
        bash -c "$cmd" &
    fi
}

echo "      Starting API server (port 8000)..."
run_in_terminal "E-Room API" "cd '$PROJECT_DIR/backend' && uv run python -m app.server"

echo "      Starting Celery worker..."
run_in_terminal "E-Room Celery Worker" "cd '$PROJECT_DIR/backend' && uv run celery -A app.infrastructure.celery.celery_app worker --loglevel=info"

echo "      Starting Celery beat..."
run_in_terminal "E-Room Celery Beat" "cd '$PROJECT_DIR/backend' && uv run celery -A app.infrastructure.celery.celery_app beat --loglevel=info"

echo "      Starting Frontend (port 3000)..."
run_in_terminal "E-Room Frontend" "cd '$PROJECT_DIR/frontend' && npm run dev"

sleep 5

# ── Step 6: Open browser ────────────────────────
echo "[6/6] Opening http://localhost:3000 ..."
xdg-open http://localhost:3000 2>/dev/null || true

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  All services started!${NC}"
echo ""
echo "  API:        http://localhost:8000"
echo "  Frontend:   http://localhost:3000"
echo "  Swagger:    http://localhost:8000/docs"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "Commands: L=logs, S=status, R=restart, D=down, Q=quit"

while true; do
    read -r -n 1 -p "Command: " cmd
    echo ""
    case "$cmd" in
        [Ll]) docker compose logs --tail=50 -f ;;
        [Ss]) docker compose ps ;;
        [Rr]) docker compose restart api ;;
        [Dd]) docker compose down ;;
        [Qq]) exit 0 ;;
        *) echo "Unknown command" ;;
    esac
done
