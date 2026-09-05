#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

echo "============================================"
echo "  E-Room Launcher (macOS)"
echo "============================================"
echo ""

# ── Step 1: env ───────────────────────────────────
echo "[1/5] Checking backend env..."
if [ ! -f backend/.env ]; then
    cp backend/.env.example backend/.env
    echo "      Created backend/.env — edit LLM/LiveKit as needed."
else
    echo "      backend/.env exists, skipping."
fi

# ── Step 2: full stack ────────────────────────────
echo "[2/5] Starting full stack (api, workers, db, livekit, frontend)..."
docker compose up -d

# ── Step 3: migrate ───────────────────────────────
echo "[3/5] Running DB migrations..."
sleep 15
(cd backend && uv run alembic upgrade head) || echo "      [WARN] migrate failed — TiDB may not be ready yet."

# ── Step 4: URLs ──────────────────────────────────
echo "[4/5] Done."
echo ""
echo "============================================"
echo "  Frontend:  http://localhost:3000  (docker prod build)"
echo "  Dev mode:  cd frontend && npm run dev  (use another port)"
echo "  API docs:  http://localhost:8000/docs"
echo "============================================"
echo ""
echo "Commands: L=logs, S=status, R=restart api, D=down, Q=quit"

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
