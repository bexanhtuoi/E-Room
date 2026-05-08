@echo off
setlocal enabledelayedexpansion
title E-Room Launcher
cd /d "%~dp0"

echo.
echo  ============================================
echo    E-Room - Realtime English Speaking Rooms
echo  ============================================
echo.

:: ── 1. Check Docker ──────────────────────────────────
echo  [*] Checking Docker...
docker info >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  [!] Docker is not running.
    echo.
    echo  Starting Docker Desktop...
    echo  (This may take 30-90 seconds on first launch)
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    echo.
    echo  Waiting for Docker engine...
    set /a attempts=0
    :wait_docker
        timeout /t 3 /nobreak >nul
        set /a attempts+=1
        docker info >nul 2>&1
        if !ERRORLEVEL! NEQ 0 (
            if !attempts! LSS 40 (
                <nul set /p "=."
                goto wait_docker
            )
            echo.
            echo  [!!!] Docker did not start in time.
            echo         Please start Docker Desktop manually and re-run run.bat
            echo.
            pause
            exit /b 1
        )
    echo.
    echo  [+] Docker is ready.
) else (
    echo  [+] Docker is running.
)

:: ── 2. Pull images & build ───────────────────────────
echo.
echo  [*] Building and starting all services...
echo      (First run downloads images - this may take a few minutes)
echo.
docker compose up -d --build --remove-orphans

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [!!!] Failed to start services.
    echo         Check the errors above.
    pause
    exit /b 1
)

:: ── 3. Wait for services ─────────────────────────────
echo.
echo  [*] Waiting for services to be ready...
echo      Starting: Redis -> Postgres -> MinIO -> LiveKit -> TURN -> API -> Frontend
echo.
set /a ticks=0
:wait_services
    timeout /t 2 /nobreak >nul
    set /a ticks+=1
    <nul set /p "=."
    if !ticks! GEQ 30 goto services_timeout

    :: Check if API is responding
    curl -s -o NUL http://localhost:8000/health 2>nul
    if !ERRORLEVEL! NEQ 0 goto wait_services

    :: Check if frontend is responding
    curl -s -o NUL http://localhost:3000 2>nul
    if !ERRORLEVEL! NEQ 0 goto wait_services

:: ── 4. Launch ────────────────────────────────────────
:services_ready
echo.
echo.
echo  ============================================
echo    E-Room is LIVE!
echo  ============================================
echo.
echo    Frontend : http://localhost:3000
echo    API      : http://localhost:8000/docs
echo    Nginx    : http://localhost
echo    MinIO    : http://localhost:9001
echo.
echo    Opening browser to the app...
start http://localhost:3000
goto show_menu

:services_timeout
echo.
echo  [*] Services may still be starting...
echo      If the browser shows an error, wait 30s and refresh.

start http://localhost:3000

:: ── 5. Main menu ─────────────────────────────────────
:show_menu
echo.
echo  ============================================
echo    COMMANDS
echo  ============================================
echo.
echo    [L] View live logs      [S] Status
echo    [R] Restart services    [D] Stop & Exit
echo    [Q] Quit (keep running)
echo.
echo    App running at: http://localhost:3000
echo.
set /p choice="    Your choice: "

if /i "%choice%"=="L" (
    docker compose logs -f --tail=50
    goto show_menu
)
if /i "%choice%"=="S" (
    docker compose ps
    pause
    goto show_menu
)
if /i "%choice%"=="R" (
    docker compose down
    docker compose up -d --build --remove-orphans
    goto show_menu
)
if /i "%choice%"=="D" (
    echo.
    echo  [*] Stopping all services...
    docker compose down
    echo  [+] All services stopped.
    echo.
    pause
    exit /b 0
)
if /i "%choice%"=="Q" (
    echo.
    echo  [+] Services still running in background.
    echo      Use 'docker compose down' to stop them later.
    echo.
    exit /b 0
)

goto show_menu
