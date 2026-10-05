# E-Room `2.0.0`

**E-Room** là nền tảng phòng trò chuyện theo chủ đề (tối đa 6 người/phòng) với video call real-time, transcript live từng người nói, trợ lý AI `@ai` streaming cả thinking lẫn câu trả lời, RAG tài liệu trong phòng, tóm tắt + phân tích session, và **chấm điểm phát âm bằng AI**. Một use case chính là nhóm luyện nói tiếng Anh (điểm tổng + 4 tiêu chí, điểm từng chữ ẩn mặc định). AI chạy hybrid: LLM/STT/TTS trỏ server AI qua biến môi trường, tự fallback local khi server chết; dữ liệu ở on-premise.

## Tính năng chính

1. **Room nói chuyện theo chủ đề, tối đa 6 người** — LiveKit WebRTC (mic/cam/share màn hình, hand-raise, emoji reactions), mỗi phòng gắn topics, trần 6 seats (mặc định 4), vòng đời `idle` → `active` → `ended` (hết người về idle, bỏ hoang 24h mới ended).
2. **`@ai` trò chuyện và hỏi đáp** — mention `@ai` trong chat (chỉ chat mới gọi được AI, nói vào mic thì không); đáp án stream từng từ qua LiveKit data channel, kèm thinking của model và quote lại câu hỏi gốc.
3. **RAG tài liệu trong room** — agent tự tra tài liệu upload (Qdrant vector store + reranker) và Tavily web search khi cần, stream thinking ("Searching documents…") trước đáp án.
4. **AI Summary / Recap / Analyze / Q&A session** — `POST /sessions/{session_id}/feedback` phân tích cả buổi (gọn, chỉ nêu phần sai kèm quote + cách sửa; `409` nếu chưa chấm câu nào), `POST /sessions/{session_id}/chat` (+ `/chat/stream` SSE) hỏi đáp trên transcript, `GET .../speech-logs/summary` gộp transcript toàn room sort theo giờ.
5. **AI heartbeat** — phòng đang live mà im lặng quá lâu sẽ được AI gợi chuyện bằng 1 câu hỏi (beat 15s, cần ≥2 người + bật `enable_heartbeat`).
6. **AI transcript** — worker nghe audio từng người, VAD cắt câu, STT chuyển thành chữ, hiển thị kèm confidence badge; mỗi câu sửa được (PATCH) rồi chấm lại.
7. **AI đánh giá phát âm và ngữ pháp** — điểm tổng + 4 tiêu chí (Sounds / Stress / Fluency / Completeness) trên bản user đã sửa, kèm hướng dẫn sửa từng từ yếu (khẩu hình + phiên âm Việt). **Điểm từng chữ ẩn mặc định**, chỉ hiện khi bấm **Thống kê điểm số**; nút **Nhận xét AI** xin góp ý (gồm cả ngữ pháp/từ vựng). Xem `docs/reading-score.md`.
8. **Agent live** — dự kiến thêm sau.
9. **Schedule Room và Private Room** — đặt lịch (`scheduled_at`, task dọn phòng hẹn quá 24h) và phòng riêng (`is_private`: ẩn khỏi list public, check quyền khi vào).
- **Auth** — đăng ký/đăng nhập + Google OAuth, session cookie 7 ngày.
- **Trang public** — Home/Pricing/Blog/Contact, Rooms (live trước → open sau → ended cuối, window 10 + infinite scroll), Profile, Onboarding, Assessment (`/assessment/:sessionId`, không cần backend riêng).

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite 6, react-router-dom 7, TanStack Query 5, LiveKit components-react 2 + livekit-client 2, i18next, Zustand |
| Backend | Python 3.13, FastAPI, SQLModel, Uvicorn, Alembic migrations — kiến trúc lớp `routers → services → repositories → models` (`services/*Service` giữ business, `repositories/*Crud` giữ CRUD, `shared/` giữ constants/keys/exceptions, `tasks/` giữ Celery jobs, lỗi domain trả `{code, detail}` tiếng Việt) |
| AI | LangChain 1.x + LangGraph (agent), LLM qua `LLM_BASE_URL` (OpenAI-compatible), faster-whisper STT (server GPU hoặc local), TTS remote (Kokoro-compatible, 4 giọng), Qwen3 reranker, Tavily search |
| Chấm phát âm | Package `app/ai/pronunciation/` (phoneme GOP + 4 tiêu chí + `articulation.py` hướng dẫn khẩu hình/phiên âm Việt `how_to`/`vi`) + nhận xét AI qua LLM (JSON-only, chỉ giải thích, không tính lại điểm) |
| Realtime | LiveKit (WebRTC video/audio/data channel) — data channel chở transcript + AI stream + emoji/hand-raise |
| Jobs | Celery (queues `ai`, `ai_observer`, `ai_transcriber`) + beat (heartbeat 15s, ensure-workers 60s), Redis |
| Data | PostgreSQL 16, Qdrant (vectors), MinIO (S3 files), speech logs JSONL (`backend/log/speech/`, runtime — không commit) |
| Auth | JWT cookie (HttpOnly) + Google OAuth |
| Infra | Docker Compose (14 services), Nginx reverse proxy duy nhất (`/` static, `/api` api, `/rtc*` livekit), Tailscale Funnel public, `uv` (Python), npm (Node) |

