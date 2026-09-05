# E-Room — Overview

> Version tài liệu: v2.0.0 · Cập nhật: 09/2026

## 1. E-Room là gì?

E-Room là nền tảng **luyện nói tiếng Anh theo nhóm nhỏ** (tối đa 4 người/phòng) với:

- **Video call real-time** (LiveKit WebRTC): mic/cam/share màn hình (desktop), hand-raise, emoji reactions.
- **Transcript live từng người nói**: worker nghe audio mỗi participant, VAD cắt câu, STT chuyển thành chữ, hiện ngay trong chat kèm icon mic.
- **Trợ lý AI `@ai`**: mention `@ai` trong chat **hoặc nói "@ai ..." vào mic** → đáp án **stream từng từ** về browser, kèm **thinking của model** (reasoning) và quote lại câu hỏi gốc.
- **RAG + web search**: agent tự tra tài liệu upload (Qdrant + reranker) và Tavily web search khi câu hỏi cần.
- **Heartbeat**: phòng live mà im lặng quá lâu → AI gợi chuyện.
- Tất cả AI chạy **local** (llama.cpp), dữ liệu on-premise (TiDB/Qdrant/MinIO chạy Docker).

## 2. Ai dùng? Vào bằng gì?

| Đối tượng | Cách vào | Ghi chú |
|---|---|---|
| Dev (local) | `http://localhost:3000` (prod) hoặc `:3002` (dev) | Mic/cam cần HTTPS → dùng bản HTTPS hoặc localhost |
| Khách public | `https://<machine>.<tailnet>.ts.net` (Tailscale Funnel) | Không cài gì, mic/cam chạy vì đã HTTPS |
| Tài khoản | Đăng ký thường hoặc Google OAuth | Session cookie 7 ngày |

