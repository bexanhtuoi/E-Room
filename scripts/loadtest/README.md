# Load test E-Room

Cài 1 lần: `winget install GrafanaLabs.k6`, tải `lk.exe`
(từ `github.com/livekit/livekit-cli/releases`, file `lk_*_windows_amd64.zip`)
bỏ vào `scripts/loadtest/bin/`.

Chạy 1 lệnh duy nhất:

```bat
scripts\loadtest\run.bat --users 50 --minutes 5 [--speakers 3] [--room ID]
```

## Nó làm gì

1. `pick_room.py` — chọn 1 phòng public (qua API) làm phòng voice.
2. `lk.exe load-test` (chạy nền) — N người nói giả vào phòng đó qua WebRTC local (`ws://localhost:7880`).
   Test LiveKit SFU + webhook join/leave + presence + transcriber join room.
3. `k6 run` — VU mô phỏng 5 hành vi theo tỉ trọng: lurker 40%, chatter 30%,
   hopper 15%, reader 12%, còn lại đọc linh tinh. Mỗi vòng sleep 3-15s
   (0,1 req/s/user như case k6 chuẩn). 50% request phòng rơi vào phòng voice
   để giữ presence cho transcriber.

## Đọc kết quả

- k6 in `checks` (> 98%) + `bad_status` (< 5) + `http_req_duration` (p95 < 500ms).
  `403 ROOM_FULL` khi join (phòng 4 ghế) là hành vi đúng, đếm riêng ở `room_full`.
  Fail threshold = exit code != 0.
- Grafana `http://localhost:8092` (dashboard eroom-red): RPS, p50/p95,
  CPU/RAM api/worker/transcriber/db.

## Giới hạn đã biết

- Transcript text chỉ chảy khi STT sống (`STT_PROVIDER=whisper_server`
  cần máy `.65`, hoặc bật `STT_LOCAL_ENABLED=true`). STT chết thì leg voice
  vẫn test được SFU + wiring, không có chữ transcript.
- Lần chạy đầu setup đăng ký tới 100 user `k6_N@gmail.com` (tái dùng các lần sau).
  Rate limit register hiện 100/giờ/IP — chạy dày hơn thì nới tạm rồi trả về.
- `bin/lk.exe` không commit (96MB) — tải theo hướng dẫn trên, `run.bat` tự tìm trong `bin/`.
