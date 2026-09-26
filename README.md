# E-Room `2.1.0`

**E-Room** là nền tảng luyện nói tiếng Anh theo nhóm nhỏ (tối đa 4 người/phòng) với video call real-time, transcript live từng người nói, trợ lý AI `@ai` streaming cả thinking lẫn câu trả lời, và **chấm điểm phát âm bằng AI** (điểm tổng + 4 tiêu chí, điểm từng chữ ẩn mặc định). Toàn bộ AI chạy local (llama.cpp), dữ liệu ở on-premise.

## Tính năng chính

- **Video rooms real-time** — LiveKit WebRTC, tối đa 4 seats, mic/cam/share màn hình, hand-raise, emoji reactions.
- **Live transcript từng user** — worker nghe audio mỗi người, VAD cắt câu, faster-whisper (hoặc cloud STT) chuyển thành chữ, hiển thị kèm confidence badge.
- **Trợ lý AI `@ai`** — mention `@ai` trong chat (hoặc nói "@ai ..." vào mic) để hỏi; đáp án stream từng từ qua LiveKit data channel, kèm thinking của model (reasoning) và quote lại câu hỏi gốc.
- **Chấm điểm phát âm AI** — mỗi câu đã nói chấm được trên bản user đã sửa: điểm tổng + 4 tiêu chí (Sounds / Stress / Fluency / Completeness). **Điểm từng chữ ẩn mặc định**, chỉ hiện khi bấm **Thống kê điểm số** (bảng riêng); nút **Nhận xét AI** xin góp ý AI (panel riêng). Xem `docs/reading-score.md`.
- **RAG tài liệu + web search** — agent tự tra tài liệu upload (Qdrant vector store + reranker) và Tavily web search khi cần, stream thinking ("Searching documents…") trước đáp án.
- **Heartbeat** — phòng đang live mà im lặng quá lâu sẽ được AI gợi chuyện bằng 1 câu hỏi.
- **Vòng đời phòng 3 trạng thái** — `open` (trống) → `live` (có người) → `ended` (chết). Hết người thì về open, bỏ hoang 24h mới ended.
- **Auth** — đăng ký/đăng nhập + Google OAuth, session cookie 7 ngày.
- **Trang public** — Home/Pricing/Blog/Contact, Rooms (live trước → open sau → ended cuối, window 10 + infinite scroll), Profile, Onboarding, **Demo chấm điểm đọc** (`/reading-demo`, chạy không cần backend).

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite 6, react-router-dom 7, TanStack Query 5, LiveKit components-react 2 + livekit-client 2, i18next, Zustand |
| Backend | Python 3.13, FastAPI, SQLModel, Uvicorn, Alembic migrations |
| AI | LangChain 1.x + LangGraph (agent), llama.cpp server (Gemma text gen + Qwen3 embedding), faster-whisper STT, Qwen3 reranker, Tavily search |
| Chấm phát âm | Scorer trong `app/ai/pronunciation.py` (phoneme GOP + 4 tiêu chí) + nhận xét AI qua LLM local (chỉ giải thích, không tính lại điểm) |
| Realtime | LiveKit (WebRTC video/audio/data channel) |
| Jobs | Celery (ai, ai_observer, ai_transcriber queues) + beat, Redis |
| Data | TiDB (MySQL-compatible), Qdrant (vectors), MinIO (S3 files), speech logs JSONL (`backend/log/speech/`, runtime — không commit) |
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

## Luồng chấm điểm phát âm (raw → sửa → chấm → nhận xét)

```
Nói ──▶ STT raw (pronunciation=None) ──▶ user sửa corrected_text (PATCH)
  ──▶ POST .../score ──▶ điểm tổng + 4 tiêu chí (điểm từng chữ ẨN)
  ──▶ [Thống kê điểm số] mở bảng riêng · [Nhận xét AI] xin góp ý AI
```

