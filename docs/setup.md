# E-Room — Setup

> Version: v2.0.0 · 3 cách chạy: dev local, full docker, public qua Tailscale.

## 1. Yêu cầu

- Docker Desktop (Windows/macOS) hoặc Engine (Linux), RAM ≥ 16GB khuyến nghị (llama + whisper ăn RAM/CPU).
- Node.js 22+, Python 3.13 + `uv`.
- Tài khoản Tailscale free (chỉ khi muốn public).
- Tài khoản LiveKit Cloud free (chỉ khi muốn media qua Cloud, khuyến nghị khi public).

## 2. Env (quan trọng nhất)

```bash
cp backend/.env.example backend/.env
```

Mở `backend/.env.example` — đầy đủ từng biến, chia 2 profile LiveKit:

| Profile | Khi nào | Đổi gì |
|---|---|---|
| **LOCAL** (mặc định) | Dev, LAN | Chạy `scripts\dev.bat` |
| **CLOUD** (public) | Khách ngoài internet | Chạy `scripts\golive.bat` |

Cả 2 cụm local/cloud nằm sẵn trong `backend/.env.docker`, chọn bằng 1 biến `LIVEKIT_MODE=local|cloud` — script tự đổi + recreate api + tạo token thử để verify. Không sửa tay từng dòng nữa.

Bắt buộc đổi trước khi public: `SECRET_KEY`, `LIVEKIT_API_KEY/SECRET` (random 32+ ký tự). MinIO/TiDB/Redis không password nhưng **chỉ listen nội bộ, không forward ra ngoài**.

## 3. Chạy dev local

```bash
# Terminal 1: stack backend (api, workers, db, livekit self-host...)
docker compose up -d
cd backend && uv run alembic upgrade head

# Terminal 2: frontend dev (port 3002 để tránh đụng prod :3000)
cd frontend && npm install && npm run dev -- --port 3002 --strictPort
```

Hoặc 1 lệnh: `scripts\dev.bat` (Windows) / `bash scripts/mac.sh` / `bash scripts/linux.sh`.
Mở `https://localhost:3002` (dev, phím F trong dev.bat — Chrome báo cert tự ký thì Advanced → Proceed) hoặc `http://localhost:8080` (prod qua nginx). Swagger: `http://localhost:8000/docs`. Cổng 3000 container KHÔNG mở ra host.

## 4. Public cho người ngoài (đang dùng thật)

Điều kiện: PC bật + Docker chạy + Tailscale login.

```bash
# 1 lệnh duy nhất (Windows):
scripts\golive.bat
```

Script tự: mở Docker → MODE=cloud → `compose up -d` → recreate api/workers → đợi API → `tailscale funnel --bg 8080` → in link `https://<may>.<tailnet>.ts.net/`.

Tự động sau reboot (chạy 1 lần):

```cmd
schtasks /create /tn "E-Room Public" /tr "C:\...\E-Room\scripts\golive.bat" /sc onlogon /rl highest /f
```

Kiến trúc public: Funnel (TLS) → Nginx `:8080` (`/` static, `/api` api, `/rtc*` livekit) + media qua LiveKit Cloud. Khách không cài gì. Nhớ thêm webhook URL `https://eroom.tail9f35e1.ts.net/api/v1/rooms/livekit/webhook` trong dashboard Cloud project.

## 5. Ports tham khảo

`8080` web prod (nginx) · `3002` web dev (https, cert tự ký) · `8000` api · `7880` livekit signal · `UDP 50000–50100` media (chỉ cần nếu self-host media) · `8012/8013` llama · `6333` qdrant · `4000` tidb · `6379` redis · `9000` minio. Cổng 3000 container KHÔNG mở ra host.

## 6. Tests

```bash
cd backend
uv run pytest tests/unit tests/api -q        # nhanh
uv run pytest tests/ -q                      # full
cd ../frontend
npm run build && npx vitest run              # build + unit
```

## 7. Troubleshooting (từ case thật)

| Hiện tượng | Nguyên nhân / Fix |
|---|---|
| `@ai` chỉ "thinking" rồi ra 1 cục | Tab mất LiveKit (không stream live, chỉ poll DB). F12 xem console có `Invalid URL` |
| `Failed to join room (invalid API key)` | Server cầm keys cũ — `docker restart livekit` (yaml mount cần restart mới nạp) |
| Vào được mà không mic/cam, vài giây văng | ICE/media chết (log: JOIN mà không ACTIVE) → dùng LiveKit Cloud, đừng self-host media |
| Mic/cam báo lỗi thiết bị | Lỗi phía browser: chưa cấp quyền / không có thiết bị / bị app khác giữ / mở trong Zalo-FB (phải dùng Chrome/Safari) |
| Điện thoại không share được màn hình | Giới hạn nền tảng (iOS Safari, Chrome Android không có `getDisplayMedia`) — dùng PC |
| List hiện người đã out | Đợi 5–10s (refresh interval); kẹt lâu = webhook miss → bấm Reload, có endpoint leave dự phòng |
| Worker `Unknown column` | Code worker cũ hơn migration — `docker restart ai-worker` |
| STT im re sau restart worker | Task nghe dở bị giết, beat 60s tự hồi (`ensure-room-workers`) |
| Test báo constraint lạ | Xóa `backend/test_eroom.db` chạy lại (sqlite dùng chung) |
| Văng khi cùng tài khoản 2 máy | LiveKit đá session cũ (duplicate identity) — dùng 2 tài khoản khác nhau |
| Funnel 502 | Serve/funnel trỏ sai port — `serve reset` + cấu hình lại paths rồi `funnel --bg <port>` |
