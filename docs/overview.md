---
title: ERoom
tags:
  - project
  - realtime
  - AI
  - edtech
created: 2026-05-04
updated: 2026-06-06
status: development
aliases:
  - E-Room
---

# ERoom

> [!abstract] Nền tảng luyện nói tiếng Anh với AI — Thế hệ mới
> Phòng nhóm 3-5 người theo chủ đề tag. AI Agent 3-trong-1: sửa lỗi chính tả/phát âm + Expert RAG + Heartbeat. TTS phát âm chuẩn. Hệ thống Subscription Pro/Pro+.

> [!info] Điều hướng nhanh
> **[[features|Tính năng]]** (30+ đặc tả) · **[[workflow|Luồng hoạt động]]** (10+ luồng) · **[[tasks|Công việc]]** · **[[notes|Ghi chú kỹ thuật]]** · **[[decisions|Quyết định kiến trúc]]** (20 ADR)

---

## Tổng quan

**ERoom** là nền tảng luyện nói tiếng Anh thời gian thực thế hệ mới, nơi người dùng được ghép cặp vào nhóm nhỏ (3-5 người) dựa trên **hệ thống tag** (lĩnh vực hứng thú) thay vì chỉ theo ngành nghề cứng nhắc. Trong mỗi phòng, một **AI Agent đảm nhận đồng thời 3 vai trò**: sửa lỗi chính tả/ngữ pháp/phát âm, chuyên gia hỏi đáp kiến thức chuyên ngành (RAG + Web Search), và người khởi động hội thoại (Heartbeat).

### Đột phá của ERoom

| Điểm khác biệt | Mô tả |
|----------------|-------|
| 🏷️ **Hệ thống Tag** | Người dùng chọn tag hứng thú (Openclaw, Marketing, Vibe Coding, Physics...) khi đăng ký. Ghép cặp tự động theo tag thay vì career field cứng nhắc |
| 🤖 **AI Agent 3-trong-1** | Một agent duy nhất vừa sửa lỗi chính tả + phát âm, vừa là chuyên gia trả lời câu hỏi, vừa khởi động hội thoại khi phòng im lặng |
| 🎙️ **TTS Phát âm chuẩn** | AI không chỉ sửa lỗi mà còn đọc mẫu phát âm chuẩn — người dùng bấm nút là nghe ngay |
| 🧠 **RAG + Web Search** | Agent nạp kiến thức từ kho tài liệu (Minio) và tìm kiếm web thời gian thực để trả lời chuyên sâu |
| 🛡️ **An toàn & Chống lạm dụng** | Phát hiện ảnh nhạy cảm khi video call, ngăn chặn người dùng lợi dụng agent vào việc riêng (coding, v.v.) |
| 💰 **Subscription thông minh** | Pro/Pro+ với quota agent khác biệt. Chỉ cần 1 user Pro trong room là cả room được hưởng agent nâng cao |

---

## Nguyên tắc cốt lõi

### Tự do với Tag
Không còn bị giới hạn vào 1 career field. Người dùng chọn nhiều tag hứng thú (tối đa 10) — từ Openclaw, Vibe Coding, Marketing, Physics, Math đến bất kỳ lĩnh vực nào. Hệ thống ghép cặp dựa trên độ tương đồng tag, tạo ra những cuộc trò chuyện đa dạng và thú vị hơn.

### AI là trung tâm — 3 vai trò trong 1 agent
AI không phải add-on. AI là **người tham gia xuyên suốt** với 3 vai trò đồng thời:
1. **Corrector**: Nghe từng câu → sửa chính tả, ngữ pháp, phát âm → trả kết quả + đọc mẫu TTS
2. **Expert**: Nạp kiến thức từ RAG (Minio) và Web Search → trả lời câu hỏi chuyên môn trong ChatWindow
3. **Heartbeat**: Phát hiện phòng im lặng → đưa ra câu hỏi khởi động phù hợp chủ đề

### Bảo mật & Chống lạm dụng
- **Phát hiện ảnh nhạy cảm**: AI quét video frame, nếu phát hiện nội dung không phù hợp → tự động tắt video + cảnh báo/ban
- **Ngăn chặn lạm dụng agent**: Agent được huấn luyện để từ chối các yêu cầu không liên quan (coding, việc riêng). Prompt guardrail + classifier phát hiện mis-use

### Monetization thông minh
- **Free**: Hạn chế quota agent, không tạo room, giới hạn 2 phòng/ngày
- **Pro**: Agent nâng cao, tạo room với tag mong muốn, quota cao hơn. **Chỉ cần 1 Pro trong room → cả room hưởng agent nâng cao**
- **Pro+**: Tất cả quyền Pro + Tự động take note (AI ghi chú), TTS, Room Series, Analytics nâng cao, Leaderboard