- Sửa câu sau khi đã chấm → điểm + nhận xét cũ bị reset, bắt chấm lại.
- Xin nhận xét khi chưa chấm → `409`. Chi tiết: `docs/reading-score.md`.
- Demo không cần backend: chạy frontend rồi mở `/reading-demo`.

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
│   │   ├── ai/                # LLM agent, STT (auto), VAD, workers, RAG, prompts,
│   │   │                      # pronunciation scorer (1 file, 10 parts) + feedback LLM,
│   │   │                      # speech_log (raw → sửa → chấm)
│   │   ├── api/routers/       # auth, google_auth, user, room, message, speech
│   │   │                      # (speech-logs: me/score/feedback), document,
│   │   │                      # notification (+ infra/health)
│   │   ├── integration/       # livekit token/webhook, redis, celery, minio
│   │   ├── models/            # SQLModel: User, Room, Message, ...
│   │   ├── schemas/           # Pydantic request/response + scoring/speech contracts
│   │   ├── services/          # CRUD repository (không business logic)
│   │   ├── seeds/             # seed users/rooms/messages
│   │   ├── config.py database.py security.py log.py main.py server.py
│   ├── alembic/               # migrations (chạy `alembic upgrade head`)
│   ├── tests/                 # unit / api / e2e / integration / security (pytest)
│   ├── .env.example .env.docker
│   └── pyproject.toml         # deps (uv)
├── frontend/src/
│   ├── api/                   # HTTP client (cookie auth)
│   ├── app/                   # router, guards, pages (Home/Pricing/Blog/Contact/.../ReadingDemo)
│   ├── features/              # rooms, chat (useRoomChat), auth, onboarding,
│   │                          # speaking (ReadingScoreCard + demo data), ...
│   ├── components/ data/ i18n/ lib/ stores/ styles/
│   └── main.jsx
├── docs/                      # overview, features, workflow, setup, reading-score
├── scripts/                   # dev.bat / golive.bat (chạy 1 lệnh) + mac.sh / linux.sh
├── nginx.conf
└── docker-compose.yml         # 12 services (compose STT/TTS giữ local ở máy AI)
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
| stt-server (máy AI riêng) | 8001 | faster-whisper-server `large-v3-turbo`, OpenAI-compatible — chạy ở máy AI, máy này chỉ cần trỏ `STT_SERVER_BASE_URL=http://<IP-máy-AI>:8001/v1` (chết thì auto fallback local) |

### Chạy 2 máy (khuyên dùng)

| Phe | Máy | Lệnh |
|---|---|---|
| AI: STT + TTS (máy AI) | máy có GPU NVIDIA | Bên máy AI: `docker compose -f docker-compose.stt.yml up -d` (lên `:8001` + `:8002`; 2 file compose/script AI giữ local ở máy đó, không nằm trong nhánh này), mở firewall 8001/8002, lấy IP bằng `tailscale ip -4` |
| Full stack (máy này, nhánh `student`) | máy còn lại | `scripts\dev.bat`, rồi sửa `backend/.env.docker`: `STT_PROVIDER=auto` (host sống thì dùng host, chết thì fallback local), `STT_SERVER_BASE_URL=http://100.x.y.z:8001/v1`, `TTS_BASE_URL=http://100.x.y.z:8002/v1`, `PRONUN_BASE_URL=` (trống = máy này tự chấm local), xong `docker restart api` |

> 2 máy nối nhau qua **Tailscale** (cùng 1 tài khoản/tailnet): IP `100.x` là tĩnh vĩnh viễn, không lo DHCP đổi số, không cần mở port router hay set IP tĩnh. Chỉ cần cả 2 máy đều `tailscale up` là thấy nhau.

## Quick start

### 1 lệnh (khuyên dùng)

