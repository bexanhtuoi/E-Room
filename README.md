# E-Room

**E-Room** là nền tảng luyện nói tiếng Anh real-time với AI, hỗ trợ video call, đánh giá phát âm, và trợ lý AI thông minh. Người học có thể tham gia phòng thảo luận theo chủ đề, nhận phản hồi phát âm chi tiết theo từng từ, và cải thiện kỹ năng nói qua các buổi học có cấu trúc — tất cả đều chạy on-premise.

## Techstack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | React 19, Bootstrap 5, react-router-dom 7, TanStack Query 5, Zustand 5 | UI, routing, state management, server state |
| **Backend** | Python 3.13, FastAPI, Uvicorn | REST API, WebSocket, async workers |
| **AI/ML** | LangChain, FunASR, Wav2Vec2, CMU Dictionary, Gemma 4 E2B, Qwen3 Embedding | ASR, phoneme alignment, pronunciation scoring, RAG embeddings |
| **Orchestration** | Celery, Redis PubSub | Background tasks, event bus, scheduling |
| **Database** | TiDB (local Docker, MySQL-compatible) | Relational storage, vector embeddings |
| **Real-time** | LiveKit (WebRTC), WebSocket | Video rooms, audio streaming, chat |
| **Auth** | JWT (PyJWT), Argon2, OAuth2 | Authentication & authorization |
| **File Storage** | MinIO (S3-compatible) | File uploads, TTS audio storage |
| **Payment** | Stripe | Subscription (free / pro / pro_plus) |
| **Container** | Docker Compose | 9-service orchestration |
| **I18n** | i18next (en + vi) | Full bilingual UI |
| **Package Mgmt** | uv (Python), npm (Node.js) | Dependency management |

## Project Structure

```
E-Room/
├── backend/
│   ├── app/
│   │   ├── api/routers/         # 14 FastAPI routers (auth, user, room, message, session, notes, series, subscription, tag, leaderboard, notification, infra, health, websocket)
│   │   ├── agent/               # LLM agents (corrector, expert, heartbeat, query router) + LangChain tool
│   │   ├── model/               # SQLModel ORM entities (User, Room, Message, Session, Subscription, v.v.)
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── service/             # Business logic (CRUD, auth, room state, heartbeat, token store)
│   │   ├── rag/                 # RAG pipeline (Nomic embeddings, TiDB vector store, chunking, retrieval)
│   │   ├── infrastructure/      # Celery workers, Redis, MinIO, LiveKit, audio pipeline (Whisper, Wav2Vec2)
│   │   ├── ws/                  # WebSocket handlers (chat, audio streaming, VAD)
│   │   ├── utils/               # Helpers (datetime, retry, validation, text normalization)
│   │ ├── seed/                # Seeder (10 default rooms, 55 tags)
│   │   ├── config.py            # Pydantic-settings configuration
│   │   ├── database.py          # SQLModel engine & session
│   │   ├── security.py          # JWT & Argon2 password utilities
│   │   ├── log.py               # Logging configuration
│   │   └── main.py              # FastAPI app entry point
│   ├── alembic/                 # Database migrations
│   ├── tests/                   # Test suite
│   └── pyproject.toml           # Python dependencies (uv)
│
├── frontend/
│   └── src/
│       ├── api/                 # HTTP client with JWT auto-refresh
│       ├── app/                 # Root layout, routing, auth/onboarding guards
│       ├── components/          # UI primitives (Avatar, Badge, Card, Toast, Skeleton, Tag system)
│       ├── context/             # ThemeContext (dark/light)
│       ├── features/            # Feature modules (auth, chat, rooms, realtime, onboarding, sessions, notes, series, leaderboard, subscription, AI)
│       ├── hooks/               # useAsyncResource
│       ├── i18n/                # i18next config (en + vi, 600+ lines, 12 namespaces)
│       ├── lib/                 # WebSocket, audio capture, constants, formatters, query client
│       ├── stores/              # Zustand stores (agent, auth, room, subscription, tags)
│       └── styles/              # CSS with dark/light theme via CSS variables (15 files)
│
├── scripts/
│   ├── win.bat                  # One-click startup (Windows)
│   ├── mac.sh                   # One-click startup (macOS)
│   └── linux.sh                 # One-click startup (Linux)
│
├── docker-compose.yml           # 8 services: api, tidb, redis, minio, livekit, coturn, frontend, nginx
├── nginx.conf                   # Non-SSL reverse proxy
├── nginx-ssl.conf               # SSL reverse proxy with Let's Encrypt
├── livekit.yaml                 # LiveKit WebRTC server config
├── turnserver.conf              # coTURN STUN/TURN config
└── dev.bat                      # Local development launcher (Windows)
```

## Key Features

