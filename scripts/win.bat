@echo off
title E-Room Launcher
cd /d "%~dp0.."

echo ============================================
echo   E-Room Launcher (Windows)
echo ============================================
echo.

REM -- Step 1: env --------------------------------------------
echo [1/5] Checking backend env...
if not exist backend\.env (
    copy backend\.env.example backend\.env >nul
    echo        Created backend\.env — sua LLM/LiveKit theo nhu cau.
) else (
    echo        backend\.env exists, skipping.
)

REM -- Step 2: full stack --------------------------------------
echo [2/5] Starting full stack (api, workers, db, livekit, frontend)...
docker compose up -d
if %errorlevel% neq 0 (
    echo        [ERROR] docker compose failed. Is Docker Desktop running?
    pause
    exit /b 1
)

REM -- Step 3: migrate -----------------------------------------
echo [3/5] Running DB migrations...
timeout /t 15 /nobreak >nul
cd backend
uv run alembic upgrade head 2>nul
if %errorlevel% neq 0 (
    echo        [WARN] migrate failed — TiDB co the chua ready, thu lai sau.
)
cd ..

REM -- Step 4: URLs --------------------------------------------
echo [4/5] Done.
echo.
echo ============================================
echo   Frontend:  http://localhost:3000  (docker prod build)
echo   Dev mode:  cd frontend ^&^& npm run dev  (port 3002 de tranh prod)
echo   API docs:  http://localhost:8000/docs
echo.
echo   Public sharing: scripts\host-public.bat (Tailscale Funnel)
echo ============================================
echo.
echo   Commands:
echo     [L] View logs   [S] Status   [R] Restart api   [D] Down   [Q] Quit
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