| Platform | Command |
|---|---|
| Windows (dev/local) | `scripts\dev.bat` |
| Windows (public) | `scripts\golive.bat` |
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
| `LLM_BASE_URL` | `http://localhost:8012/v1` | llama.cpp text gen |
| `LLM_MODEL` | `gemma-4-E2B-it` | Model chat + nhận xét phát âm AI (local, không key riêng) |
| `EMBEDDING_BASE_URL` | `http://localhost:8013/v1` | llama.cpp embedding |
| `QDRANT_HOST` / `QDRANT_PORT` | `localhost` / `6333` | Vector DB (trong docker: `qdrant`) |
| `LIVEKIT_MODE` + `LIVEKIT_LOCAL_URL` | `local` / `ws://localhost:7880` | WebRTC (trong docker: `ws://livekit:7880`; public: `LIVEKIT_MODE=cloud`) |
| `ROOM_EMPTY_END_SECONDS` | `86400` | Phòng trống bao lâu thì ended |
| `AI_TIMEOUT_SECONDS` | `300` | Trần 1 job AI |
| `TAVILY_API_KEY` | — | Web search (không có thì agent bỏ qua) |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | — | Login Google (cần OAuth Client ID, không dùng service-account) |
| `PRONUN_BASE_URL` | — | Scorer remote (không có thì chấm local → heuristic) |
| `SCORING_MAX_PARALLEL` | `1` | Số lượt chấm local chạy song song (1 = tuần tự, chống OOM máy host) |
| `SPEECH_LOG_DIR` | `backend/log/speech` | Nơi lưu transcript + audio từng câu (runtime, không commit) |

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
| GET | `/rooms/{room_id}/speech-logs/me` | Cookie | Câu của chính mình (để sửa/chấm) |
| GET | `/rooms/{room_id}/speech-logs` | Cookie | Toàn bộ room, group theo user |
| GET | `/rooms/{room_id}/speech-logs/summary` | Cookie | Gộp sort theo giờ (cho mục summary) |
| PATCH | `/rooms/{room_id}/speech-logs/{message_id}` | Cookie | Sửa `corrected_text` (reset điểm cũ) |
| POST | `/rooms/{room_id}/speech-logs/{message_id}/score` | Cookie | Chấm phát âm 1 câu (máy host tính, lưu DB) |
| POST | `/rooms/{room_id}/speech-logs/{message_id}/feedback` | Cookie | Nhận xét AI (chỉ sau khi đã chấm) |
| POST | `/sessions/{session_id}/feedback` | Cookie | AI feedbacks cả session (gọn, chỉ nêu phần sai; 409 nếu chưa chấm câu nào) |
| GET/POST | `/messages/` | Cookie | Chat (`@ai` đầu tin nhắn → trigger agent) |
| GET | `/users/{id}` `/users/me` | Cookie | Users |
| — | `/documents/` `/notifications/` | Cookie | Upload tài liệu RAG, thông báo |

## Tài liệu

| File | Nội dung |
|---|---|
| `docs/overview.md` | Kiến trúc tổng thể, services/ports, vòng đời phòng, quy ước code |
| `docs/features.md` | Danh sách tính năng đã chạy thật |
| `docs/workflow.md` | Sơ đồ các luồng (join/leave, chat, `@ai`, transcript, heartbeat, public hosting) |
| `docs/setup.md` | Cài đặt: dev local, full docker, public qua Tailscale |
| `docs/reading-score.md` | Logic chấm điểm đọc AI + thiết kế UI (ẩn điểm từng chữ, 2 nút riêng) + demo |

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

## Troubleshooting

| Hiện tượng | Nguyên nhân thường gặp |
|---|---|
| `@ai` chỉ hiện "thinking" rồi ra 1 cục | Tab mất kết nối LiveKit (không stream live, chỉ poll DB). Kiểm tra mic/cam có nối không; F12 xem console có `Invalid URL` |
| Mic/cam báo lỗi thiết bị | Lỗi phía browser: chưa cấp quyền, không có thiết bị, hoặc thiết bị đang bị app khác giữ (Zoom/Zalo/tab khác) |
| List rooms hiện người đã out | Đợi ~5–10s (members refresh 5s, list 10s); nếu kẹt lâu là webhook miss — bấm Reload |
| Worker báo `Unknown column` | Worker cũ hơn migration — `docker restart ai-worker` (code bind-mount) |
| Job AI timeout 300s | LLM CPU ~3.7 tok/s; câu RAG nặng có thể quá trần — câu trả lời ngắn gọn hơn |
| `/feedback` lỗi | LLM local (`:8012`) chưa chạy — điểm số vẫn chấm bình thường, chỉ nhận xét AI là không chạy |
| Điểm từng chữ không hiện | Đúng thiết kế — bấm **Thống kê điểm số** để mở bảng riêng (`docs/reading-score.md`) |

## License

Chưa có file `LICENSE` trong repo.