- **Real-time Video/Audio Rooms** — LiveKit WebRTC rooms với chat, VAD (Voice Activity Detection), và audio streaming qua WebSocket.
- **Pronunciation Assessment** — Pipeline 4 bước: Faster-Whisper ASR → Wav2Vec2 forced alignment → CMU Pronouncing Dictionary → Scorer (accuracy, GOP, fluency, prosody, composite).
- **AI Pronunciation Correction** — LLM-based correction với phản hồi chi tiết (IPA, tongue/lip position, TTS text). Kích hoạt tự động khi điểm phát âm < 7/10.
- **AI Expert** — Trả lời câu hỏi chuyên sâu kết hợp RAG (Nomic embeddings + TiDB vector store) + Brave web search + LLM answer.
- **Heartbeat System** — AI sinh câu hỏi gợi chuyện định kỳ (45s) để duy trì hội thoại trong phòng.
- **Matchmaking** — Thuật toán ghép cặp staged (initial → cross-tag → level-expand → AI room fallback) với Jaccard similarity + tier/level proximity.
- **Session Notes** — Tự động tạo session note Markdown (summary, vocabulary, corrections, strengths, areas to improve) — Pro+ feature.
- **Leaderboard** — Bảng xếp hạng tuần theo tag, tính điểm dựa trên thời gian nói + điểm trung bình.
- **Subscription** — Stripe integration: free / pro / pro_plus tiers với quota management.
- **Moderation** — NSFW/Spam pattern scanning (Celery beat, 10s interval).
- **Dark/Light Theme** — Full theming via CSS variables (data-theme attribute).
- **I18n** — Tiếng Anh và Tiếng Việt qua i18next.
- **Role-Based Access** — User + ban system với strike tracking (3 strikes → 24h ban, 5 strikes → permanent).
- **CORS + Rate Limiting** — Configurable CORS và Redis-based rate limiter (login, TTS).

## Agent Workflow

E-Room sử dụng **3 tác nhân AI độc lập** phối hợp qua Redis PubSub và Celery workers:

### 1. Pronunciation Pipeline

```
  ┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
  │  WebSocket   │────▶│  AudioBuffer     │────▶│  VAD Detection  │
  │  (PCM audio) │     │  (VAD buffering) │     │  (speech_end)   │
  └─────────────┘     └──────────────────┘     └────────┬────────┘
                                                         │
                                                         ▼
  ┌──────────────────────────────────────────────────────────────┐
  │               PronunciationPipeline.assess()                  │
  │  1. Faster-Whisper → ASR (text + segments)                   │
  │  2. Wav2Vec2 Aligner → forced phoneme alignment              │
  │  3. CMU Dictionary → lookup canonical phonemes per word      │
  │  4. PronunciationScorer → accuracy(40%) + GOP(20%)           │
  │     + fluency(25%) + prosody(15%) → composite score 0-10     │
  └─────────────────────────┬────────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              │                           │
              ▼                           ▼
       overall ≥ 7/10               overall < 7/10
              │                           │
              ▼                           ▼
     ┌─────────────────┐       ┌─────────────────────────┐
     │  Publish to     │       │  LLM Corrector Agent    │
     │  Redis Channel  │       │  (semaphore=1, async)   │
     │  "room:         │       │  → corrected text       │
     │   transcript"   │       │  → errors list          │
     └─────────────────┘       │  → pronunciation_feedback│
                               │  → tts_text              │
                               └────────────┬────────────┘
                                            │
                                            ▼
                               ┌─────────────────────────┐
                               │  Publish to Redis        │
                               │  Channel "room:          │
                               │   correction"            │
                               └────────────┬────────────┘
                                            │
                                            ▼
                               ┌─────────────────────────┐
                               │  CeleryBridge → WebSocket│
                               │  → Frontend (correction  │
                               │    card + TTSPlayer)     │
                               └─────────────────────────┘
```

### 2. AI Expert (RAG + Web Search)

```
  ┌─────────────┐     ┌────────────────────────────────────────────┐
  │  WebSocket   │────▶│  answer_expert(question, room_id, tags)   │
  │  "chat" msg  │     └────────────┬───────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
     ┌────────────────────────┐       ┌────────────────────────┐
     │  RAG Retrieval         │       │  Brave Web Search      │
     │  NomicEmbeddings →     │       │  (nếu có API key)      │
     │  TiDB Vector Store     │       │  → top 3 web results   │
     │  → top 5 passages      │       └────────────┬───────────┘
     └────────────┬───────────┘                    │
                  │                               │
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                    ┌────────────────────────────┐
                    │  LLM Answer Generation     │
                    │  (ChatOpenAI, temp=0.5)    │
                    │  → answer text + sources   │
                    └────────────┬───────────────┘
                                 │
                                 ▼
                    ┌────────────────────────────┐
                    │  WebSocket → Frontend      │
                    │  (ExpertResponse component) │
                    └────────────────────────────┘
```

