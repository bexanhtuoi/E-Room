@echo off
REM Load test E-Room: k6 API (da hanh vi) + lk voice matrix (nhieu room, nhieu speakers).
REM Dung: scripts\loadtest\run.bat --users 50 --minutes 5 [--speakers 1,4,6] [--voice-rooms 3] [--room-size 6] [--room ID]

set USERS=50
set MINUTES=5
set SPEAKERS=1,4,6
set VROOMS=3
set ROOMSIZE=6
set ROOM=

:parse
if "%~1"=="" goto done_parse
if "%~1"=="--users" call :take USERS %~2
if "%~1"=="--minutes" call :take MINUTES %~2
if "%~1"=="--speakers" call :take SPEAKERS %~2
if "%~1"=="--voice-rooms" call :take VROOMS %~2
if "%~1"=="--room-size" call :take ROOMSIZE %~2
if "%~1"=="--room" call :take ROOM %~2
shift
shift
goto parse
goto done_parse

:take
set %~1=%~2
goto :eof

:done_parse
set DURATION=%MINUTES%m
set /a DURATION_S=%MINUTES%*60

if "%ROOM%"=="" (
  for /f "tokens=1,2 delims=|" %%i in ('backend\.venv\Scripts\python.exe scripts\loadtest\pick_room.py %VROOMS% %ROOMSIZE%') do (
    set ROOM=%%i
    set LK_SECRET=%%j
  )
)
if "%ROOM%"=="" (
  echo Khong tim thay/tao duoc phong voice nao.
  exit /b 1
)
if "%LK_SECRET%"=="" (
  for /f %%j in ('backend\.venv\Scripts\python.exe scripts\loadtest\pick_room.py secret') do set LK_SECRET=%%j
)
if "%LK_SECRET%"=="" (
  echo Khong doc duoc LiveKit secret tu backend\livekit.yaml.
  exit /b 1
)
echo Voice rooms: %ROOM% - VU: %USERS% - Phut: %MINUTES%
echo Chuan bi pool %USERS% users...
backend\.venv\Scripts\python.exe scripts\loadtest\ensure_pool.py %USERS%
if errorlevel 1 (
  echo Pool that bai, dung lai.
  exit /b 1
)

for /f "tokens=1,2" %%a in ('backend\.venv\Scripts\python.exe scripts\loadtest\voice_plan.py %ROOM% %SPEAKERS%') do (
  start /b "" scripts\loadtest\bin\lk.exe load-test --url ws://localhost:7880 --api-key eroom-livekit --api-secret %LK_SECRET% --room %%a --audio-publishers %%b --simulate-speakers --duration %DURATION% --num-per-second 2 > lk-voice-%%a.log 2>&1
)
where k6 >nul 2>&1
if errorlevel 1 set PATH=%PATH%;C:\Program Files\k6

k6 run -e USERS=%USERS% -e DURATION=%DURATION% -e DURATION_S=%DURATION_S% -e VOICE_ROOMS=%ROOM% -e POOL=%USERS% scripts\loadtest\k6-api.js

for %%r in (%ROOM%) do backend\.venv\Scripts\python.exe scripts\loadtest\pick_room.py leave %%r >nul 2>&1
echo Xong. Xem Grafana http://localhost:8092 (dashboard eroom-red): RPS, p50/p95, worker CPU/RAM.
