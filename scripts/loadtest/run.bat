@echo off
REM Load test E-Room: k6 API (da hanh vi) + lk voice (nguoi noi that qua WebRTC).
REM Dung: scripts\loadtest\run.bat --users 50 --minutes 5 [--speakers 3] [--room ID]

set USERS=50
set MINUTES=5
set SPEAKERS=3
set ROOM=

:parse
if "%~1"=="" goto done_parse
if "%~1"=="--users" call :take USERS %~2
if "%~1"=="--minutes" call :take MINUTES %~2
if "%~1"=="--speakers" call :take SPEAKERS %~2
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

if "%ROOM%"=="" (
  for /f %%i in ('backend\.venv\Scripts\python.exe scripts\loadtest\pick_room.py') do set ROOM=%%i
)
if "%ROOM%"=="" (
  echo Khong tim thay phong public nao. Tao phong truoc roi chay lai.
  exit /b 1
)
for /f "tokens=2 delims=: " %%a in ('findstr /r "eroom-livekit:" backend\livekit.yaml') do set LK_SECRET=%%a
if "%LK_SECRET%"=="" (
  echo Khong doc duoc LiveKit secret tu backend\livekit.yaml.
  exit /b 1
)
echo Chuan bi pool %USERS% users...
backend\.venv\Scripts\python.exe scripts\loadtest\ensure_pool.py %USERS%
if errorlevel 1 (
  echo Pool that bai, dung lai.
  exit /b 1
)
echo Phong voice: %ROOM% - VU: %USERS% - Phut: %MINUTES% - Speakers: %SPEAKERS% - Duration: %DURATION%

start /b "" scripts\loadtest\bin\lk.exe load-test --url ws://localhost:7880 --api-key eroom-livekit --api-secret %LK_SECRET% --room %ROOM% --audio-publishers %SPEAKERS% --simulate-speakers --duration %DURATION% --num-per-second 2 > lk-voice.log 2>&1

where k6 >nul 2>&1
if errorlevel 1 set PATH=%PATH%;C:\Program Files\k6

k6 run --vus %USERS% --duration %DURATION% -e VOICE_ROOM=%ROOM% -e POOL=%USERS% scripts\loadtest\k6-api.js

echo Xong. Xem Grafana http://localhost:8092 (dashboard eroom-red): RPS, p50/p95, worker CPU/RAM.