### 3. Heartbeat System (Conversation Starter)

```
  ┌─────────────┐     ┌──────────────────────────────────────────────┐
  │  Celery Beat │────▶│  room_heartbeat_tick (every 45s)            │
  │  scheduler   │     │  → query active rooms with participants     │
  └─────────────┘     └────────────┬─────────────────────────────────┘
                                    │
                                    ▼
                    ┌──────────────────────────────────────────────┐
                    │  generate_heartbeat_question(room_id, topic) │
                    │  → LLM (temp=0.7) với prompt đa dạng:       │
                    │    Heartbeat 1: Icebreaker, light, fun       │
                    │    Heartbeat 2: Thought-provoking, reflection │
                    │    Heartbeat 3+: Challenging, speculative     │
                    │  → {question, context, suggested_response}    │
                    └────────────┬─────────────────────────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────────────────────────┐
                    │  Redis PubSub → CeleryBridge → WebSocket     │
                    │  → Frontend (HeartbeatMessage component)     │
                    └──────────────────────────────────────────────┘
```

### 4. Background Pipeline (Celery Tasks)

| Task | Schedule | Description |
|---|---|---|
| `matchmaking-heartbeat` | 5s | Jaccard matchmaking (initial → cross-tag → level → AI room) |
| `room-moderation-scan` | 10s | NSFW/Spam regex scanning in active rooms |
| `room-heartbeat-tick` | 45s | Generate conversation starters in active rooms |
| `cleanup-expired-rooms` | 5min | Archive empty rooms older than 1h |
| `cleanup-expired-tokens` | 1h | Delete expired JWT refresh tokens |
| `weekly-leaderboard` | 1h | Compute leaderboard scores |

All AI results are published to Redis PubSub channels (`room:transcript`, `room:correction`, `room:heartbeat`) and relayed to WebSocket clients via `CeleryBridge`.

## Problems & Solutions

- **Pronunciation feedback complexity** — Giving word-level phonetic feedback requires ASR + phoneme alignment + dictionary lookup + scoring + LLM correction. → Built a 4-stage pipeline: Whisper → Wav2Vec2 → CMU → Scorer, with LLM post-correction only when score < 7/10, saving 90% of LLM calls.

- **Real-time audio processing** — Streaming PCM audio over WebSocket requires VAD buffering, non-blocking pipeline, and concurrent user support. → `AudioBuffer` with sequence-based reassembly + per-user asyncio tasks + Celery offload for heavy inference.

- **Multi-agent coordination** — Corrector, expert, heartbeat, moderation, and matchmaking must run concurrently without conflicts. → Redis PubSub as event bus + `CeleryBridge` as WebSocket relay; each agent subscribes to its own channel and publishes results asynchronously.

- **Non-deterministic AI outputs** — LLM responses vary, making testing unreliable. → Structured output parsing (JSON mode) + fallback responses + retry decorators with exponential backoff.

- **Cost & privacy** — Cloud AI services are expensive and raise data privacy concerns for voice data. → Local LLM inference via llama.cpp (Gemma 4 E2B port 8012 + Qwen3 Embedding port 8013) + on-premise FunASR + local MySQL (Docker) + local embeddings.

- **Frontend complexity** — Video rooms, streaming chat, pronunciation cards, dark/light theme, and i18n must coexist. → Feature-based folder structure + Zustand stores + CSS variables + lazy-loaded routes with auth guards.

## Quick Starts

### Prerequisites

- Python 3.13+ with `uv` package manager
- Node.js 22+
- Docker Desktop (Windows / macOS) or Docker Engine (Linux)
- Local LLM server (llama.cpp) with two models:
  - Gemma 4 E2B Q8_0 (text gen) — port **8012**, api_key `dev`
  - Qwen3 Embedding 0.6B Q8_0 (embedding) — port **8013**, api_key `dev`

### One-Click Scripts

Start everything (infra containers + backend API + Celery workers + Frontend) with a single command:

| Platform | Command |
|---|---|
| Windows | `scripts\win.bat` |
| macOS | `bash scripts/mac.sh` |
| Linux | `bash scripts/linux.sh` |

These scripts:
1. Copy `.env.example` → `.env` nếu chưa tồn tại
2. Spin up Docker containers (tidb, redis, minio, livekit, coturn)
3. Install backend dependencies with `uv sync`
4. Install frontend dependencies with `npm install`
5. Start API server (port 8000), Celery worker, Celery beat, and Frontend (port 3000)
6. Open `http://localhost:3000` in browser

### Manual Setup

