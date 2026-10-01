# E-Room — Setup

> Cập nhật: 09/2026 · 3 cách chạy: dev local, full docker, public qua Tailscale.

## 1. Yêu cầu

- Docker Desktop (Windows/macOS) hoặc Engine (Linux), RAM ≥ 16GB khuyến nghị (STT/scoring ăn CPU/RAM).
- Node.js 22+, Python 3.13 + `uv`.
- Tài khoản Tailscale free (chỉ khi muốn public).
- Tài khoản LiveKit Cloud free (chỉ khi muốn media qua Cloud, khuyến nghị khi public).
- Máy AI riêng có GPU NVIDIA (chỉ khi muốn STT/TTS server `:8001/:8002`).

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

AI ngoài (LLM/STT/TTS) trỏ qua `LLM_BASE_URL`, `STT_PROVIDER` + `STT_SERVER_BASE_URL`, `TTS_BASE_URL` — xem bảng biến ở `README.md`.

## 3. Chạy dev local

```bash
# Terminal 1: stack backend (api, workers, db, livekit self-host...)
docker compose up -d
cd backend && uv run alembic upgrade head

# Terminal 2: frontend dev
cd frontend && npm install && npm run dev
```

Hoặc 1 lệnh: `scripts\dev.bat` (Windows) / `bash scripts/mac.sh` / `bash scripts/linux.sh`.
Mở `http://localhost:3001` (prod container) hoặc `http://localhost:8080` (prod qua nginx). Dev hot reload: `cd frontend && npm run dev` → `https://localhost:3000` (Chrome báo cert tự ký thì Advanced → Proceed). Swagger: `http://localhost:8000/docs`.

`dev.bat` còn làm thêm: copy `backend/.env` nếu thiếu, ép `LIVEKIT_MODE=local`, `tailscale funnel reset` (tắt public), migrate + verify token LiveKit local.

## 4. Public cho người ngoài (đang dùng thật)

Điều kiện: PC bật + Docker chạy + Tailscale login.

```bash
# 1 lệnh duy nhất (Windows):
scripts\golive.bat
```

Script tự: đợi Docker → `LIVEKIT_MODE=cloud` → `compose up -d` → stop livekit self-host + recreate api/workers/beat → migrate + verify Cloud → đợi API → `tailscale funnel --bg 8080` → in link `https://<máy>.<tailnet>.ts.net/`.

Tự động sau reboot (chạy 1 lần):

```cmd
schtasks /create /tn "E-Room Public" /tr "C:\...\E-Room\scripts\golive.bat" /sc onlogon /rl highest /f
```

Kiến trúc public: Funnel (TLS) → Nginx `:8080` (`/` static, `/api` api timeout 600s, `/rtc*` livekit) + media qua LiveKit Cloud. Khách không cài gì. Nhớ thêm webhook URL `https://<máy>.<tailnet>.ts.net/api/v1/rooms/livekit/webhook` trong dashboard Cloud project (thay `<máy>.<tailnet>` bằng Funnel thật của bạn).

## 5. Ports tham khảo

`3001` web prod (container) · `8080` web prod (nginx) · `3000` web dev (https, cert tự ký) · `8000` api · `7880` livekit signal + `UDP 50000–50100` media (chỉ cần nếu self-host media) · `11434` ollama · `8014` reranker · `6333` qdrant · `4000` tidb · `6379` redis · `9000/9001` minio · `8001/8002` STT/TTS (máy AI riêng, không trong compose này).

## 6. Tests

```bash
cd backend
uv run pytest tests/unit tests/api -q        # nhanh
uv run pytest tests/ -q                      # full
cd ../frontend
npm run build && npx vitest run              # build + unit
```

Guard kiến trúc: `tests/unit/test_architecture.py` quét AST — routers cấm `HTTPException`/DB trực tiếp/import `app.ai`, cấm import ngược tầng. Refactor làm vỡ tầng là test đỏ ngay.

## 6b. Giả lập user (đổ số liệu cho Grafana)

```bash
cd backend
uv run python scripts/load_simulator.py --users 3 --interval 4   # chạy mãi đến Ctrl+C
uv run python scripts/load_simulator.py --users 5 --minutes 10 --with-ai --bad-rate 0.1
```

Mỗi user ảo: xem rooms → join → đọc chat → gửi 1-3 tin → leave, lặp lại.
Mặc định không gọi `@ai` (tốn quota) và không chấm điểm (tốn CPU);
`--with-ai` bật hỏi AI thưa, `--bad-rate` tạo lỗi 4xx cho panel Error.

## 7. Troubleshooting (từ case thật)

| Hiện tượng | Nguyên nhân / Fix |
|---|---|
| `@ai` chỉ "thinking" rồi ra 1 cục | Tab mất LiveKit (không stream live, chỉ poll DB). F12 xem console có `Invalid URL` |
| `Failed to join room (invalid API key)` | Server cầm keys cũ — `docker restart livekit` (yaml mount cần restart mới nạp) |
| Vào được mà không mic/cam, vài giây văng | ICE/media chết (log: JOIN mà không ACTIVE) → dùng LiveKit Cloud, đừng self-host media |
| Mic/cam báo lỗi thiết bị | Lỗi phía browser: chưa cấp quyền / không có thiết bị / bị app khác giữ / mở trong Zalo-FB (phải dùng Chrome/Safari) |
| Điện thoại không share được màn hình | Giới hạn nền tảng (iOS Safari, Chrome Android không có `getDisplayMedia`) — dùng PC |
| List hiện người đã out | Đợi 5–10s (refresh interval); kẹt lâu = webhook miss → bấm Reload, có endpoint join/leave dự phòng |
| Worker `Unknown column` | Code worker cũ hơn migration — `docker restart ai-worker` (code bind-mount) |
| STT im re sau restart worker | Task nghe dở bị giết, beat 60s tự hồi (`ensure-room-workers`) |
| Score treo ở "queued" mãi | Worker queue `ai` chết hoặc Redis chết — `docker ps`, restart ai-worker/redis |
| `/feedback` lỗi | LLM server (`LLM_BASE_URL`) chưa chạy — điểm số vẫn chấm bình thường, chỉ nhận xét AI là không chạy |
| Điểm từng chữ không hiện | Đúng thiết kế — bấm **Thống kê điểm số** để mở bảng riêng (`reading-score.md`) |
| Test báo constraint lạ | Xóa `backend/test_eroom.db` chạy lại (sqlite dùng chung) |
| Văng khi cùng tài khoản 2 máy | LiveKit đá session cũ (duplicate identity) — dùng 2 tài khoản khác nhau |
| Funnel 502 | Serve/funnel trỏ sai port — `serve reset` + cấu hình lại paths rồi `funnel --bg <port>` |
