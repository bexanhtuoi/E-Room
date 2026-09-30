# E-Room — Overview

> Cập nhật: 09/2026 · Khớp kiến trúc hiện tại (`services/` + `repositories/` + `shared/` + `tasks/`, `ai/` chia package).

## 1. E-Room là gì?

E-Room là nền tảng **luyện nói tiếng Anh theo nhóm nhỏ** (tối đa 6 người/phòng) với:

- **Video call real-time** (LiveKit WebRTC): mic/cam/share màn hình (desktop), hand-raise, emoji reactions.
- **Transcript live từng người nói**: worker nghe audio mỗi participant, VAD cắt câu, STT chuyển thành chữ, hiện ngay trong chat kèm confidence badge.
- **Trợ lý AI `@ai`**: mention `@ai` trong chat **hoặc nói "@ai ..." vào mic** → đáp án **stream từng từ** về browser, kèm **thinking của model** và quote lại câu hỏi gốc.
- **Chấm điểm phát âm + ngữ pháp AI**: điểm tổng + 4 tiêu chí, điểm từng chữ ẩn mặc định (xem `reading-score.md`); góp ý từng từ yếu gồm khẩu hình + phiên âm Việt.
- **Session AI**: feedback cả buổi, hỏi đáp trên transcript (sync + SSE stream), transcript gộp sort theo giờ.
- **RAG + web search**: agent tự tra tài liệu upload (Qdrant + reranker) và Tavily web search khi câu hỏi cần.
- **Heartbeat**: phòng live mà im lặng quá lâu → AI gợi chuyện.
- **Schedule + Private Room**: đặt lịch hẹn, phòng riêng ẩn khỏi list public.
- AI chạy **hybrid** (LLM/STT/TTS trỏ server ngoài qua env, fallback local khi chết), dữ liệu on-premise (TiDB/Qdrant/MinIO chạy Docker).

## 2. Ai dùng? Vào bằng gì?

| Đối tượng | Cách vào | Ghi chú |
|---|---|---|
| Dev (local) | `http://localhost:3001` (prod container) hoặc `https://localhost:3000` (dev) | Mic/cam cần HTTPS → dùng bản HTTPS hoặc localhost |
| Khách public | `https://<machine>.<tailnet>.ts.net` (Tailscale Funnel) | Không cài gì, mic/cam chạy vì đã HTTPS |
| Tài khoản | Đăng ký thường hoặc Google OAuth | Session cookie 7 ngày |

