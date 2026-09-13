@echo off
title E-Room GO LIVE (public)
cd /d "%~dp0.."

echo ============================================
echo   E-Room GO LIVE - public qua Tailscale
echo ============================================
echo.

set "TS=C:\Program Files\Tailscale\tailscale.exe"

REM -- Step 1: Docker --------------------------------------------
echo [1/6] Checking Docker...
docker ps >nul 2>&1
if %errorlevel% equ 0 goto :docker_ok
echo        Docker not running. Starting Docker Desktop...
start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
echo        Waiting for Docker (toi da 15 phut, check moi 5s)...
for /l %%i in (1,1,180) do (
    timeout /t 5 /nobreak >nul
    docker ps >nul 2>&1
    if not errorlevel 1 goto :docker_ok
    echo        ... cho %%i/180 (Docker dang khoi dong)...
)
echo        [ERROR] Docker still not ready after 15 minutes. Start it manually, then re-run.
pause
exit /b 1
:docker_ok
echo        Docker OK.

REM -- Step 2: env -----------------------------------------------
echo [2/6] Checking backend env...
if not exist backend\.env (
    copy backend\.env.example backend\.env >nul
    echo        Created backend\.env.
)

REM -- Step 3: LiveKit cloud ---------------------------------------
echo [3/6] Set LIVEKIT_MODE=cloud...
powershell -NoProfile -Command "(Get-Content backend\.env.docker) -replace '^LIVEKIT_MODE=.*','LIVEKIT_MODE=cloud' | Set-Content backend\.env.docker"
findstr /B "LIVEKIT_MODE=" backend\.env.docker

REM -- Step 4: stack + recreate consumers ---------------------------
echo [4/6] Starting stack, api + workers nap env Cloud...
docker compose up -d
if %errorlevel% neq 0 (
    echo        [ERROR] docker compose failed.
    pause
    exit /b 1
)
docker compose stop livekit
docker compose up -d --force-recreate api ai-worker ai-observer ai-transcriber ai-beat
timeout /t 20 /nobreak >nul

REM -- Step 5: migrate + verify --------------------------------------
echo [5/6] Migrate + verify LiveKit Cloud...
cd backend
uv run alembic upgrade head 2>nul
cd ..
docker exec api uv run python -c "from app.config import settings; from app.integration.livekit import create_token; print('MODE:', settings.livekit_mode); print('URL :', settings.livekit_url); print('TOKEN_OK:', len(create_token('probe','1')) > 50)"
echo        Waiting for reverse proxy :8080 ...
for /l %%i in (1,1,24) do (
    powershell -NoProfile -Command "try { Invoke-WebRequest -Uri 'http://localhost:8080/api/v1/rooms/count' -TimeoutSec 5 | Out-Null; exit 0 } catch { exit 1 }"
    if %errorlevel% equ 0 goto :nginx_ok
    timeout /t 5 /nobreak >nul
)
echo        [ERROR] Nginx/API not responding after 2 minutes. Check: docker compose logs api nginx
pause
exit /b 1
:nginx_ok
echo        Nginx + API OK.

REM -- Step 6: Funnel -----------------------------------------------
echo [6/6] Opening public link...
if not exist "%TS%" (
    echo        [ERROR] Tailscale not found. Install it and login first.
    pause
    exit /b 1
)
"%TS%" funnel reset >nul 2>&1
"%TS%" funnel --bg 8080
if %errorlevel% neq 0 (
    echo        [ERROR] funnel failed. Is Tailscale logged in? Run: tailscale status
    pause
    exit /b 1
)

echo.
echo ============================================
echo   LIVE! Share this link:
echo   https://eroom.tail9f35e1.ts.net/
echo ============================================
echo   Keep this PC on. Closing this window is fine.
echo   To stop sharing: tailscale funnel reset
echo ============================================
echo.
pause