```bash
# 1. Clone và copy env
cd E-Room
cp backend/.env.example backend/.env

# 2. Sửa backend/.env — cấu hình LLM_BASE_URL trỏ đến llama.cpp
#    LLM_BASE_URL=http://localhost:8012/v1 (Gemma 4 E2B)
#    EMBEDDING_BASE_URL=http://localhost:8013/v1 (Qwen3 Embedding)

# 3. Start infra services
docker compose up -d tidb redis minio livekit coturn

# 4. Start backend (API)
cd backend
uv sync
uv run python -m app.server

# 5. Start frontend (terminal mới)
cd frontend
npm install
npm run dev
```

### Docker Compose (full stack)

```bash
docker compose up --build
```

This builds and starts all 10 services. No local Python or Node.js needed.

### Environment Variables

Xem `backend/.env.example` cho danh sách đầy đủ. Các biến quan trọng:

| Variable | Default | Description |
|---|---|---|
| `LLM_BASE_URL` | `http://localhost:8012/v1` | llama.cpp text gen endpoint (Gemma 4 E2B) |
| `LLM_MODEL` | `gemma-4-E2B-it` | Model name |
| `LLM_API_KEY` | `dev` | API key for llama.cpp |
| `EMBEDDING_BASE_URL` | `http://localhost:8013/v1` | llama.cpp embedding endpoint (Qwen3) |
| `EMBEDDING_MODEL` | `Qwen3-Embedding-0.6B` | Embedding model name |
| `LIVEKIT_URL` | `ws://localhost:7880` | WebRTC server URL |
| `STRIPE_SECRET_KEY` | — | Stripe payment processing |

> **⚠️ Security:** `.env` và `.env.docker` chứa credentials thật (database, API keys). Đã được thêm vào `.gitignore` — không commit các file này.

## API Docs

Tất cả API endpoints được mount dưới prefix `/api/v1`.

### Auth

| Method | Path | Description |
|---|---|---|
| POST | `/auth/register` | Register new user |
| POST | `/auth/login` | Login (returns JWT access + refresh tokens) |
| POST | `/auth/refresh` | Refresh access token |
| POST | `/auth/logout` | Logout (revoke access + refresh tokens) |
| PATCH | `/auth/me` | Update current user profile |

### Rooms

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/rooms/` | — | List active rooms (room_id, topic, tags, etc.) |
| POST | `/rooms/` | JWT | Create room |
| GET | `/rooms/{id}` | — | Room detail |
| POST | `/rooms/{id}/join` | JWT | Join room |
| POST | `/rooms/{id}/leave` | JWT | Leave room |
| POST | `/rooms/{id}/token` | JWT | Get LiveKit token |
| POST | `/rooms/match` | JWT | Matchmaking (tìm phòng phù hợp) |

### Sessions

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/sessions/` | JWT | List user sessions (paginated) |
| GET | `/sessions/rooms/{room_id}` | JWT | Sessions by room |

### Messages

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/messages/` | JWT | List messages (paginated) |
| GET | `/messages/rooms/{room_id}` | JWT | Messages by room |
| POST | `/messages/` | JWT | Send message |
| POST | `/messages/transcripts` | JWT | Save transcript |

### Notes

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/notes/` | JWT | List session notes |
| GET | `/notes/{id}` | JWT | Note detail |
| DELETE | `/notes/{id}` | JWT | Delete note |

### Series

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/series/` | — | List room series |
| POST | `/series/` | JWT | Create series |
| GET | `/series/{id}` | — | Series detail |
| POST | `/series/{id}/register` | JWT | Register for topic rooms |

### Leaderboard

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/leaderboard/` | — | Weekly leaderboard (filter by tag, period) |

### Tags

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/tags/popular` | — | Popular tags |
| GET | `/tags/search` | — | Search tags |
| POST | `/tags/custom` | JWT | Create custom tag |
| POST | `/tags/bulk-add` | JWT | Bulk add tags to user |

### Notifications

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/notifications/` | JWT | User notifications |
| PATCH | `/notifications/{id}/read` | JWT | Mark as read |

### Subscriptions

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/subscriptions/me` | JWT | Current subscription |
| POST | `/subscriptions/create-checkout` | JWT | Stripe checkout session |
| POST | `/subscriptions/cancel` | JWT | Cancel subscription |
| POST | `/subscriptions/webhook` | — | Stripe webhook |
| GET | `/subscriptions/invoices` | JWT | Invoice history |

### Infra

| Method | Path | Description |
|---|---|---|
| GET | `/infra/status` | System status |
| GET | `/infra/health` | Health check |
| GET | `/infra/health/live` | Liveness probe |

### WebSocket

| Path | Description |
|---|---|
| `/ws/rooms/{room_id}` | Chat WebSocket (expert replies, heartbeat, presence) |
| `/ws/audio/{room_id}` | Audio WebSocket (PCM streaming, VAD, speech processing) |

Swagger UI available at `http://localhost:8000/docs` when backend is running.

## License

MIT License — see [LICENSE](./LICENSE) for details.