## 3. Tech stack (thực tế)

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite 6, react-router-dom 7, TanStack Query 5, LiveKit components-react 2 + livekit-client 2, i18next, Zustand |
| Backend | Python 3.13, FastAPI, SQLModel, Uvicorn, Alembic, `uv` — kiến trúc `routers → services → repositories → models` |
| AI | LangChain 1.x + LangGraph (agent), LLM qua `LLM_BASE_URL` (OpenAI-compatible), Qwen3 reranker, Tavily search |
| STT | faster-whisper-server `:8001` (máy AI, GPU) + dispatch `auto`: server sống thì dùng, chết thì fallback local; tràn sang cloud khi hàng đợi ≥4 job (tiếng Anh + có key) |
| TTS | Kokoro-compatible server `:8002`, 4 giọng `af_heart`/`am_adam`/`bf_emma`/`bm_george` |
| Chấm phát âm | Package `app/ai/pronunciation/` (wav2vec2 + phoneme GOP local trên máy host, chấm tuần tự) + nhận xét AI qua LLM (prompt ở `app/ai/prompts/feedback_utterance.md` + `assessment.md`) |
| Realtime | LiveKit (video/audio/**data channel**) — data channel chở transcript + AI stream + emoji/hand-raise |
| Jobs | Celery (queues: `ai`, `ai_observer`, `ai_transcriber`) + beat, Redis |
| Data | TiDB (MySQL-compatible), Qdrant (vectors), MinIO (S3 files), speech logs JSONL (`backend/log/speech/`, runtime) |
| Auth | JWT cookie HttpOnly + Google OAuth |
| Public | Tailscale Funnel (TLS) + Nginx reverse proxy nội bộ |

## 4. Kiến trúc tổng thể

```mermaid
flowchart LR
    subgraph Visitor["Khách (không cài gì)"]
        WEB[Browser<br/>https://...ts.net]
    end
    subgraph Home["PC nhà (Docker)"]
        FUN[Tailscale Funnel<br/>TLS edge]
        NG[Nginx :8080<br/>/ → frontend<br/>/api → api (600s)<br/>/rtc* → livekit]
        FE[frontend :3000<br/>prod build]
        API[api :8000<br/>FastAPI]
        W[ai-worker<br/>ai-transcriber<br/>ai-observer<br/>ai-beat]
        DB[(TiDB :4000)]
        RD[(Redis :6379)]
        QD[(Qdrant :6333)]
        LK[livekit :7880<br/>self-host<br/>(dự phòng)]
        OL[ollama :11434<br/>LLM local<br/>reranker :8014]
    end
    subgraph Cloud["LiveKit Cloud (free)"]
        LC[wss TURN/SFU<br/>media + signaling]
    end
    subgraph AIServer["Máy AI (GPU)"]
        STT[STT :8001<br/>large-v3-turbo]
        TTS[TTS :8002<br/>Kokoro]
    end
    WEB -->|https| FUN --> NG
    NG --> FE & API & LK
    API <--> DB & RD
    W <--> RD & DB & OL & QD
    API & W -->|STT/TTS/LLM| AIServer
    WEB <-->|wss + UDP media| LC
    W <-->|join room cloud| LC
    LC -->|webhook join/leave| FUN
```

> Hiện tại media + signaling chạy **LiveKit Cloud** (free tier) vì không mở được port UDP ở nhà. LiveKit self-host giữ lại để dev LAN/revert (`dev.bat` ép `LIVEKIT_MODE=local`, `golive.bat` ép `cloud` + stop livekit self-host).

## 5. Services & ports

| Service | Port | Public? | Ghi chú |
|---|---|---|---|
| Nginx | 8080 (funnel 443) | ✅ qua Funnel | Reverse proxy duy nhất ra ngoài |
| frontend | 3000 (nội bộ, map 3001) | ➖ qua Nginx `/` | Prod build (SPA, no-cache; `/assets` cache 1 năm) |
| api | 8000 (nội bộ) | ➖ qua Nginx `/api` | REST + webhook, timeout 600s cho AI |
| livekit (self-host) | 7880, UDP 50000–50100 | ❌ đang tắt (public) | Dự phòng, hiện dùng Cloud |
| ollama | 11434 | ❌ | LLM local (khi không trỏ server ngoài) |
| reranker | 8014 | ❌ | Qwen3-Reranker (llama.cpp server) |
| qdrant | 6333 | ❌ | Vectors |
| tidb | 4000 | ❌ | SQL |
| redis | 6379 | ❌ | Queue + presence + heartbeat locks |
| minio | 9000/9001 | ❌ | Files |
| STT/TTS (máy AI) | 8001/8002 | ❌ (LAN/Tailscale) | Giữ local ở máy AI, không nằm trong compose này |

Chỉ Nginx (qua Funnel) là cửa công khai. **Không bao giờ** forward DB/Redis/MinIO ra internet.

## 6. Vòng đời phòng (3 trạng thái)

```
idle ── có người vào ──▶ active ── người cuối out ──▶ idle
 ▲                                                              │
 └────────────── trống quá ROOM_EMPTY_END_SECONDS (24h) ──▶ ended ──┘
```

| Status (code `RoomStatus`) | Label UI | Nghĩa |
|---|---|---|
| `idle` | Open | Trống, vào được ngay |
| `active` | Live now | Đang có người |
| `ended` | Ended | Chết, ẩn bớt (vẫn mở lại được qua link) |

- Vào (`register_participant_join`): presence + mở session + enqueue observer/transcriber.
- Người cuối out (`drop_participant_from_room`): về `idle`, đóng session, **enqueue chấm nốt** các câu chưa chấm.
- `ended` chỉ từ task `end_stale_empty_rooms` (trống quá 24h). Phòng hẹn (`scheduled_at`) quá 24h → xóa hẳn (`delete_expired_scheduled_rooms`).
- Phòng riêng (`is_private`): ẩn khỏi list public, chỉ host/admin/email được mời mới vào (`ensure_room_access`).

Presence (ai đang trong phòng) lưu ở Redis `room:{id}:participants` — ghi bởi **webhook LiveKit** (bỏ qua prefix `ai_`) + **endpoint join/leave trực tiếp** (idempotent, chống miss webhook khi tab đóng đột ngột). Worker/transcriber/observer/assistant join dưới identity `ai_*` nên **không chiếm seat, không hiển thị**.

## 7. Bố cục repo

```
E-Room/
├── backend/app/
│   ├── ai/            # llm, rag, stt, tts, vad, pronunciation (package con + helpers), prompts/
│   ├── api/routers/   # endpoint mỏng: validate → service → response (cấm DB/HTTPException)
│   ├── services/      # BUSINESS: XxxService + singleton
│   ├── repositories/  # DATA ACCESS: XxxCrud + singleton
│   ├── shared/        # lá: constants, keys, exceptions
│   ├── tasks/         # Celery jobs: helpers, room_jobs, maintenance, scoring
│   ├── integration/   # livekit, redis, celery, minio
│   ├── models/ schemas/ seeds/
│   └── config.py database.py security.py log.py main.py server.py
├── backend/alembic/   # migrations — luôn chạy `alembic upgrade head`
├── backend/tests/     # unit / api / e2e / integration / security
├── frontend/src/
│   ├── api/           # HTTP client (cookie)
│   ├── app/           # router, guards, pages
│   ├── features/      # rooms, chat, auth, onboarding, profile, ...
│   └── ...components/data/i18n/lib/stores/styles
├── scripts/           # dev.bat (local) / golive.bat (public) + mac.sh / linux.sh
├── docs/              # overview, features, workflow, setup, reading-score (bạn đang đọc)
├── nginx.conf         # reverse proxy cho Funnel
└── docker-compose.yml # 14 services
```

## 8. Quy ước quan trọng (đồng nghiệp mới đọc trước khi code)

1. **Tầng rõ ràng** — routers mỏng (validate → service → response), không query DB trực tiếp, không raise HTTPException; services giữ business, repositories giữ CRUD/query, lỗi domain gom ở `shared/exceptions.py` (trả `{code, detail}` tiếng Việt).
2. **AI workers join phòng dưới identity `ai_*`** — webhook + presence + UI đều phải loại chúng ra khỏi seat/danh sách.
3. **Token LiveKit**: backend ký (`room = str(room_id)`), user identity = `user_id` → **1 tài khoản vào 2 máy cùng lúc sẽ đá nhau** (LiveKit duplicate identity).
4. **Mic/cam cần HTTPS** (trừ localhost) — test mobile/LAN phải dùng bản HTTPS.
5. **LLM qua server ngoài** — đáp án dài có thể ~1 phút; trần 1 job `AI_TIMEOUT_SECONDS` (mặc định 900s).
6. **Test DB sqlite dùng chung file** — chạy lẻ thấy lỗi constraint lạ thì xóa `backend/test_eroom.db` chạy lại.
7. **Redis là hạ tầng bắt buộc** — Celery queues + presence phòng + heartbeat + locks worker đều qua Redis. Tắt container redis là mất transcript live + AI.
8. **Chấm điểm chạy tuần tự** — `SCORING_MAX_PARALLEL=1`, điểm lưu DB `pronunciation_scores` (xem `reading-score.md`).
9. Quy chuẩn đầy đủ ở `.opencode/rules/` (version cùng repo). Xem tiếp: `features.md` (tính năng), `workflow.md` (các luồng), `setup.md` (cài đặt).
