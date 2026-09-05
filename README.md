# E-Room `2.0.0`

**E-Room** là nền tảng luyện nói tiếng Anh theo nhóm nhỏ (tối đa 4 người/phòng) với video call real-time, transcript live từng người nói và trợ lý AI `@ai` streaming cả thinking lẫn câu trả lời. Toàn bộ AI chạy local (llama.cpp), dữ liệu ở on-premise.

## Tính năng chính

- **Video rooms real-time** — LiveKit WebRTC, tối đa 4 seats, mic/cam/share màn hình, hand-raise, emoji reactions.
- **Live transcript từng user** — worker nghe audio mỗi người, VAD cắt câu, faster-whisper (hoặc cloud STT) chuyển thành chữ, hiển thị kèm confidence badge.
- **Trợ lý AI `@ai`** — mention `@ai` trong chat (hoặc nói "@ai ..." vào mic) để hỏi; đáp án stream từng từ qua LiveKit data channel, kèm thinking của model (reasoning) và quote lại câu hỏi gốc.
- **RAG tài liệu + web search** — agent tự tra tài liệu upload (Qdrant vector store + reranker) và Tavily web search khi cần, stream thinking ("Searching documents…") trước đáp án.
- **Heartbeat** — phòng đang live mà im lặng quá lâu sẽ được AI gợi chuyện bằng 1 câu hỏi.
- **Vòng đời phòng 3 trạng thái** — `open` (trống) → `live` (có người) → `ended` (chết). Hết người thì về open, bỏ hoang 24h mới ended.
- **Auth** — đăng ký/đăng nhập + Google OAuth, session cookie 7 ngày.
- **Trang public** — Home/Pricing/Blog/Contact, Rooms (live trước → open sau → ended cuối, window 10 + infinite scroll), Profile, Onboarding.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite 6, react-router-dom 7, TanStack Query 5, LiveKit components-react 2 + livekit-client 2, i18next, Zustand |
| Backend | Python 3.13, FastAPI, SQLModel, Uvicorn, Alembic migrations |
| AI | LangChain 1.x + LangGraph (agent), llama.cpp server (Gemma text gen + Qwen3 embedding), faster-whisper STT, Qwen3 reranker, Tavily search |
| Realtime | LiveKit (WebRTC video/audio/data channel) |
| Jobs | Celery (ai, ai_observer, ai_transcriber queues) + beat, Redis |
| Data | TiDB (MySQL-compatible), Qdrant (vectors), MinIO (S3 files) |
| Auth | JWT cookie (HttpOnly) + Google OAuth |
| Infra | Docker Compose (12 services), `uv` (Python), npm (Node) |

## Luồng AI trong phòng

```
Mic/user ──▶ LiveKit room ──▶ ai-transcriber worker ──▶ VAD ──▶ STT ──▶ transcript (chat + DB)
                                                                     │ "@ai ..." ──▶ enqueue job
                                                                                          │
Mic/user ◀── LiveKit data ──◀ stream từng từ + thinking ◀── agent (tools → thinking → tokens)
                                                                                          │
                                                                                   └──▶ lưu DB (poll hiển thị)
```

- Worker `ai-transcriber`/`ai-observer` join phòng như participant `ai_*` nhưng **không chiếm seat, không hiển thị** (webhook bỏ qua `ai_*`, frontend lọc).
- Chat gõ `@ai` hoặc nói "@ai ..." đều trigger cùng 1 pipeline.

## Vòng đời phòng

| Status | Label UI | Nghĩa |
|---|---|---|
| `idle` | Open | Phòng trống, vào được ngay |
| `active` | Live now | Đang có người bên trong |
| `ended` | Ended | Phòng chết (ẩn bớt, vẫn mở lại được qua link) |

Người cuối out → về `open`. Trống quá `ROOM_EMPTY_END_SECONDS` (mặc định 24h) → `ended`.

## Cấu trúc dự án

```
E-Room/
├── backend/
│   ├── app/
│   │   ├── ai/                # LLM agent (query/events/thinking), STT dispatcher,
│   │   │                      # VAD, transcriber/observer workers, RAG retrieval,
│   │   │                      # tools, prompts, celery tasks
│   │   ├── api/routers/       # auth, google_auth, user, room, message,
│   │   │                      # document, notification (+ infra/health)
│   │   ├── integration/       # livekit token/webhook, redis, celery, minio
│   │   ├── models/            # SQLModel: User, Room, Message, ...
│   │   ├── schemas/           # Pydantic request/response + validation
│   │   ├── services/          # CRUD repository (không business logic)
│   │   ├── seeds/             # seed users/rooms/messages
│   │   ├── config.py database.py security.py log.py main.py server.py
│   ├── alembic/               # migrations (chạy `alembic upgrade head`)
│   ├── tests/                 # unit / api / e2e / integration / security (pytest)
│   ├── .env.example .env.docker
│   └── pyproject.toml         # deps (uv)
├── frontend/src/
│   ├── api/                   # HTTP client (cookie auth)
│   ├── app/                   # router, guards, pages (Home/Pricing/Blog/Contact/...)
│   ├── features/              # rooms, chat (useRoomChat), auth, onboarding, ...
│   ├── components/ data/ i18n/ lib/ stores/ styles/
│   └── main.jsx
├── scripts/                   # win.bat / mac.sh / linux.sh (chạy 1 lệnh)
└── docker-compose.yml         # 12 services
```

## Services & ports

