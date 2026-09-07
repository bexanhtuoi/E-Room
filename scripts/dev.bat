@echo off
title E-Room DEV (local)
cd /d "%~dp0.."

echo ============================================
echo   E-Room DEV - chay local, media noi bo
echo ============================================
echo.

REM -- Step 1: env --------------------------------------------
echo [1/5] Checking backend env...
if not exist backend\.env (
    copy backend\.env.example backend\.env >nul
    echo        Created backend\.env.
) else (
    echo        backend\.env exists, skipping.
)

REM -- Step 2: LiveKit local -----------------------------------
echo [2/5] Set LIVEKIT_MODE=local...
powershell -NoProfile -Command "(Get-Content backend\.env.docker) -replace '^LIVEKIT_MODE=.*','LIVEKIT_MODE=local' | Set-Content backend\.env.docker"
findstr /B "LIVEKIT_MODE=" backend\.env.docker

REM -- Step 3: full stack --------------------------------------
echo [3/5] Starting full stack (api, workers, db, livekit, frontend)...
docker compose up -d
if %errorlevel% neq 0 (
    echo        [ERROR] docker compose failed. Is Docker Desktop running?
    pause
    exit /b 1
)

REM -- Step 4: migrate -----------------------------------------
echo [4/5] Running DB migrations...
timeout /t 15 /nobreak >nul
cd backend
uv run alembic upgrade head 2>nul
if %errorlevel% neq 0 (
    echo        [WARN] migrate failed - TiDB co the chua ready, thu lai sau.
)
cd ..

REM -- Step 5: verify ------------------------------------------
echo [5/5] Verify LiveKit local...
docker exec api uv run python -c "from app.config import settings; from app.integration.livekit import create_token; print('MODE:', settings.livekit_mode); print('URL :', settings.livekit_url); print('TOKEN_OK:', len(create_token('probe','1')) > 50)"
echo.
echo ============================================
echo   Web prod (container): http://localhost:3001
echo   Web qua nginx:        http://localhost:8080
echo   API docs:             http://localhost:8000/docs
echo   Hot reload: cd frontend ^&^& npm run dev  (https://localhost:3000)
echo ============================================
echo.
echo   Commands:
echo     [L] View logs   [S] Status   [R] Recreate api   [D] Down   [Q] Quit
echo ============================================
echo.

:menu
choice /c LSRDQ /n /m "Command (L=logs, S=status, R=recreate api, D=down, Q=quit): "
if errorlevel 5 exit /b 0
if errorlevel 4 (
    docker compose down
    goto menu
)
if errorlevel 3 (
    docker compose up -d --force-recreate api
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