## Luồng AI trong phòng

```
Mic/user ──▶ LiveKit room ──▶ ai-transcriber worker ──▶ VAD ──▶ STT ──▶ transcript (chat + DB)
                                                                     │ "@ai ..." ──▶ enqueue job (queue ai)
                                                                                          │
Mic/user ◀── LiveKit data ──◀ stream từng từ + thinking ◀── agent (tools → thinking → tokens)
                                                                                          │
                                                                                   └──▶ lưu DB (poll hiển thị)
```

- Worker `ai-transcriber`/`ai-observer` join phòng dưới identity `ai_*` nhưng **không chiếm seat, không hiển thị** (webhook + presence + frontend đều lọc prefix `ai_`).
- Observer giữ `mark_room_activity` theo người đang nói; transcriber/enqueue lại chừng nào còn người trong phòng.

## Luồng chấm điểm phát âm (raw → sửa → chấm → nhận xét)

```
Nói ──▶ STT raw (pronunciation=None) ──▶ user sửa corrected_text (PATCH)
  ──▶ POST .../score ──▶ điểm tổng + 4 tiêu chí (điểm từng chữ ẨN)
      ├─ audio nặng → 202 {queued} (chấm nền xong báo lại)
      └─ nhẹ → chấm sync, kèm hướng dẫn sửa từng từ yếu (how_to khẩu hình, vi phiên âm Việt)
  ──▶ [Thống kê điểm số] mở bảng riêng · [Nhận xét AI] xin góp ý AI
```

- Sửa câu sau khi đã chấm → điểm + nhận xét cũ bị reset, bắt chấm lại.
- Xin nhận xét khi chưa chấm → `409` (`NO_SCORE_REPORT`). Câu không có audio → `no_audio`; scorer crash → `scorer_failed` (điểm giữ nguyên, không ghi đè).
- Người cuối rời phòng → auto enqueue chấm nốt các câu chưa chấm.
- Lỗi API trả `{code, detail}` (mã ổn định cho client, detail tiếng Việt). Chi tiết: `docs/reading-score.md`.

## Vòng đời phòng

| Status (code) | Label UI | Nghĩa |
|---|---|---|
| `idle` | Open | Phòng trống, vào được ngay |
| `active` | Live now | Đang có người bên trong |
| `ended` | Ended | Phòng chết (ẩn bớt, vẫn mở lại được qua link) |

Người cuối out → về `idle` (+ đóng session, enqueue chấm nốt). Trống quá `ROOM_EMPTY_END_SECONDS` (mặc định 24h) → `ended`. Phòng hẹn (`scheduled_at`) quá 24h → xóa hẳn.

Presence (ai đang trong phòng) lưu ở Redis `room:{id}:participants` — ghi bởi **webhook LiveKit** + **endpoint join/leave trực tiếp** (idempotent, chống miss webhook khi tab đóng đột ngột).

## Cấu trúc dự án

