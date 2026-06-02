---
title: ERoom — Triển khai & Vận hành
tags:
  - deployment
  - devops
  - docker
  - ERoom
  - infrastructure
created: 2026-05-10
updated: 2026-06-02
---

# Triển khai & Vận hành

> [!abstract] Hướng dẫn triển khai ERoom
> Docker Compose setup, cấu hình từng service (LiveKit, coTURN, Nginx, Minio), quản lý biến môi trường, SSL, và quy trình deploy.

> [!info] Điều hướng nhanh
> [[ERoom/overview|← Tổng quan]] · [[ERoom/project-structure|Cấu trúc dự án →]] · [[ERoom/dev-notes|Dev Notes →]]

---

## 1. Docker Compose — Tổng quan

File: `docker-compose.yml` (root project)

### 1.1 Danh sách Services

| Service | Container | Ports | Mục đích |
|---------|-----------|-------|----------|
| `api` | `e-room-api-1` | 8000 | FastAPI backend |
| `celery_worker` | `e-room-celery_worker-1` | — | Xử lý tác vụ bất đồng bộ |
| `celery_beat` | `e-room-celery_beat-1` | — | Lập lịch định kỳ (matching 5s, cleanup) |
| `redis` | `e_room_redis` | 6379 | Queue, cache, pub/sub |
| `minio` | `e-room-minio-1` | 9000, 9001 | Object storage (RAG docs, TTS, avatars, evidence) |
| `minio_init` | — | — | Khởi tạo buckets (chạy 1 lần) |
| `livekit` | `e-room-livekit-1` | 7880-7881, 50000-50100/udp | WebRTC SFU |
| `coturn` | `e-room-coturn-1` | 3478 (TCP+UDP) | NAT traversal |
| `frontend` | `e_room_frontend` | 3000 | React SPA (dev) |
| `nginx` | `e-room-nginx-1` | 80 | Reverse proxy |

### 1.2 Service Dependencies

```mermaid
graph TD
    nginx --> api
    nginx --> frontend
    api --> redis
    api --> minio
    celery_worker --> redis
    celery_beat --> redis
    livekit --> redis
    minio_init --> minio
```

### 1.3 Health Checks

| Service | Check | Interval |
|---------|-------|----------|
| `redis` | `redis-cli ping` | 5s |
| Các service khác | Docker built-in | — |

---

## 2. Cấu hình từng Service

### 2.1 LiveKit (`livekit.yaml`)

```yaml
port: 7880
bind_addresses:
  - 0.0.0.0
rtc:
  tcp_port: 7881
  port_range_start: 50000
  port_range_end: 50100
  node_ip: 127.0.0.1          # ⚠️ Production: đổi thành public IP
keys:
  devkey: secret               # ⚠️ Production: đổi key + secret mạnh
redis:
  address: redis:6379
room:
  empty_timeout: 86400         # 24h — phòng "always-on"
  enable_remote_unmute: true
```

> [!warning] Production
> - `node_ip`: phải là public IP của server, không phải `127.0.0.1`
> - `keys`: dùng key/secret random 64+ ký tự
> - `port_range_start/end`: mở trên firewall (UDP)

### 2.2 coTURN (`turnserver.conf`)

```ini
listening-port=3478
fingerprint
use-auth-secret
static-auth-secret=change-me   # ⚠️ Production: đổi secret mạnh
realm=e-room.local             # ⚠️ Production: đổi thành domain thật
no-cli
lt-cred-mech
```

> [!warning] Production
> - `static-auth-secret`: random 64+ ký tự
> - `realm`: domain production (vd: `eroom.app`)
> - Mở cả TCP + UDP port 3478 trên firewall
> - Cân nhắc thêm TLS port 5349 cho production

### 2.3 Nginx (`nginx.conf`)

Reverse proxy chính:
- `/api/*` → FastAPI (port 8000)
- `/ws/*` → WebSocket (port 8000)
- `/*` → Frontend static (port 3000)

SSL config trong `nginx-ssl.conf` (dùng với certbot).

### 2.4 Minio + Bucket Init (`init-buckets.sh`)

```bash
#!/bin/sh
mc alias set local http://minio:9000 minioadmin minioadmin

# Tạo buckets
mc mb --ignore-existing local/ERoom-rag-docs
mc mb --ignore-existing local/ERoom-tts
mc mb --ignore-existing local/ERoom-avatars
mc mb --ignore-existing local/ERoom-evidence

# TTL policy cho TTS (24h) và evidence (30 ngày)
mc ilm rule add --expire-days 1 local/ERoom-tts
mc ilm rule add --expire-days 30 local/ERoom-evidence
```

### 2.5 Celery Tasks (định kỳ)

| Task | Schedule | Mục đích |
|------|----------|----------|
| `run_matching_engine` | Mỗi 5s | Ghép cặp người dùng theo tag |
| `cleanup_expired_rooms` | Mỗi 5 phút | Dọn phòng hết hạn |
| `cleanup_expired_tokens` | Mỗi giờ | Xóa refresh token hết hạn |
| `update_leaderboard` | CN 23:59 | Tính bảng xếp hạng tuần |

---

## 3. Biến Môi trường

### 3.1 File cấu hình