## 3. Tech stack (thực tế)

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite 6, react-router-dom 7, TanStack Query 5, LiveKit components-react 2 + livekit-client 2, i18next, Zustand |
| Backend | Python 3.13, FastAPI, SQLModel, Uvicorn, Alembic, `uv` |
| AI | LangChain 1.x + LangGraph (agent), llama.cpp (Gemma text-gen + Qwen3 embedding), faster-whisper STT (local), Qwen3 reranker, Tavily search |
| Realtime | LiveKit (video/audio/**data channel**) — data channel chở transcript + AI stream |
| Jobs | Celery (queues: `ai`, `ai_observer`, `ai_transcriber`) + beat, Redis |
| Data | TiDB (MySQL-compatible), Qdrant (vectors), MinIO (S3 files) |
| Auth | JWT cookie HttpOnly + Google OAuth |
| Public | Tailscale Funnel (TLS) + Caddy reverse proxy nội bộ |

## 4. Kiến trúc tổng thể

```mermaid
flowchart LR
    subgraph Visitor["Khách (không cài gì)"]
        WEB[Browser<br/>https://...ts.net]
    end
    subgraph Home["PC nhà (Docker)"]
        FUN[Tailscale Funnel<br/>TLS edge]
        CAD[Caddy :8080<br/>/ → frontend<br/>/api → api<br/>/rtc* → livekit]
        FE[frontend :3000<br/>prod build]
        API[api :8000<br/>FastAPI]
        W[ai-worker<br/>ai-transcriber<br/>ai-observer<br/>ai-beat]
        DB[(TiDB :4000)]
        RD[(Redis :6379)]
        QD[(Qdrant :6333)]
        LK[livekit :7880<br/>self-host<br/>(dự phòng)]
        LM[llama :8012/:8013<br/>Gemma + Qwen3-emb]
    end
    subgraph Cloud["LiveKit Cloud (free)"]
        LC[wss TURN/SFU<br/>media + signaling]
    end
    WEB -->|https| FUN --> CAD
    CAD --> FE & API & LK
    API <--> DB & RD
    W <--> RD & DB & LM & QD
    WEB <-->|wss + UDP media| LC
    W <-->|join room cloud| LC
    LC -->|webhook join/leave| FUN
```

> Hiện tại media + signaling chạy **LiveKit Cloud** (free tier) vì không mở được port UDP ở nhà. LiveKit self-host giữ lại để dev LAN/revert.

## 5. Services & ports

| Service | Port | Public? | Ghi chú |
|---|---|---|---|
| Caddy | 8080 (funnel 443) | ✅ qua Funnel | Reverse proxy duy nhất ra ngoài |
| frontend | 3000 (nội bộ) | ➖ qua Caddy | Prod build |
| api | 8000 (nội bộ) | ➖ qua Caddy `/api` | REST + webhook |
| livekit (self-host) | 7880, UDP 50000–50100 | ❌ đang tắt | Dự phòng, hiện dùng Cloud |
| llama text-gen | 8012 | ❌ | Gemma |
| llama embedding | 8013 | ❌ | Qwen3-Embedding |
| qdrant | 6333 | ❌ | Vectors |
| tidb | 4000 | ❌ | SQL |
| redis | 6379 | ❌ | Queue + presence |
| minio | 9000/9001 | ❌ | Files |

Chỉ Caddy (qua Funnel) là cửa công khai. **Không bao giờ** forward DB/Redis/MinIO ra internet.

## 6. Vòng đời phòng (3 trạng thái)

```
open (idle) ── có người vào ──▶ live (active) ── người cuối out ──▶ open
   ▲                                                                │
   └────────────── trống quá ROOM_EMPTY_END_SECONDS (24h) ──▶ ended ──┘
```

| Status | Label UI | Nghĩa |
|---|---|---|
| `idle` | Open | Trống, vào được ngay |
| `active` | Live now | Đang có người |
| `ended` | Ended | Chết, ẩn bớt (vẫn mở lại được qua link) |

Presence (ai đang trong phòng) lưu ở Redis `room:{id}:participants` — webhook LiveKit + endpoint `POST /rooms/{id}/leave` (client gọi trực tiếp khi bấm Leave/back, chống miss webhook). Identity `ai_*` (transcriber/observer/assistant) **không chiếm seat, không hiển thị**.

## 7. Bố cục repo

```
E-Room/
├── backend/app/
│   ├── ai/            # agent, STT, VAD, transcriber/observer, RAG, tasks
│   ├── api/routers/   # auth, google_auth, user, room, message, document, notification
│   ├── integration/   # livekit, redis, celery, minio
│   ├── models/ schemas/ services/ seeds/
│   └── config.py database.py security.py main.py server.py
├── backend/alembic/   # migrations — luôn chạy `alembic upgrade head`
├── backend/tests/     # unit / api / e2e / integration / security
├── frontend/src/
│   ├── api/           # HTTP client (cookie)
│   ├── app/           # router, guards, pages
│   ├── features/      # rooms, chat, auth, onboarding, ...
│   └── ...components/data/i18n/lib/stores/styles
├── scripts/           # win.bat / mac.sh / linux.sh (dev) + host-public.bat (public)
├── docs/              # overview, features, workflow, setup (bạn đang đọc)
├── Caddyfile          # reverse proxy cho Funnel
└── docker-compose.yml # 13 services
```

## 8. Quy ước quan trọng (đồng nghiệp mới đọc trước khi code)

1. **Service layer chỉ CRUD** — business logic nằm ở router/tasks, không query DB trong router.
2. **AI workers join phòng dưới identity `ai_*`** — webhook + UI đều phải loại chúng ra khỏi seat/danh sách.
3. **Token LiveKit**: backend ký (`room = str(room_id)`), user identity = `user_id` → **1 tài khoản vào 2 máy cùng lúc sẽ đá nhau** (LiveKit duplicate identity).
4. **Mic/cam cần HTTPS** (trừ localhost) — test mobile/LAN phải dùng bản HTTPS.
5. **Model AI nặng (CPU ~3.7 tok/s)** — đáp án dài ~1 phút là bình thường; RAG nặng có thể chạm trần worker 300s.
6. **Test DB sqlite dùng chung file** — chạy lẻ thấy lỗi constraint lạ thì xóa `backend/test_eroom.db` chạy lại.
7. Xem tiếp: `features.md` (tính năng), `workflow.md` (các luồng), `setup.md` (cài đặt).
