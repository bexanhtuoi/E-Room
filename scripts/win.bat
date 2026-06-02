@echo off
title E-Room Dev Mode
cd /d "%~dp0.."

echo ============================================
echo   E-Room Development Launcher
echo ============================================
echo.

REM ── Step 1: Check .env ──────────────────────────
if not exist backend\.env (
    echo [1/6] Copying .env.example to .env...
    copy backend\.env.example backend\.env >nul
    echo        Created backend\.env — edit LLM_BASE_URL before starting.
) else (
    echo [1/6] .env already exists, skipping.
)

REM ── Step 2: Docker infra ────────────────────────
echo [2/6] Checking Docker infrastructure...
docker ps --format "{{.Names}}" 2>nul | findstr /C:"e_room_tidb" >nul
if %errorlevel% neq 0 (
    echo        Starting Docker services: tidb, redis, minio, livekit, coturn...
    docker compose up -d tidb redis minio livekit coturn
    echo        Waiting for TiDB to be ready (this may take 20-30s first time)...
    timeout /t 5 /nobreak >nul
    docker compose exec tidb mysql -h 127.0.0.1 -P 4000 -u root -e "SELECT 1" 2>nul
    if %errorlevel% neq 0 (
        timeout /t 15 /nobreak >nul
    )
    if %errorlevel% neq 0 (
        echo        [ERROR] Docker failed to start. Is Docker Desktop running?
        pause
        exit /b 1
    )
    echo        Waiting for services to be ready...
    timeout /t 8 /nobreak >nul
) else (
    echo        Docker services already running.
)

REM ── Step 3: Backend dependencies ────────────────
echo [3/6] Installing backend dependencies...
cd backend
uv sync 2>nul
if %errorlevel% neq 0 (
    echo        [WARN] uv sync failed — may need manual install.
)
cd ..

REM ── Step 4: Frontend dependencies ───────────────
echo [4/6] Installing frontend dependencies...
cd frontend
call npm install 2>nul
cd ..

REM ── Step 5: Start services ──────────────────────
echo [5/6] Starting servers...

echo        Starting API server (port 8000)...
start "E-Room API" cmd /c "cd /d "%CD%\backend" && uv run python -m app.server"

echo        Starting Celery worker...
start "E-Room Celery Worker" cmd /c "cd /d "%CD%\backend" && uv run celery -A app.infrastructure.celery.celery_app worker --loglevel=info"

echo        Starting Celery beat...
start "E-Room Celery Beat" cmd /c "cd /d "%CD%\backend" && uv run celery -A app.infrastructure.celery.celery_app beat --loglevel=info"

echo        Starting Frontend (port 3000)...
start "E-Room Frontend" cmd /c "cd /d "%CD%\frontend" && npm run dev"

timeout /t 5 /nobreak >nul

REM ── Step 6: Open browser ────────────────────────
echo [6/6] Opening http://localhost:3000 ...
start http://localhost:3000

echo.
echo ============================================
echo   All services started!
echo.
echo   API:        http://localhost:8000
echo   Frontend:   http://localhost:3000
echo   Swagger:    http://localhost:8000/docs
echo.
echo   Commands:
echo     [L] View Docker logs
echo     [S] Docker status
echo     [D] Docker compose down
echo     [Q] Quit
echo ============================================
echo.

:menu
choice /c LSRDQ /n /m "Command (L=logs, S=status, R=restart, D=down, Q=quit): "
if errorlevel 5 exit /b 0
if errorlevel 4 (
    docker compose down
    goto menu
)
if errorlevel 3 (
    docker compose restart api
    goto menu
)
if errorlevel 2 (
    docker compose ps
    goto menu
)
if errorlevel 1 (
    docker compose logs --tail=50 -f
    goto menu
)
