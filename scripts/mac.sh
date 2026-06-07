#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

echo "============================================"
echo "  E-Room Development Launcher"
echo "============================================"
echo ""

# ── Step 1: Check .env ──────────────────────────
echo "[1/6] Checking .env..."
if [ ! -f backend/.env ]; then
    cp backend/.env.example backend/.env
    echo "      Created backend/.env — edit LLM_BASE_URL before starting."
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
uv sync 2>/dev/null || echo "      [WARN] uv sync failed."
cd "$PROJECT_DIR"

# ── Step 4: Frontend dependencies ───────────────
echo "[4/6] Installing frontend dependencies..."
cd frontend
npm install 2>/dev/null || echo "      [WARN] npm install failed."
cd "$PROJECT_DIR"

# ── Step 5: Start services ──────────────────────
echo "[5/6] Starting servers..."
echo "      Starting API server (port 8000)..."
osascript -e "tell app \"Terminal\" to do script \"cd '$PROJECT_DIR/backend' && uv run python -m app.server\"" 2>/dev/null || \
    xterm -e "cd '$PROJECT_DIR/backend' && uv run python -m app.server" &

echo "      Starting Frontend (port 3000)..."
osascript -e "tell app \"Terminal\" to do script \"cd '$PROJECT_DIR/frontend' && npm run dev\"" 2>/dev/null || \
    xterm -e "cd '$PROJECT_DIR/frontend' && npm run dev" &

sleep 5

# ── Step 6: Open browser ────────────────────────
echo "[6/6] Opening http://localhost:3000 ..."
open http://localhost:3000 2>/dev/null || xdg-open http://localhost:3000 2>/dev/null || true

echo ""
echo "============================================"
echo "  All services started!"
echo ""
echo "  API:        http://localhost:8000"
echo "  Frontend:   http://localhost:3000"
echo "  Swagger:    http://localhost:8000/docs"
echo "============================================"
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