```
E-Room/
├── backend/
│   ├── app/
│   │   ├── ai/                # llm/ (agent, client, tools, participant, observer),
│   │   │                      # rag/ (chunking, dense, sparse, reranker, retrieval),
│   │   │                      # stt/ (local, server, cloud, dispatch, transcriber, speech_log),
│   │   │                      # tts/, vad/, prompts/ (.md cho LLM),
│   │   │                      # pronunciation/ (audio, g2p, align, scorer, feedback,
│   │   │                      #   articulation, metrics, models, phonemes)
│   │   ├── api/routers/       # endpoint mỏng: auth, google_auth, user, room, session,
│   │   │                      # message, speech (speech-logs: me/score/feedback),
│   │   │                      # document, notification, tts (+ infra/health)
│   │   ├── services/          # BUSINESS: XxxService + singleton (orchestrate repo/ai/tasks)
│   │   ├── repositories/      # DATA ACCESS: XxxCrud + singleton (CRUD/query/transaction)
│   │   ├── shared/            # lá: constants, keys, exceptions (lỗi domain tiếng Việt)
│   │   ├── tasks/             # Celery jobs: helpers, room_jobs, maintenance, scoring
│   │   ├── integration/       # livekit token/webhook, redis, celery, minio
│   │   ├── models/            # SQLModel: User, Room, Message, ...
│   │   ├── schemas/           # Pydantic request/response + scoring/speech contracts
│   │   ├── seeds/             # seed users/rooms/messages
│   │   ├── config.py database.py security.py log.py main.py server.py
│   ├── alembic/               # migrations (chạy `alembic upgrade head`)
│   ├── tests/                 # unit / api / e2e / integration / security (pytest)
│   ├── .env.example .env.docker
│   └── pyproject.toml         # deps (uv)
├── frontend/src/
│   ├── api/                   # HTTP client (cookie auth)
│   ├── app/                   # router, guards, pages (Home/Pricing/Blog/Contact/.../Assessment)
│   ├── features/              # rooms, chat (useRoomChat), auth, onboarding,
│   │                          # profile (Schedule/Sessions/Assessment/ReadingScoreCard), ...
│   ├── components/ data/ i18n/ lib/ stores/ styles/
│   └── main.jsx
├── docs/                      # overview, features, workflow, setup, reading-score
├── scripts/                   # dev.bat / golive.bat (chạy 1 lệnh) + mac.sh / linux.sh
├── nginx.conf                 # / → frontend, /api → api (timeout 600s), /rtc* → livekit
└── docker-compose.yml         # 14 services
```

## Quick start

### 1 lệnh (khuyên dùng)

| Platform | Command |
|---|---|
| Windows (dev/local) | `scripts\dev.bat` |
| Windows (public) | `scripts\golive.bat` |
| macOS | `bash scripts/mac.sh` |
| Linux | `bash scripts/linux.sh` |

`dev.bat` ép `LIVEKIT_MODE=local` + tắt funnel (dev nội bộ); `golive.bat` ép `LIVEKIT_MODE=cloud` + stop livekit self-host + `tailscale funnel --bg 8080` (public). Chi tiết: `docs/setup.md`.

### Thủ công

```bash
# 1. Env + infra
cp backend/.env.example backend/.env   # sửa LLM_BASE_URL nếu cần
docker compose up -d db redis minio livekit qdrant

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
npm run dev                            # https://localhost:3000 (cert tu ky)
```

### Full Docker

```bash
docker compose up --build
```

## Biến môi trường chính

Xem đầy đủ ở `backend/.env.example`. Quan trọng nhất:

| Variable | Default | Mô tả |
|---|---|---|
| `LLM_BASE_URL` | `http://127.0.0.1:1234/v1` | LLM server (OpenAI-compatible; trỏ server ngoài hoặc ollama local) |
| `LLM_MODEL` | `google/gemma-4-e2b` | Model chat + nhận xét phát âm AI (không key riêng) |
| `STT_PROVIDER` | `auto` | `whisper_server` = ép dùng server GPU (chết thì fallback local) |
| `STT_SERVER_BASE_URL` | — | STT server, ví dụ `http://<IP-máy-AI>:8001/v1` |
| `TTS_BASE_URL` | `http://localhost:8002/v1` | TTS server (Kokoro-compatible) |
| `EMBEDDING_BASE_URL` | — (trống = dùng chung `LLM_BASE_URL`) | Embedding server riêng (khi có) |
| `QDRANT_HOST` / `QDRANT_PORT` | `localhost` / `6333` | Vector DB (trong docker: `qdrant`) |
| `LIVEKIT_MODE` + `LIVEKIT_LOCAL_URL` | `local` / `ws://localhost:7880` | WebRTC (trong docker: `ws://livekit:7880`; public: `LIVEKIT_MODE=cloud`) |
| `ROOM_EMPTY_END_SECONDS` | `86400` | Phòng trống bao lâu thì ended |
| `AI_TIMEOUT_SECONDS` | `900` | Trần 1 job AI |
| `TAVILY_API_KEY` | — | Web search (không có thì agent bỏ qua) |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | — | Login Google (cần OAuth Client ID, không dùng service-account) |
| `PRONUN_BASE_URL` | — | Scorer remote (không có thì chấm local → heuristic) |
| `SCORING_MAX_PARALLEL` | `1` | Số lượt chấm local chạy song song (1 = tuần tự, chống OOM máy host) |
| `SPEECH_LOG_DIR` | `backend/log/speech` | Nơi lưu transcript + audio từng câu (runtime, không commit) |

> ⚠️ `.env` / `.env.docker` / `livekit.yaml` không commit (đã có trong `.gitignore`). Clone mới thì copy từ `.env.example` / `livekit.yaml.example` rồi điền secret.

