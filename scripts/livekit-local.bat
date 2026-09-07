@echo off
title E-Room - LiveKit LOCAL
cd /d "%~dp0.."

echo ============================================
echo   LiveKit -^> LOCAL (docker livekit:7880)
echo ============================================
echo.

echo [1/4] Set LIVEKIT_MODE=local trong backend\.env.docker...
powershell -NoProfile -Command "(Get-Content backend\.env.docker) -replace '^LIVEKIT_MODE=.*','LIVEKIT_MODE=local' | Set-Content backend\.env.docker"
findstr /B "LIVEKIT_MODE=" backend\.env.docker
echo.

echo [2/4] Start container livekit local...
docker compose up -d livekit
echo.

echo [3/4] Recreate api de nap env moi (restart khong nap env)...
docker compose up -d api
timeout /t 20 /nobreak >nul
echo.

echo [4/4] Verify: tao token thu bang dung key dang chay...
docker exec api uv run python -c "from app.config import settings; from app.integration.livekit import create_token; print('MODE:', settings.livekit_mode); print('URL :', settings.livekit_url); print('TOKEN_OK:', len(create_token('probe','1')) > 50)"
if errorlevel 1 (
  echo        [FAIL] api chua len hoac key sai. Thu: docker logs api --tail 20
) else (
  echo        [OK] Xong. Vao phong thu mic/cam tren LAN.
)
