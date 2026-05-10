# ERoom — Deployment Guide

## Quick Start (Docker Compose)

```bash
git clone <repo-url> e-room
cd e-room

# 1. Configure environment
cp backend/.env.docker.sample backend/.env.docker
# Edit backend/.env.docker with your TiDB Cloud (or PostgreSQL) credentials

# 2. Start all services
docker compose up -d

# 3. Verify health
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/infra/health

# 4. Open the app
open http://localhost:3000   # frontend + nginx
open http://localhost:8000/docs  # Swagger API docs
```

## Architecture

```
                                ┌──────────┐
                                │  nginx   │ :80
                                └────┬─────┘
                    ┌────────────────┼────────────────┐
                    ▼                                 ▼
            ┌───────────┐                     ┌──────────────┐
            │  api :8000 │                     │ frontend :3000│
            └─────┬─────┘                     └──────────────┘
       ┌──────────┼──────────┐
       ▼          ▼          ▼
┌─────────┐ ┌─────────┐ ┌─────────┐
│ celery  │ │ celery  │ │ LiveKit │ :7880
│ worker  │ │ beat    │ │ coTURN  │ :3478
└────┬────┘ └────┬────┘ └─────────┘
     │           │
     ▼           ▼
┌─────────┐ ┌─────────┐
│  Redis  │ │  MinIO  │
│  :6379  │ │  :9000  │
└─────────┘ └─────────┘
```

## Services (9 containers)

| Container | Port(s) | Purpose |
|-----------|---------|---------|
| e-room-api-1 | 8000, 9000 | FastAPI backend (REST + WebSocket) |
| e-room-celery_worker-1 | — | Background tasks (AI, TTS, RAG) |
| e-room-celery_beat-1 | — | Scheduled tasks (matchmaking tick) |
| e_room_redis | 6379 | Cache, message broker, rate limiter |
| e-room-minio-1 | 9000, 9001 | Object storage (avatars, RAG docs, TTS audio) |
| e-room-livekit-1 | 7880, 7881, 50000-50100/UDP | WebRTC media server |
| e-room-coturn-1 | 3478 (TCP+UDP) | TURN/STUN for NAT traversal |
| e_room_frontend | 3000 | React SPA (served via nginx in production) |
| e-room-nginx-1 | 80 | Reverse proxy (API + WebSocket + static) |

## Environment Variables

### Required (`backend/.env.docker`)

```bash
# Database (TiDB Cloud — MySQL compatible)
DATABASE_URL=mysql+pymysql://user:pass@host:4000/ERoom?ssl_ca=/etc/ssl/certs/ca-certificates.crt
DATABASE_URL_SYNC=mysql+pymysql://user:pass@host:4000/ERoom?ssl_ca=/etc/ssl/certs/ca-certificates.crt

# Redis
REDIS_URL=redis://redis:6379/0

# MinIO
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=e-room-rag-docs

# LiveKit
LIVEKIT_URL=http://livekit:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret

# JWT
JWT_SECRET=change-me-to-a-random-64-char-string
JWT_ALGORITHM=HS256
```

### PostgreSQL + pgvector (alternative)

```bash
# Uncomment & use instead of TiDB Cloud:
# DATABASE_URL=postgresql+psycopg2://eroom:eroom@postgres:5432/eroom
# DATABASE_URL_SYNC=postgresql+psycopg2://eroom:eroom@postgres:5432/eroom

# Start PostgreSQL service:
docker compose up -d postgres  # uncomment in docker-compose.yml first

# Run migrations:
cd backend && uv run alembic upgrade head

# Migrate data from SQLite:
cd backend && uv run python scripts/migrate_to_postgres.py
```

## Production Checklist

- [ ] Change all default passwords (MinIO, LiveKit, JWT_SECRET)
- [ ] Set CORS origins to your domain(s) instead of `["*"]`
- [ ] Enable HTTPS via Let's Encrypt in nginx.conf
- [ ] Configure firewall (only expose 80/443, 3478 UDP, 50000-50100 UDP)
- [ ] Set `APP_ENV=production`
- [ ] Set up monitoring (health endpoint: `GET /api/v1/infra/health`)
- [ ] Set up database backups
- [ ] Configure CI/CD (`.github/workflows/ci.yml`)

## Troubleshooting

### Service won't start
```bash
docker compose logs api          # backend logs
docker compose logs celery_worker # Celery worker logs
docker compose ps                # check which containers are down
```

### Database connection failed
```bash
# Verify TiDB Cloud is accessible
docker compose exec api uv run python -c "from app.database import engine; engine.connect()"
```

### LiveKit / WebRTC issues
- Ensure UDP ports 50000-50100 and 3478 are open on the firewall
- Check TURN server: `docker compose logs coturn`
- Verify LiveKit config: `docker compose logs livekit`

### Rate limited on login
- Wait 15 minutes or restart Redis to reset the rate limit:
  ```bash
  docker compose restart redis
  ```