## API (tóm tắt)

Prefix `/api/v1`, chi tiết đầy đủ ở Swagger `http://localhost:8000/docs`. Lỗi trả `{code, detail}`.

| Method | Path | Auth | Mô tả |
|---|---|---|---|
| POST | `/auth/register` `/auth/login` `/auth/logout` | —/Cookie | Đăng ký (201), đăng nhập (set cookie), đăng xuất (xóa cookie) |
| GET | `/auth/google/login` `/auth/google/callback` | — | Google OAuth |
| GET | `/users/me` `/users/me/stats` | Cookie | Thông tin + thống kê cá nhân |
| GET | `/rooms/?public_only=` | — | List (ẩn `is_private` với người lạ) |
| POST | `/rooms/` | Cookie | Tạo phòng (tên, topics, seats ≤6, `is_private`, `scheduled_at`) |
| GET | `/rooms/{id}` | — | Chi tiết phòng (+ check quyền phòng riêng) |
| POST | `/rooms/match` | Cookie | Ghép phòng public phù hợp topic (ưu tiên active) |
| POST | `/rooms/{id}/token` | Cookie | LiveKit token (chặn khi full seats) |
| POST | `/rooms/{id}/join` `/rooms/{id}/leave` | Cookie | Join/leave trực tiếp (idempotent) |
| POST | `/rooms/livekit/webhook` | LiveKit | Join/leave events (bỏ qua `ai_*`) |
| GET/POST/DELETE | `/rooms/{id}/documents...` | Cookie | Upload tài liệu RAG (pdf/md/txt ≤10MB, host-only) |
| GET | `/rooms/{room_id}/speech-logs/me` | Cookie | Câu của chính mình (để sửa/chấm) |
| GET | `/rooms/{room_id}/speech-logs/summary` | Cookie | Transcript gộp sort theo giờ |
| PATCH | `/rooms/{room_id}/speech-logs/{message_id}` | Cookie | Sửa `corrected_text` (reset điểm cũ) |
| POST | `/rooms/{room_id}/speech-logs/{message_id}/score` | Cookie | Chấm phát âm (nặng → `202 {queued}`) |
| POST | `/rooms/{room_id}/speech-logs/{message_id}/feedback` | Cookie | Nhận xét AI (chỉ sau khi đã chấm, chưa chấm → `409`) |
| POST | `/sessions/{session_id}/chat` `/chat/stream` | Cookie | Hỏi đáp trên transcript (sync + SSE) |
| POST | `/sessions/{session_id}/feedback` | Cookie | AI feedbacks cả session (`409` nếu chưa chấm câu nào) |
| GET/POST | `/messages/` | Cookie | Chat (`@ai` đầu tin nhắn → trigger agent) |
| GET | `/tts/voices` | — | 4 giọng (af_heart, am_adam, bf_emma, bm_george) |
| POST | `/tts/speak` | Cookie | Tổng hợp giọng, trả MP3 |
| — | `/documents/` `/notifications/` `/users/` | Cookie | CRUD tài liệu, thông báo, users |

## Tài liệu

| File | Nội dung |
|---|---|
| `docs/overview.md` | Kiến trúc tổng thể, tech stack, vòng đời phòng, bố cục repo, quy ước code |
| `docs/features.md` | Chi tiết 9 tính năng + auth/pages/subscription |
| `docs/workflow.md` | Sơ đồ các luồng (join/leave, chat, `@ai`, transcript, heartbeat, chấm điểm, session, RAG, TTS, public hosting) |
| `docs/flows.md` | Luồng kỹ thuật chi tiết (task → worker → Redis key → DB) + ghi chú vận hành |
| `docs/setup.md` | Cài đặt: dev local, full docker, public qua Tailscale + troubleshooting |
| `docs/reading-score.md` | Logic chấm điểm phát âm + ngữ pháp, thiết kế UI, wiring session/DB |
| `.opencode/rules/` | Quy chuẩn kiến trúc backend + style Python/API (version cùng repo) |

## Test

```bash
cd backend
uv run pytest tests/unit tests/api -q        # nhanh, không cần infra ngoài redis
uv run pytest tests/ -q                      # full (cần redis + DB test local)
cd ../frontend
npm run build                                # verify build
npx vitest run                               # unit tests (gồm ReadingScoreCard: ẩn điểm từng chữ mặc định)
```

Lưu ý: test dùng sqlite file `backend/test_eroom.db` (đã gitignore). Nếu gặp lỗi constraint lạ khi chạy lẻ, xóa file này rồi chạy lại — nó tự tạo mới.

## License

Chưa có file `LICENSE` trong repo.