| Service | Port | Ghi chú |
|---|---|---|
| frontend (dev) | 3000 | Vite HMR |
| api | 8000 | FastAPI + Swagger `/docs` |
| livekit | 7880 | WebRTC (browser đổi host docker → localhost) |
| llama (text gen) | 8012 | Gemma, OpenAI-compatible |
| llama (embedding) | 8013 | Qwen3 Embedding |
| qdrant | 6333 | Vector DB tài liệu |
| tidb | 4000 | MySQL-compatible |
| redis | 6379 | Queue + presence + heartbeat |
| minio | 9000 | S3 files |
| ai-worker / ai-observer / ai-transcriber / ai-beat | — | Celery (code bind-mount, restart là nạp) |

## Quick start

### 1 lệnh (khuyên dùng)

| Platform | Command |
|---|---|
| Windows | `scripts\win.bat` |
| macOS | `bash scripts/mac.sh` |
| Linux | `bash scripts/linux.sh` |

### Thủ công

```bash
# 1. Env + infra
cp backend/.env.example backend/.env   # sửa LLM_BASE_URL nếu cần
docker compose up -d tidb redis minio livekit qdrant llama

# 2. Migrate DB
cd backend
uv sync
uv run alembic upgrade head

# 3. Backend API (terminal 1)
uv run python -m app.server            # :8000

# 4. Workers (mỗi worker 1 terminal)
uv run celery -A app.integration.celery.celery_app worker --queues=ai --loglevel=INFO
uv run celery -A app.integration.celery.celery_app worker --queues=ai_transcriber --loglevel=INFO
uv run celery -A app.integration.celery.celery_app worker --queues=ai_observer --loglevel=INFO
uv run celery -A app.integration.celery.celery_app beat --loglevel=INFO

# 5. Frontend (terminal mới)
cd ../frontend
npm install
npm run dev                            # http://localhost:3000
```

### Full Docker

```bash
docker compose up --build
```

## Biến môi trường chính

Xem đầy đủ ở `backend/.env.example`. Quan trọng nhất:

| Variable | Default | Mô tả |
|---|---|---|
| `LLM_BASE_URL` | `http://localhost:8012/v1` | llama.cpp text gen |
| `LLM_MODEL` | `gemma-4-E2B-it` | Model chat |
| `EMBEDDING_BASE_URL` | `http://localhost:8013/v1` | llama.cpp embedding |
| `QDRANT_HOST` / `QDRANT_PORT` | `localhost` / `6333` | Vector DB (trong docker: `qdrant`) |
| `LIVEKIT_URL` | `ws://localhost:7880` | WebRTC (trong docker: `ws://livekit:7880`) |
| `ROOM_EMPTY_END_SECONDS` | `86400` | Phòng trống bao lâu thì ended |
| `AI_TIMEOUT_SECONDS` | `300` | Trần 1 job AI |
| `TAVILY_API_KEY` | — | Web search (không có thì agent bỏ qua) |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | — | Login Google (cần OAuth Client ID, không dùng service-account) |

> ⚠️ `.env` / `.env.docker` / `livekit.yaml` không commit (đã có trong `.gitignore`). Clone mới thì copy từ `.env.example` / `livekit.yaml.example` rồi điền secret.

## API (tóm tắt)

Prefix `/api/v1`, chi tiết đầy đủ ở Swagger `http://localhost:8000/docs`.

| Method | Path | Auth | Mô tả |
|---|---|---|---|
| POST | `/auth/register` `/auth/login` `/auth/refresh` | — | Session cookie 7 ngày |
| GET | `/auth/me` | Cookie | Thông tin user |
| GET | `/rooms/?skip=&limit=` | — | List mới nhất trước |
| POST | `/rooms/` | Cookie | Tạo phòng |
| GET | `/rooms/{id}` | — | Chi tiết phòng |
| POST | `/rooms/{id}/token` | Cookie | LiveKit token |
| POST | `/rooms/{id}/leave` | Cookie | Rời phòng (xóa presence ngay) |
| POST | `/rooms/match` | Cookie | Ghép phòng phù hợp |
| POST | `/rooms/livekit/webhook` | LiveKit | Join/leave events (bỏ qua `ai_*`) |
| GET/POST | `/messages/` | Cookie | Chat (`@ai` đầu tin nhắn → trigger agent) |
| GET | `/users/{id}` `/users/me` | Cookie | Users |
| — | `/documents/` `/notifications/` | Cookie | Upload tài liệu RAG, thông báo |

## Test

```bash
cd backend
uv run pytest tests/unit tests/api -q        # nhanh, không cần infra ngoài redis
uv run pytest tests/ -q                      # full (cần redis + DB test local)
cd ../frontend
npm run build                                # verify build
npx vitest run                               # unit tests
```

Lưu ý: test dùng sqlite file `backend/test_eroom.db` (đã gitignore). Nếu gặp lỗi constraint lạ khi chạy lẻ, xóa file này rồi chạy lại — nó tự tạo mới.

## Troubleshooting

| Hiện tượng | Nguyên nhân thường gặp |
|---|---|
| `@ai` chỉ hiện "thinking" rồi ra 1 cục | Tab mất kết nối LiveKit (không stream live, chỉ poll DB). Kiểm tra mic/cam có nối không; F12 xem console có `Invalid URL` |
| Mic/cam báo lỗi thiết bị | Lỗi phía browser: chưa cấp quyền, không có thiết bị, hoặc thiết bị đang bị app khác giữ (Zoom/Zalo/tab khác) |
| List rooms hiện người đã out | Đợi ~5–10s (members refresh 5s, list 10s); nếu kẹt lâu là webhook miss — bấm Reload |
| Worker báo `Unknown column` | Worker cũ hơn migration — `docker restart ai-worker` (code bind-mount) |
| Job AI timeout 300s | LLM CPU ~3.7 tok/s; câu RAG nặng có thể quá trần — câu trả lời ngắn gọn hơn |

## License

Chưa có file `LICENSE` trong repo.