| File | Mục đích |
|------|----------|
| `.env.example` | Template cho dev local |
| `.env` | Dev local (git-ignored) |
| `.env.docker` | Dùng trong Docker Compose |

### 3.2 Biến quan trọng (từ `.env` thực tế)

```bash
# ---- Database (Local MySQL) ----
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/eroom

# ---- Nomic Embeddings ----
NOMIC_API_KEY=nk-...

# ---- Redis ----
REDIS_URL=redis://localhost:6379/0

# ---- LiveKit ----
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret

# ---- TURN ----
TURN_SERVER_URL=turn:localhost:3478

# ---- MinIO ----
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=e-room-rag-docs
MINIO_SECURE=false
```

> [!tip] Khác biệt giữa `.env` và `.env.docker`
> - Local: host = `localhost`
> - Docker: host = tên service (`redis`, `livekit`, `coturn`, `minio`)
> - Docker: MySQL host = tên service `mysql`, port 3306

---

## 4. Quy trình Deploy

### 4.1 Development (Local)

```bash
# 1. Clone + vào thư mục
cd E-Room

# 2. Copy env
cp backend/.env.example backend/.env
# Sửa DATABASE_URL, API keys...

# 3. Khởi động tất cả services
docker compose up -d

# 4. Kiểm tra
docker compose ps                    # Tất cả Up?
curl http://localhost:8000/health    # API OK?
curl http://localhost:7880           # LiveKit OK? → "OK"
docker logs e-room-livekit-1         # Log LiveKit
docker logs e-room-coturn-1          # Log coTURN

# 5. Frontend
cd frontend && npm install && npm start
# → http://localhost:3000
```

### 4.2 Production Checklist

- [ ] Đổi TẤT CẢ secrets (JWT_SECRET_KEY, LIVEKIT_API_KEY/SECRET, TURN static-auth-secret, MINIO_ACCESS/SECRET_KEY)
- [ ] `livekit.yaml`: `node_ip` → public IP, `keys` → secrets mạnh
- [ ] `turnserver.conf`: `static-auth-secret` → secret mạnh, `realm` → domain thật
- [ ] Mở firewall ports: 80, 443, 3478 (TCP+UDP), 50000-50100 (UDP), 7880-7881
- [ ] SSL: chạy certbot với `nginx-ssl.conf`
- [ ] MySQL: setup user/password, enable remote access nếu cần
- [ ] Redis: set password (`requirepass`)
- [ ] Minio: đổi credentials mặc định
- [ ] Backup: mysqldump schedule cho database
- [ ] Monitoring: Celery Flower (port 5555, chỉ internal)

### 4.3 SSL với Certbot

```bash
# 1. Dùng nginx-ssl.conf thay nginx.conf
cp nginx-ssl.conf nginx.conf

# 2. Chạy certbot
docker compose run --rm certbot certonly --webroot \
  -w /var/www/certbot \
  -d eroom.app -d www.eroom.app \
  --email admin@eroom.app --agree-tos

# 3. Reload nginx
docker compose exec nginx nginx -s reload

# 4. Auto-renew (cron)
# 0 3 * * * docker compose -f /path/to/docker-compose.yml run --rm certbot renew && docker compose exec nginx nginx -s reload
```

---

## 5. Khắc phục sự cố

### 5.1 LiveKit không start

```bash
docker logs e-room-livekit-1 --tail 50
# Lỗi thường gặp:
# - port_range_start/end không mở trên firewall
# - node_ip sai
# - Redis không reachable
```

### 5.2 coTURN không nhận kết nối

```bash
# Kiểm tra port
docker exec e-room-coturn-1 netstat -tulpn | grep 3478

# Test STUN binding
# Từ client: dùng trickle-ice hoặc WebRTC samples test
```

### 5.3 WebRTC không kết nối được (ICE failed)

1. Kiểm tra `node_ip` trong livekit.yaml = public IP
2. Kiểm tra firewall mở UDP 50000-50100
3. Kiểm tra coTURN đang chạy + port 3478 mở
4. Xem LiveKit logs: tìm `ice connection state`

### 5.4 Celery worker không nhận task

```bash
docker logs e-room-celery_worker-1 --tail 20
# Kiểm tra Redis connection
docker exec e_room_redis redis-cli ping  # Phải trả về PONG
```

---

## 6. Volumes & Dữ liệu

| Volume | Dữ liệu | Backup? |
|--------|---------|---------|
| `redis_data` | Queue, cache, session | ❌ Tạm thời |
| `minio_data` | RAG docs, TTS audio, avatars, evidence | ✅ RAG docs cần backup |
| `mysql_data` | Local MySQL database | ✅ mysqldump định kỳ |

---

## Liên quan

- [[ERoom/overview|Tổng quan]] — Kiến trúc & ports
- [[ERoom/project-structure|Cấu trúc dự án]] — Map file thực tế
- [[ERoom/dev-notes|Dev Notes]] — Trạng thái hiện tại & utils
- [[ERoom/notes|Ghi chú kỹ thuật]] — API contracts, Redis keys
- [[ERoom/decisions|Quyết định kiến trúc]] — ADR-003 (MySQL), ADR-021 (Local DB)