---

> [!warning] Cập nhật 2026-06-07 — Kiến trúc thực tế
> - **Database**: Local MySQL — **không phải** TiDB Cloud (xem [[decisions#ADR-021|ADR-021]])
> - **Vector store**: `TiDBRawVectorStore` (MySQL table, pickle numpy, brute-force cosine) + `NumpyVectorStore` fallback
> - **STT**: `faster-whisper small.en` (CUDA float16) — **không phải** FunASR SenseVoiceSmall, **không phải** Whisper API
> - **Pronunciation scoring**: Whisper confidence + CMU Dictionary lookup (không phải GOP/Wav2Vec2)
> - **LLM**: llama.cpp local (Gemma 4 E2B Q8_0, port 8012) — **không phải** GPT-4o
> - **Embedding**: llama.cpp local (Qwen3 Embedding 0.6B Q8_0, port 8013)
> - **TTS**: Supertonic local (CPU) — ONNX model
> - **Image Moderation**: Chưa implement
> - **coTURN**: Chưa cấu hình trong code
> - **Không có Celery**: Mọi tác vụ chạy in-process (async/ThreadPoolExecutor)
> - Chi tiết cấu trúc thực tế: [[project-structure]]

## Kiến trúc hệ thống (thiết kế)

```
┌──────────────────────────────────────────────────────────────────┐
│                         TẦNG CLIENT                              │
│  ┌──────────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐   │
│  │ React (Vite)  │  │ LiveKit  │  │ WebSocket│  │ TTS Player │   │
│  │ + React Router│  │ Client   │  │ Client   │  │ (Audio)    │   │
│  └──────┬───────┘  └────┬─────┘  └────┬─────┘  └─────┬──────┘   │
└─────────┼───────────────┼─────────────┼───────────────┼──────────┘
          │ HTTP/REST     │ WebRTC UDP  │ WSS           │ HTTPS
          ▼               ▼             ▼               ▼
┌──────────────────────────────────────────────────────────────────┐
│                      TẦNG GATEWAY                                │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                    Nginx Reverse Proxy                      │  │
│  │  /api/* → FastAPI    /ws/* → WebSocket    SSL + WSS        │  │
│  └────────────────────────┬───────────────────────────────────┘  │
└───────────────────────────┼──────────────────────────────────────┘
                            │
            ┌────────────────┼────────────────┐
            ▼                ▼                ▼
┌─────────────────┐ ┌──────────────┐ ┌──────────────────────┐
│  FastAPI BE     │ │ LiveKit SFU  │ │                      │
│  (REST + WS)    │ │ (WebRTC)     │ │   (In-process)       │
└───────┬─────────┘ └──────┬───────┘ └──────────────────────┘
        │                  │
        ▼                  │
┌───────────────┐          │
│  MySQL        │          │
│  + Vector     │          │
│  Store        │          │
│  (TiDBRaw)    │          │
└───────┬───────┘          │
        │                  │
        ▼                  │
┌───────────────┐          │
│    Redis      │          │
│  Cache+Queue  │          │
└───────────────┘          │
                           │
        ┌──────────────────┘
        ▼
┌──────────────────────┐
│   coTURN Server      │
│   (NAT Traversal)    │
└──────────────────────┘
```

> [!warning] Cập nhật 2026-06-07
> Luồng dữ liệu dưới đây là **thiết kế mục tiêu**. Code thực tế đã implement:
> - **Bước 5-6**: PronunciationPipeline local — Whisper (faster-whisper small.en) + CMU Dictionary, **không phải** FunASR/Wav2Vec2
> - **Pronunciation scoring**: Whisper confidence (avg_logprob → 0-100), **không phải** GOP/Wav2Vec2 forced alignment
> - **LLM**: Local (llama.cpp / Gemma 4 E2B, port 8012) thay vì GPT-4o
> - **Embedding**: Local (llama.cpp / Qwen3 Embedding 0.6B, port 8013)
> - **Bước 7**: TTS: Supertonic local (CPU) — ONNX model
> - **Không có Celery**: Mọi tác vụ chạy in-process (async/ThreadPoolExecutor)
> - **Bước 10**: NSFW chưa implement
> - **Bước 11**: Đánh giá qua PronunciationPipeline, take note chưa implement
> - Chi tiết: [[dev-notes]], [[pronunciation-workflow]]

### Cách dữ liệu luân chuyển (theo kiến trúc mới)

| Bước | Hành động của người dùng | Phản hồi của hệ thống |
|------|--------------------------|------------------------|
| 1 | Đăng ký + chọn tag | Lưu tags vào `user_tags` (53 preset tags) |
| 2 | Nhấn "Bắt đầu nói" | `POST /api/rooms/match` → tìm room phù hợp hoặc vào queue |
| 3 | Tìm thấy người ghép | LiveKit tạo phòng, matching engine (Jaccard + 3-stage fallback) |
| 4 | Agent giới thiệu | AI Briefing: chủ đề, câu hỏi mở đầu |
| 5 | Người dùng nói | Âm thanh → WebSocket `/ws/audio` → PronunciationPipeline (Whisper + CMU Dict) → transcript + pronunciation scores |
| 6 | AI sửa lỗi | Nếu overall < 70: LLM (local) sửa phát âm → trả về ChatWindow |
| 7 | TTS | ⏳ Chưa implement |
| 8 | Expert Q&A | Query router → RAG (OpenAIEmbed + TiDBRawVectorStore) + Brave Search → LLM answer |
| 9 | Phòng im lặng | Heartbeat loop (asyncio) → LLM question |
| 10 | Image Moderation | ⏳ Chưa implement |
| 11 | Phiên kết thúc | PronunciationPipeline scores. Note: ⏳ Chưa implement |
| 12 | Người dùng xem lại | Vào Profile → Session History |

---

## Tech Stack

### Frontend

| Công nghệ | Phiên bản | Mục đích |
|-----------|---------|---------|
| React | 19+ | Thư viện UI (SPA) |
| Vite | 6+ | Build tool, HMR |
| React Router | 7+ | Client-side routing |
| Bootstrap 5 | 5.3+ | CSS framework (react-bootstrap) |
| Zustand | 5+ | Quản lý state (5 stores) |
| @tanstack/react-query | 5+ | Server state & caching |
| @livekit/components-react | latest | LiveKit UI components |
| livekit-client | latest | WebRTC client SDK |
| i18next | latest | Đa ngôn ngữ (en + vi) |
| react-markdown | 10+ | Markdown rendering |
| react-icons | 5+ | Icon library |
| vitest | 4+ | Unit testing |
| jsdom | latest | DOM testing environment |

### Backend

| Công nghệ | Phiên bản | Mục đích |
|-----------|---------|---------|
| FastAPI | 0.136+ | Async REST + WebSocket framework |
| Uvicorn | 0.46+ | ASGI server |
| SQLModel | 0.0.38+ | ORM (SQLAlchemy-based) |
| Alembic | 1.18+ | Database migrations |
| Pydantic | 2+ | Xác thực dữ liệu |
| PyJWT | 2.12+ | JWT auth + xoay refresh token |
| Argon2-cffi | 25+ | Băm mật khẩu (thay Passlib) |
| Redis-py | 7.4+ | Redis client |
| httpx | 0.28+ | HTTP client |
| minio | 7+ | Object storage client (RAG docs) |
| faster-whisper | 1.1+ | STT local (small.en, CUDA float16) |
| langchain | 1.2+ | Document processing, agent orchestration |
| langgraph | 1.0+ | Agent graph workflows |
| langchain-openai | 1.1+ | OpenAIEmbeddings (LM Studio) |
| TiDBRawVectorStore | custom | Vector store (MySQL table, pickle numpy, brute-force cosine) |

### Hạ tầng

| Công nghệ | Phiên bản | Mục đích |
|-----------|---------|---------|
| MySQL | 8+ | Database chính (local, SQLModel + PyMySQL) |
| SQLite | 3+ | Test database (auto trong pytest) |
| Redis | 7+ | Queue, cache, pub/sub, session store |
| LiveKit Server | 1.7+ | WebRTC SFU |
| coTURN | 4.6+ | TURN server NAT traversal |
| Minio | latest | Object storage cho RAG documents & avatar |
| Nginx | 1.25+ | Reverse proxy |
| Docker | 24+ | Containerization |
| Docker Compose | 2+ | Local dev orchestration |

### Dịch vụ AI

| Dịch vụ | Nhà cung cấp | Model / Engine |
|---------|-------------|----------------|
| Chuyển giọng nói thành văn bản | Tự host (local) | faster-whisper small.en (CUDA) |
| Phoneme Lookup | Tự host (local) | CMU Dictionary (cmudict.json) |
| Sửa lỗi & Expert Q&A | Tự host (llama.cpp) | Gemma 4 E2B Q8_0 (port 8012, OpenAI-compatible) |
| Nhịp tim AI | Tự host (llama.cpp) | Gemma 4 E2B Q8_0 |
| Đánh giá phiên + Take Note | Tự host (llama.cpp) | Gemma 4 E2B Q8_0 |
| TTS (Text-to-Speech) | Tự host (CPU) | Supertonic ONNX |
| Vector nhúng | Tự host (llama.cpp) | Qwen3 Embedding 0.6B Q8_0 (port 8013) |
| Image Moderation | Chưa implement | ⏳ (nsfw_detector) |
| Web Search | Brave Search API | Brave Search API (có config) |
| Pronunciation Scoring | Self-contained pipeline | Whisper confidence + CMU Dict |

---

## Cấu hình cổng

| Dịch vụ | Cổng | Giao thức | Phạm vi |
|---------|------|----------|----------|
| Frontend (dev) | 3000 | HTTP | localhost |
| FastAPI | 8000 | HTTP/WS | localhost (dev), Nginx (prod) |
| LiveKit | 7880 | WebRTC TCP | Public (UDP 50000-60000) |
| LiveKit WebSocket | 7881 | WSS | Public |
| MySQL | 3306 | MySQL TCP | localhost |
| SQLite (test) | — | File-based | — |
| Redis | 6379 | TCP | localhost |
| Minio API | 9000 | HTTP | localhost |
| Minio Console | 9001 | HTTP | localhost |
| coTURN | 3478, 5349 | UDP/TCP | Public |
| LLM (Gemma 4 E2B) | 8012 | HTTP | localhost (llama.cpp) |
| LLM (Qwen3 Embedding) | 8013 | HTTP | localhost (llama.cpp) |

---

## Biến môi trường

```bash
# === DATABASE ===
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/eroom

# === REDIS ===
REDIS_URL=redis://:password@localhost:6379/0

# === JWT ===
JWT_SECRET_KEY=your-secret-key-min-32-chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# === LIVEKIT ===
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret

# === MINIO (RAG Storage) ===
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=ERoom-rag-docs
MINIO_SECURE=False

# === AI ===
LLM_BASE_URL=http://localhost:8012/v1
LLM_MODEL=gemma-4-E2B-it
LLM_API_KEY=dev
EMBEDDING_BASE_URL=http://localhost:8013/v1
EMBEDDING_MODEL=Qwen3-Embedding-0.6B
BRAVE_SEARCH_API_KEY=BSA...

# === WEB SEARCH ===
BRAVE_SEARCH_API_KEY=BSA...

# === IMAGE MODERATION ===
NSFW_DETECTOR_ENABLED=true
NSFW_THRESHOLD=0.85

# === EMAIL ===
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=SG....
EMAIL_FROM=noreply@ERoom.app

# === STRIPE ===
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRO_PRICE_ID=price_...
STRIPE_PRO_PLUS_PRICE_ID=price_...

# === CORS ===
CORS_ORIGINS=http://localhost:3000,https://ERoom.app

# === APP ===
ENVIRONMENT=development
LOG_LEVEL=INFO
```

---

## Cấu trúc dự án

> [!info] Cấu trúc thực tế
> Cấu trúc dưới đây là thiết kế kiến trúc phân tầng. Cấu trúc code thực tế đã được refactor sang module-based, xem chi tiết tại **[[project-structure]]**.

### Backend — Kiến trúc phân tầng (thiết kế)
```
backend/app/
├── model/          # SQLModel entities (tương đương domain)
├── schemas/        # Pydantic DTOs (tương đương value_objects)
├── service/        # Business logic (tương đương application)
├── api/            # Routers + WebSocket (tương đương presentation)
├── infrastructure/ # LiveKit, Minio, Redis, Audio, Video
├── agent/          # AI Agent 3-trong-1 (langchain create_agent)
├── rag/            # RAG pipeline (langchain: chunking, embedding, retrieval)
└── utils/          # datetime_utils, file_handle, logging, retry, text, validation
```

### Frontend — Module-based (thực tế)
```
frontend/src/
├── features/       # Feature modules (auth, rooms, ai, tags, realtime, dashboard)
├── components/     # Shared components (ui, base, layout)
├── app/            # App shell, routing, auth context
├── api/            # HTTP client (Axios wrapper)
├── lib/            # api.js, websocket.js
├── hooks/          # Custom hooks
├── context/        # Theme context
└── styles/         # CSS
```

> [!tip] Xem chi tiết từng file
> Map đầy đủ file-to-file với giải thích: **[[project-structure]]**

---

## Các mẫu kiến trúc chính

### Kiến trúc phân tầng (Backend)
```
domain → application → infrastructure → presentation
```

### AI Agent 3-trong-1
```
                    ┌──────────────────┐
                    │   AI AGENT       │
                    │   (per room)     │
                    └────────┬─────────┘
           ┌─────────────────┼─────────────────┐
           ▼                 ▼                  ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │  CORRECTOR   │ │   EXPERT     │ │  HEARTBEAT   │
    │  Sửa lỗi +   │ │  RAG + Web   │ │  Khởi động   │
    │  TTS phát âm │ │  Search Q&A  │ │  hội thoại   │
    └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
           │                │                 │
           ▼                ▼                 ▼
    ┌──────────┐   ┌──────────────┐   ┌──────────────┐
    │ Whisper  │   │ Minio + Web  │   │ Audio Level  │
    │ + LLM    │   │ Search + LLM │   │ + LLM        │
    │ + TTS    │   │              │   │              │
    └──────────┘   └──────────────┘   └──────────────┘
```

### Thoái lui nhẹ nhàng
- Whisper sập → transcript ngừng, sửa lỗi ngừng, video call vẫn chạy
- LLM sập → sửa lỗi/expert/heartbeat tạm dừng, đánh giá cơ bản
- Minio sập → Expert dự phòng Web Search only
- TTS sập → Sửa lỗi vẫn hiện text, mất nút nghe phát âm
- Toàn bộ AI sập → Cuộc gọi video thuần + chat văn bản

---

## Gói Subscription

| Tính năng | Free | Pro ($9.99/tháng) | Pro+ ($19.99/tháng) |
|-----------|------|-------------------|---------------------|
| Số phòng / ngày | 2 | Không giới hạn | Không giới hạn |
| Tạo room | ❌ | ✅ | ✅ |
| Quota agent trong room | Cơ bản | Nâng cao (nếu room có ≥1 Pro) | Nâng cao + TTS + Note |
| Sửa lỗi AI | Giới hạn (3/phòng) | Đầy đủ | Đầy đủ + Phát âm |
| Heartbeat | 1/phòng | 3/phòng | 5/phòng |
| Expert Q&A (RAG) | ❌ | Web Search only | RAG + Web Search |
| TTS Phát âm chuẩn | ❌ | ❌ | ✅ |
| Auto Take Note | ❌ | ❌ | ✅ |
| Room Series | ❌ | ❌ | ✅ |
| Analytics nâng cao | ❌ | ❌ | ✅ |
| Leaderboard | ❌ | ❌ | ✅ |
| Mời guest vào room riêng | ❌ | ✅ | ✅ |
| Dùng thử | — | 7 ngày | 7 ngày |

---

## So sánh cạnh tranh

| Nền tảng | Ghép cặp | AI trong phòng | RAG Expert | TTS Phát âm | Anti-Misuse | Giá |
|----------|----------|---------------|------------|-------------|-------------|-----|
| **ERoom** | Theo Tag | ✅ 3-trong-1 | ✅ Minio+Web | ✅ | ✅ | Free/$9.99/$19.99 |
| Cambly | Gia sư | ❌ | ❌ | ❌ | ❌ | $10-15/giờ |
| Italki | Gia sư | ❌ | ❌ | ❌ | ❌ | $8-30/giờ |
| ELSA Speak | Một mình | Phát âm | ❌ | ✅ | ❌ | $11.99/tháng |
| Clubhouse | Chủ đề | ❌ | ❌ | ❌ | ❌ | Miễn phí |
| Duolingo | Một mình | Cơ bản | ❌ | ❌ | ❌ | Free/$6.99 |

---

## Trạng thái hiện tại

🟢 **Đang phát triển** — Backend đã implement gần đầy đủ (FastAPI + RAG + Pronunciation Pipeline). Frontend đang hoàn thiện UI components. Chi tiết: [[dev-notes]].

---

## 📁 Bản đồ file

| File | Vai trò |
|------|--------|
| [[features\|Tính năng]] | Đặc tả sản phẩm (30+ tính năng, P0-P3) |
| [[workflow\|Luồng hoạt động]] | UX + Thiết kế hệ thống (10+ luồng) |
| [[tasks\|Công việc]] | Kế hoạch kỹ thuật |
| [[notes\|Ghi chú kỹ thuật]] | Tham khảo kỹ thuật (DB, API, Redis, RAG) |
| [[decisions\|Quyết định kiến trúc]] | Cơ sở lý luận (20 ADR) |
| [[deployment\|Triển khai]] | Kế hoạch deploy, CI/CD, monitoring |
| [[project-structure\|Cấu trúc dự án]] | Map file-to-file thực tế |
| [[pronunciation-workflow\|Pronunciation Workflow]] | Luồng phát âm chi tiết |

