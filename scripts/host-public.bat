@echo off
title E-Room Public Hosting
cd /d "%~dp0.."

echo ============================================
echo   E-Room Public Hosting (Tailscale Funnel)
echo ============================================
echo.

set "TS=C:\Program Files\Tailscale\tailscale.exe"

REM -- Step 1: Docker Desktop ---------------------------------------
echo [1/4] Checking Docker...
docker ps >nul 2>&1
if %errorlevel% neq 0 (
    echo        Docker not running. Starting Docker Desktop...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    echo        Waiting 60s for Docker to boot...
    timeout /t 60 /nobreak >nul
    docker ps >nul 2>&1
    if %errorlevel% neq 0 (
        echo        [ERROR] Docker still not ready. Start it manually, then re-run.
        pause
        exit /b 1
    )
)
echo        Docker OK.

REM -- Step 2: Stack --------------------------------------------------
echo [2/4] Starting containers (api, workers, db, livekit, frontend, caddy)...
docker compose up -d
if %errorlevel% neq 0 (
    echo        [ERROR] docker compose failed.
    pause
    exit /b 1
)

REM -- Step 3: Wait for Caddy ------------------------------------------
echo [3/4] Waiting for reverse proxy :8080 ...
for /l %%i in (1,1,24) do (
    powershell -NoProfile -Command "try { Invoke-WebRequest -Uri 'http://localhost:8080/api/v1/rooms/count' -TimeoutSec 5 | Out-Null; exit 0 } catch { exit 1 }"
    if %errorlevel% equ 0 goto :caddy_ok
    timeout /t 5 /nobreak >nul
)
echo        [ERROR] Caddy/API not responding after 2 minutes. Check: docker compose logs api caddy
pause
exit /b 1
:caddy_ok
echo        Caddy + API OK.

REM -- Step 4: Tailscale Funnel -----------------------------------------
echo [4/4] Opening public link...
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
echo             + docker compose stop caddy frontend
echo ============================================
echo.
pause
