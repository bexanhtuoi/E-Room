---
title: ERoom — Công việc
tags:
  - tasks
  - project
  - ERoom
  - implementation
status: development
updated: 2026-06-02
---

# Danh sách Công việc Triển khai

> [!warning] Cập nhật 2026-06-02
> Database đã switch từ PostgreSQL + pgvector → **Local MySQL + TiDBRawVectorStore / NumpyVectorStore**. Các task dưới đây còn đề cập PostgreSQL/pgvector — cần cập nhật sau. Xem [[ERoom/decisions#ADR-021|ADR-021]] để biết chi tiết.

> [!abstract] Danh sách Tổng thể
> Mọi tác vụ để xây dựng ERoom thế hệ mới, tổ chức theo tầng: **Database → Tag System → API → Video → AI Engine → RAG/Minio → TTS → Moderation → Subscription → UI**. Mỗi checkbox là 1 đơn vị công việc nguyên tử.

> [!info] Điều hướng nhanh
> [[ERoom/overview|← Tổng quan]] · [[ERoom/features|← Tính năng]] · [[ERoom/workflow|← Luồng hoạt động]] · **Công việc** · [[ERoom/notes|Ghi chú kỹ thuật →]] · [[ERoom/decisions|Quyết định kiến trúc →]]

> [!tip] Tham khảo
> SQL schemas & API contracts → [[ERoom/notes|Ghi chú kỹ thuật]] | Tại sao chọn mỗi thứ → [[ERoom/decisions|Quyết định kiến trúc]] | AC tính năng → [[ERoom/features|Tính năng]] | Luồng người dùng → [[ERoom/workflow|Luồng hoạt động]]

---

## 📊 PHẦN 1 — DATABASE

### 1.1 Thiết lập PostgreSQL

- [ ] Cài đặt PostgreSQL 16+ với encoding UTF-8
- [ ] Tạo database `ERoom` và user `ERoom_app`
- [ ] Cấu hình PgBouncer connection pooling
- [ ] Cấu hình hiệu năng: `shared_buffers=256MB`, `effective_cache_size=1GB`
- [ ] Bật extensions: `uuid-ossp`, `pg_stat_statements`, `pgvector`
- [ ] Thiết lập sao lưu tự động `pg_dump` (3h sáng, giữ 30 ngày)
- [ ] Cấu hình WAL archiving
- [ ] Thiết lập read replica cho production

### 1.2 Alembic Migration Framework

- [ ] Cài đặt Alembic, khởi tạo `alembic init backend/migrations`
- [ ] Cấu hình `alembic.ini` với `DATABASE_URL`
- [ ] Quy ước đặt tên: `YYYY_MM_DD_HHMMSS_mô_tả.py`
- [ ] Thêm `alembic check` vào CI pipeline
- [ ] Viết script rollback cho revert khẩn cấp
- [ ] Seed migration: tạo tất cả bảng theo thứ tự phụ thuộc

### 1.3 Bảng Lõi

#### users
- [ ] Tạo bảng `users` (id, email, password_hash, display_name, avatar_url, english_level, career_field, job_title, learning_goal, auto_join_enabled, profile_completed, email_verified, is_active, is_banned, ban_reason, strikes, timestamps)
- [ ] Unique index LOWER(email), partial indexes cho active users

#### tags & user_tags
- [ ] Tạo bảng `tags` (id, name, slug, category, icon, is_custom, approved, usage_count)
- [ ] Tạo bảng `user_tags` (id, user_id, tag_id, UNIQUE(user_id, tag_id))
- [ ] Indexes: tags by category, user_tags by user_id + tag_id
- [ ] Pre-seed 50+ tags phổ biến trong migration data

#### refresh_tokens
- [ ] Tạo bảng `refresh_tokens` (id, user_id FK, token_hash, device_info, ip_address, expires_at, revoked)

#### rooms (cập nhật)
- [ ] Tạo bảng `rooms` với cột MỚI: tags TEXT[], primary_tag_id FK, agent_level, is_public
- [ ] Indexes: GIN on tags, partial indexes cho matching/active rooms

#### room_participants
- [ ] Tạo bảng `room_participants` (id, room_id FK, user_id FK, joined_at, left_at, speaking_time_seconds, words_spoken, is_muted, connection_quality)

#### sessions
- [ ] Tạo bảng `sessions` (id, room_id FK, user_id FK, topic, tags TEXT[], transcript, full_transcript JSONB, corrections JSONB, ai_review JSONB, scores, duration)
- [ ] GIN indexes trên corrections + ai_review

#### messages
- [ ] Tạo bảng `messages` với message_type MỚI: ai_expert, tts_audio
- [ ] Indexes: (room_id, created_at), partial index cho transcript

#### knowledge_documents (RAG)
- [ ] Tạo bảng `knowledge_documents` (id, tag_id FK, title, description, file_path, minio_key UNIQUE, file_type, file_size_bytes, chunk_count, embedding vector(1536), status, uploaded_by)
- [ ] Indexes: tag_id WHERE status='ready', status

#### knowledge_chunks (RAG)
- [ ] Tạo bảng `knowledge_chunks` (id, document_id FK, tag_id FK, content, chunk_index, embedding vector(1536), metadata JSONB)
- [ ] ivfflat index trên embedding với lists=100
- [ ] Unique constraint (document_id, chunk_index)

#### session_notes (Pro+)
- [ ] Tạo bảng `session_notes` (id, user_id FK, session_id FK, content TEXT, tags TEXT[], word_count)
- [ ] Indexes: (user_id, created_at DESC), session_id

#### room_series (Pro+)
- [ ] Tạo bảng `room_series` (id, title, description, creator_id FK, tag_id FK, total_sessions, schedule_cron, status)
- [ ] Indexes: creator_id, tag_id

#### leaderboard
- [ ] Tạo bảng `leaderboard` (id, user_id FK, tag_id FK, week_start, speaking_time, avg_score, sessions_count, rank)
- [ ] UNIQUE(user_id, tag_id, week_start), index (week_start DESC, tag_id, rank)

#### moderation_events
- [ ] Tạo bảng `moderation_events` (id, user_id FK, room_id FK, event_type, evidence_url, confidence, action, moderator_notes)
- [ ] Index: (user_id, created_at DESC)

#### agent_misuse_logs
- [ ] Tạo bảng `agent_misuse_logs` (id, user_id FK, room_id FK, query, intent, action)
- [ ] Index: (user_id, created_at DESC)

#### Bảng hỗ trợ
- [ ] `subscriptions` — tier MỚI: 'pro_plus'
- [ ] `topic_rooms` — thêm tag_id FK, series_id FK
- [ ] `topic_room_registrations`, `notifications`, `companies`, `company_members`

### 1.4 Hàm & Trigger

- [ ] `update_updated_at()` trigger cho users, subscriptions
- [ ] `increment/decrement_room_participants()` triggers
- [ ] `cleanup_expired_tokens()` qua pg_cron (hàng giờ)
- [ ] `auto_end_stale_rooms()` qua pg_cron (mỗi 5 phút)

### 1.5 Thiết lập Redis

- [ ] Cài đặt Redis 7+ với `maxmemory=256MB`, `allkeys-lru`
- [ ] Thiết lập Redis persistence (RDB + AOF)
- [ ] Định nghĩa keys MỚI:
  - `ERoom:queue:tag:{tag_slug}` — hàng đợi ghép cặp theo tag
  - `ERoom:correction:{room_id}:{user_id}` — quota sửa lỗi
  - `ERoom:expert:{room_id}` — quota expert
  - `ERoom:misuse:{room_id}:{user_id}` — misuse counter
  - `ERoom:cache:rag:{tag}:{hash}` — cache RAG query
  - `ERoom:cache:websearch:{hash}` — cache web search
  - `ERoom:cache:tts:{sha256}` — cache TTS audio
  - `ERoom:agent:{room_id}:rag_loaded` — cờ RAG đã nạp
  - `ERoom:lock:matching:tag:{tag_slug}` — lock ghép cặp theo tag
  - `ERoom:moderation:scan:{room_id}` — lock quét NSFW

### 1.6 Seed Dữ liệu

- [ ] Sinh 100 người dùng test với tags (A1-C2, đa dạng tags)
- [ ] Pre-seed 50+ tags phổ biến (Openclaw, Vibe Coding, Marketing, Physics, Math, DevOps, v.v.)
- [ ] Sinh 500 phiên đã hoàn thành với transcript + corrections
- [ ] Seed 20 phòng chủ đề mẫu
- [ ] Seed tài liệu RAG mẫu cho 5 tags phổ biến

---

## 🏷️ PHẦN 2 — TAG SYSTEM

### 2.1 Backend Tag Service

- [ ] Tạo `TagService` trong `application/services/tag.py`
- [ ] Triển khai `search_tags(query, limit)` — autocomplete debounce
- [ ] Triển khai `get_popular_tags(limit)` — theo usage_count
- [ ] Triển khai `suggest_tags(user_profile)` — gợi ý dựa trên career + job
- [ ] Triển khai `add_user_tags(user_id, tag_ids)` — bulk add
- [ ] Triển khai `remove_user_tag(user_id, tag_id)`
- [ ] Triển khai `create_custom_tag(name, category)` — is_custom=TRUE, approved=FALSE
- [ ] Triển khai `get_user_tags(user_id)`
- [ ] Celery task: `update_tag_usage_counts` — cập nhật usage_count định kỳ

### 2.2 Tag API Endpoints

- [ ] `GET /api/tags/popular` — danh sách tag phổ biến
- [ ] `GET /api/tags/search?q=vibe&limit=10` — tìm kiếm tag
- [ ] `POST /api/tags/custom` — tạo tag tùy chỉnh [Auth]
- [ ] `POST /api/tags/bulk-add` — thêm nhiều tag cho user [Auth]
- [ ] `GET /api/users/me/tags` — lấy tags của user [Auth]
- [ ] `DELETE /api/users/me/tags/{tag_id}` — xóa tag khỏi profile [Auth]
- [ ] `GET /api/tags/{tag_id}/rooms` — danh sách phòng đang hoạt động theo tag

### 2.3 Tag Matching Engine

- [ ] Cập nhật `MatchingService` để match theo tag similarity
- [ ] Triển khai Jaccard similarity: `|tags_A ∩ tags_B| / |tags_A ∪ tags_B|`
- [ ] Cập nhật công thức tương thích: `tag_jaccard * 0.6 + level_proximity * 0.25 + embedding_cosine * 0.15`
- [ ] Redis Sorted Set theo tag: `ERoom:queue:tag:{tag_slug}`
- [ ] Distributed lock theo tag: `ERoom:lock:matching:tag:{tag_slug}`
- [ ] Celery Beat: chạy matching engine mỗi 5s, quét từng tag queue

### 2.4 Frontend Tag UI

- [ ] Tạo `TagPicker` component — popup chọn tag khi đăng ký
- [ ] Tạo `TagCloud` — hiển thị tag dạng cloud/group theo category
- [ ] Tạo `TagBadge` — chip hiển thị tag với màu sắc theo category
- [ ] Tạo `TagSearch` — autocomplete input tìm kiếm tag
- [ ] Tạo `TagSuggestions` — gợi ý tag dựa trên job title
- [ ] Tích hợp TagPicker vào onboarding flow (Bước 2)
- [ ] Hiển thị tag trên video tile của người tham gia trong phòng
- [ ] Tạo `tag-store.ts` — Zustand store quản lý tags đã chọn

### 2.5 Tag Moderation

- [ ] Admin endpoint: `GET /api/admin/tags/pending` — tag tùy chỉnh chờ duyệt
- [ ] Admin endpoint: `PATCH /api/admin/tags/{id}/approve`
- [ ] Admin endpoint: `DELETE /api/admin/tags/{id}` — từ chối tag
- [ ] Tự động approve tag nếu được ≥ 3 users tạo giống nhau
- [ ] Merge tag trùng lặp: admin tool gộp 2 tags

---

## 🔌 PHẦN 3 — API (BACKEND)

### 3.1 Khởi tạo Dự án

- [ ] FastAPI app với `uv init --bare`
- [ ] Cấu trúc tầng: domain → application → infrastructure → presentation
- [ ] Cài đặt dependencies: fastapi, uvicorn[standard], pydantic-settings, sqlalchemy[asyncio], asyncpg, alembic, redis[hiredis], python-jose, passlib[bcrypt], httpx, minio, openai, sentence-transformers, langchain
- [ ] `app/config.py` với pydantic-settings
- [ ] `app/main.py` với FastAPI app factory + lifespan
- [ ] CORS middleware, structured logging (structlog)
- [ ] Health check `GET /health`, readiness `GET /ready`

### 3.2 Xác thực & Phân quyền

- [ ] Băm mật khẩu passlib bcrypt rounds=12
- [ ] JWT access token (15 phút) + refresh token (7 ngày, httpOnly)
- [ ] Xoay refresh token + Redis blacklist
- [ ] Auth dependencies: `get_current_user`, `get_current_active_user`, `require_subscription_tier(tier)`
- [ ] `POST /api/auth/register`, `/login`, `/refresh`, `/logout`
- [ ] `POST /api/auth/verify-email`, `/forgot-password`, `/reset-password`
- [ ] `GET /api/auth/me`, `PATCH /api/auth/me`
- [ ] Google + GitHub OAuth (Giai đoạn 2)

### 3.3 User Profile Endpoints

- [ ] `GET /api/users/{id}/profile`, `/stats`, `/sessions`
- [ ] `GET /api/users/{id}/sessions/{session_id}`
- [ ] `DELETE /api/users/{id}/sessions/{session_id}` (GDPR)
- [ ] `GET /api/users/{id}/progress`
- [ ] `POST /api/users/{id}/placement-test`

### 3.4 Room & Matching Endpoints (Cập nhật)

- [ ] `POST /api/rooms/match` — vào hàng đợi theo tag
- [ ] `DELETE /api/rooms/match` — rời hàng đợi
- [ ] `GET /api/rooms/match/status` — trạng thái hàng đợi
- [ ] `POST /api/rooms` — tạo room (Pro+ required)
- [ ] `GET /api/rooms` — liệt kê phòng, filter theo tag
- [ ] `GET /api/rooms/{id}` — chi tiết phòng
- [ ] `POST /api/rooms/{id}/join`, `/leave`, `/end`
- [ ] `POST /api/rooms/{id}/invite` — mời guest Free (Pro+)
- [ ] `GET /api/rooms/{id}/transcript`, `/messages`
- [ ] `GET /api/rooms/{id}/agent-status` — trạng thái agent (level, quota)

### 3.5 Subscription Endpoints

- [ ] `GET /api/subscriptions/me` — gói hiện tại
- [ ] `POST /api/subscriptions/create-checkout` — Stripe checkout
- [ ] `POST /api/subscriptions/webhook` — Stripe webhook handler
- [ ] `POST /api/subscriptions/cancel`, `/resume`
- [ ] `GET /api/subscriptions/invoices`

### 3.6 Session & Review Endpoints

- [ ] `GET /api/sessions/{id}/review` — đánh giá phiên
- [ ] `POST /api/sessions/{id}/review/regenerate`
- [ ] `POST /api/sessions/{id}/review/share`

### 3.7 WebSocket Server

- [ ] `WS /ws/{room_id}?token={jwt}` — auth on connect
- [ ] Định tuyến message theo `message_type`
- [ ] Sự kiện server → client MỚI:
  - `transcript_update` — hiển thị transcript NGAY LẬP TỨC
  - `ai_correction` — card sửa lỗi trong ChatWindow
  - `ai_expert_response` — câu trả lời Expert
  - `ai_heartbeat` — khởi động hội thoại
  - `tts_audio_ready` — audio URL sẵn sàng
  - `sensitive_content_alert` — cảnh báo NSFW
  - `agent_misuse_warning` — cảnh báo lạm dụng
  - `agent_level_changed` — thay đổi cấp agent
  - `note_ready` — note đã sẵn sàng (Pro+)
  - `request_video_frame` — server yêu cầu frame để scan
- [ ] Sự kiện client → server MỚI:
  - `ask_expert` — hỏi AI Expert
  - `request_tts` — yêu cầu phát âm TTS
  - `video_frame_capture` — gửi frame để NSFW scan
  - `report_agent_misuse` — báo cáo từ chối sai
- [ ] Heartbeat kết nối (ping mỗi 30s)

### 3.8 Celery Tasks

- [ ] `transcribe_audio_chunk` → text transcript
- [ ] `generate_ai_correction` → JSON sửa lỗi
- [ ] `generate_heartbeat_prompt` → câu hỏi khởi động
- [ ] `generate_session_review` → JSON đánh giá
- [ ] **MỚI:** `load_rag_knowledge(tag_ids, room_id)` → nạp RAG
- [ ] **MỚI:** `index_document(doc_id)` → index tài liệu vào pgvector
- [ ] **MỚI:** `query_expert_rag(query, tag_ids)` → RAG + Web Search
- [ ] **MỚI:** `generate_tts_audio(text, lang)` → audio URL
- [ ] **MỚI:** `scan_video_frame(frame, room_id, user_id)` → NSFW score
- [ ] **MỚI:** `classify_intent(query)` → intent label
- [ ] **MỚI:** `generate_session_note(session_id, user_id)` → markdown note (Pro+)
- [ ] **MỚI:** `update_leaderboard()` → tính bảng xếp hạng hàng tuần
- [ ] `run_matching_engine` — cập nhật cho tag-based matching
- [ ] `cleanup_expired_rooms`, `cleanup_expired_tokens`
- [ ] Celery Beat schedule: matching 5s, cleanup 5phút, leaderboard CN 23:59

### 3.9 Kiểm thử API

- [ ] pytest + pytest-asyncio + httpx.AsyncClient
- [ ] Integration tests cho tất cả endpoint (auth, tags, rooms, sessions, subscriptions)
- [ ] Integration tests cho WebSocket events mới
- [ ] Mock tests cho RAG, TTS, NSFW, Web Search
- [ ] > 85% test coverage

---

## 🎥 PHẦN 4 — LIVEKIT VIDEO SERVER

- [ ] Cài đặt LiveKit Server qua Docker
- [ ] Cấu hình `livekit.yaml` (ports, TURN, keys, Redis)
- [ ] Thiết lập coTURN server cho NAT traversal
- [ ] Cài đặt LiveKit Python SDK + `@livekit/components-react`
- [ ] Tạo `LiveKitService` trong `infrastructure/livekit.py`
- [ ] Tạo token với claims: room, participant, permissions
- [ ] WebHook handler: room_started, participant_joined, room_finished
- [ ] Tích hợp LiveKit client trong React (client-side only)
- [ ] LiveKit multi-node scaling với Redis (production)

---

## 🧠 PHẦN 5 — AI ENGINE

### 5.1 FunASR (STT)

- [ ] Thiết lập FunASR SenseVoiceSmall model
   - [ ] Config: `FUNASR_MODEL_PATH`
- [ ] Giai đoạn 2: tối ưu FunASR model

### 5.2 LLM Integration

- [ ] `LLMService` trong `infrastructure/llm.py`
- [ ] GPT-4o cho: Corrector + Expert RAG + Review + Note
- [ ] GPT-4o-mini cho: Heartbeat + Intent Classifier
- [ ] Cache phản hồi: Redis 1h (correction), 24h (topics)
- [ ] Fallback chain: primary → retry → fallback → graceful degradation

### 5.3 Corrector Prompt Engineering

- [ ] System prompt: huấn luyện viên tiếng Anh, nhận biết trình độ + tag context
- [ ] JSON schema: `{has_errors, corrections: [{original, corrected, explanation, type, severity}]}`
- [ ] Few-shot examples: 20 cặp prompt-response
- [ ] Ngưỡng severity: chỉ hiện moderate + major
- [ ] Loại bỏ trùng lặp: fuzzy match Levenshtein > 0.8

### 5.4 Heartbeat Prompt Engineering

- [ ] System prompt: điều phối viên thân thiện + tag context
- [ ] Nhắm mục tiêu: ưu tiên người im lặng nhất
- [ ] Quản trị: max quota theo agent_level, min 2 phút giữa các lần
- [ ] Prompt templates theo tag (Software, Marketing, Finance, Healthcare, Education, Default)

### 5.5 Review & Note Prompt Engineering

- [ ] System prompt đánh giá phiên: transcript + corrections → JSON review
- [ ] System prompt take note (Pro+): transcript + corrections → markdown note
- [ ] Schema xác thực: scores 0-10, min 1 top mistake, min 1 strength + improvement

### 5.6 Vector Embeddings

- [ ] SentenceTransformer `all-MiniLM-L6-v2` (384-dim) — CHỈ dùng để embed tài liệu RAG
- [ ] Celery task: `index_document(doc_id)` — embed document chunks → pgvector
- [ ] Giai đoạn 2: nâng cấp `all-mpnet-base-v2` (768-dim)

### 5.7 Intent Classifier (Anti-Misuse)

- [ ] Prompt: phân loại intent → english_practice | code_request | personal_task | unrelated | unsure
- [ ] Celery task chạy GPT-4o-mini (timeout 2s)
- [ ] Guardrail system prompt prepend vào mọi prompt của Agent
- [ ] Redis counter `ERoom:misuse:{room_id}:{user_id}` (TTL phiên)
- [ ] ≥ 3 từ chối/phiên → auto-flag moderator

---

## 📦 PHẦN 6 — MINIO & RAG SETUP

### 6.1 Minio Setup

- [ ] Cài đặt Minio Server qua Docker
- [ ] Tạo buckets: `ERoom-rag-docs`, `ERoom-tts`, `ERoom-avatars`, `ERoom-evidence`
- [ ] Cấu hình bucket policies: private, presigned URLs
- [ ] TTL rules: `ERoom-tts` expire sau 24h, `ERoom-evidence` sau 30 ngày
- [ ] Cài đặt `minio` Python client trong backend

### 6.2 RAG Document Management

- [ ] `MinioService` trong `infrastructure/minio.py`
- [ ] Upload document: `POST /api/knowledge/documents` (Admin only)
- [ ] Parse file: PyPDF2 (PDF), markdown parser (MD), text (TXT)
- [ ] Chunk text: 500 ký tự, overlap 50
- [ ] Embed chunks: `text-embedding-3-small` (1536-dim)
- [ ] Lưu vào `knowledge_chunks` với pgvector ivfflat index
- [ ] Document status flow: pending → indexing → ready | failed

### 6.3 RAG Query Pipeline

- [ ] Embed query → pgvector cosine search → top-5 chunks
- [ ] Song song: Brave Search API → top-3 results
- [ ] Combine context → LLM answer
- [ ] Cache: Redis `ERoom:cache:rag:{tag}:{query_hash}` TTL 1h
- [ ] Celery task: `query_expert_rag(query, tag_ids, room_id)`

### 6.4 Agent Knowledge Loading

- [ ] Celery task: `load_rag_knowledge(tag_ids, room_id)` — chạy khi phòng được tạo
- [ ] Load documents từ Minio theo tag
- [ ] Pre-embed và cache kết quả web search cho các keywords phổ biến
- [ ] Xây dựng system prompt agent với tag context
- [ ] Thời gian nạp: < 5s (basic), < 15s (advanced/full)

---

## 🔊 PHẦN 7 — TTS INTEGRATION

### 7.1 TTS Engine Setup

- [ ] Thiết lập Supertonic ONNX model local
- [ ] `TTSService` trong `application/services/tts.py`
- [ ] `POST /api/tts/generate` — text → audio [Pro+ only]
- [ ] Audio lưu vào Minio `ERoom-tts/{sha256}.mp3` (TTL 24h)
- [ ] Cache URL trong Redis: `ERoom:cache:tts:{sha256}` TTL 24h

### 7.2 TTS Frontend

- [ ] Nút 🔊 "Nghe phát âm chuẩn" trên mỗi card sửa lỗi AI
- [ ] howler.js để streaming audio playback
- [ ] Waveform animation khi đang phát
- [ ] Trạng thái loading khi đang generate
- [ ] Chỉ hiển thị nút TTS nếu user là Pro+
- [ ] Rate limit: 10 TTS requests/user/phiên

### 7.3 TTS Fallback

- [ ] Nếu TTS engine sập → ẩn nút TTS, vẫn hiện text sửa lỗi
- [ ] Nếu Minio sập → trả audio base64 trực tiếp (max 1MB)
- [ ] Đánh giá Supertonic model cho tiếng Việt

---

## 🛡️ PHẦN 8 — IMAGE MODERATION

### 8.1 NSFW Detector Setup

- [ ] Cài đặt `nsfw_detector` model (TensorFlow/Keras)
- [ ] `NSFWDetector` class trong `infrastructure/nsfw_detector.py`
- [ ] Phương thức `predict(image_bytes) → {score, is_nsfw}`
- [ ] Ngưỡng: confidence > 0.85 → gắn cờ
- [ ] Google Vision SafeSearch API làm fallback

### 8.2 Moderation Pipeline

- [ ] Celery Beat: `moderation_scan` mỗi 30s cho mỗi phòng ACTIVE
- [ ] WebSocket: server gửi `request_video_frame` → client gửi `video_frame_capture` (JPEG 320x240)
- [ ] Gọi NSFW detector → nếu NSFW → áp dụng 3-strike policy
- [ ] Lần 1: warning + video_off
- [ ] Lần 2: video_off + INSERT strike
- [ ] Lần 3: ban 24h + notify admin
- [ ] Lưu evidence vào Minio `ERoom-evidence`

### 8.3 Moderation UI

- [ ] `SensitiveContentAlert` component trong ChatWindow
- [ ] Warning message: "⚠️ Video của {tên} đã bị tắt do phát hiện nội dung không phù hợp"
- [ ] Admin dashboard: moderation queue với evidence ảnh

---

## 💰 PHẦN 9 — SUBSCRIPTION SYSTEM

### 9.1 Stripe Integration

- [ ] Thiết lập Stripe account + webhook endpoint
- [ ] Tạo products/prices: Pro ($9.99/tháng), Pro+ ($19.99/tháng)
- [ ] Stripe Checkout session creation
- [ ] Webhook handler: checkout.session.completed, subscription.updated, subscription.deleted
- [ ] Bảng `subscriptions` với tier MỚI: 'pro_plus'
- [ ] Trial 7 ngày cho cả Pro và Pro+

### 9.2 Quota Enforcement

- [ ] Middleware `require_subscription_tier(tier)` cho API endpoints
- [ ] `get_room_agent_level(room_id)` — quét tier của tất cả participants
- [ ] Redis counters cho từng loại quota trong phòng
- [ ] Enforcement: từ chối nếu vượt quota + thông báo nâng cấp

### 9.3 Auto Note-Taking (Pro+)

- [ ] Celery task: `generate_session_note(session_id, user_id)` — chỉ Pro+
- [ ] Prompt LLM: tạo markdown note từ transcript + corrections
- [ ] Lưu vào `session_notes`
- [ ] WebSocket: `note_ready` event
- [ ] `GET /api/sessions/{id}/note` — lấy note
- [ ] `GET /api/users/me/notes` — danh sách notes, filter theo tag

### 9.4 Room Series (Pro+)

- [ ] `POST /api/series` — tạo series [Pro+]
- [ ] Tự động tạo `topic_rooms` theo lịch trong series
- [ ] `GET /api/series?tag=devops` — danh sách series
- [ ] Đăng ký toàn bộ series (thay vì từng buổi)

### 9.5 Leaderboard (Pro+)

- [ ] Bảng `leaderboard` với partition theo tuần + tag
- [ ] Celery Beat: tính toán mỗi CN 23:59
- [ ] `GET /api/leaderboard?tag=vibe-coding&week=2026-05-04`
- [ ] Huy hiệu thành tích hiển thị trên profile

### 9.6 Subscription UI

- [ ] `UpgradePrompt` component — hiển thị khi Free user gặp giới hạn
- [ ] `QuotaIndicator` — hiển thị quota còn lại trong phòng
- [ ] `SubscriptionPage` — so sánh gói, nút nâng cấp
- [ ] `BillingPage` — lịch sử hóa đơn, hủy gói

---

## 🎨 PHẦN 10 — UI (FRONTEND)

### 10.1 Thiết lập Dự án

- [ ] React 18+ + Vite 5+, TailwindCSS, shadcn/ui
- [ ] Zustand stores: auth-store, room-store, tag-store, subscription-store, agent-store
- [ ] @tanstack/react-query với QueryClientProvider
- [ ] i18next + react-i18next cho i18n (en + vi)
- [ ] `lib/api.ts` — HTTP client với JWT interceptor
- [ ] `lib/websocket.ts` — WebSocket client với auto-reconnect
- [ ] `lib/livekit.ts`, `lib/tts.ts`
- [ ] `lib/types.ts` — TypeScript types dùng chung

### 10.2 Layout & Auth Pages

- [ ] Root layout, landing page, navbar, footer
- [ ] AuthGuard, OnboardingGuard (kiểm tra tags)
- [ ] Login, Register, Forgot Password, Verify Email pages
- [ ] OAuth callback cho Google + GitHub (Giai đoạn 2)

### 10.3 Trình khởi tạo với Tag

- [ ] `app/onboarding/page.tsx` — container 5 bước
- [ ] StepEnglishLevel, **StepTagPicker**, StepJobTitle, StepLearningGoal, StepConfirm
- [ ] `TagPicker` component full-screen với tag cloud + search + custom tag
- [ ] Xác thực bước: không thể skip bước chọn tag
- [ ] Lưu tiến độ một phần vào localStorage

### 10.4 Bảng điều khiển

- [ ] Dashboard với StatsCard, WeeklyChart, SkillRadar
- [ ] StreakTracker, RecentSessions, UpcomingTopics
- [ ] **MỚI:** QuotaIndicator — hiển thị gói hiện tại + quota còn lại
- [ ] **MỚI:** UpgradePrompt — CTA nâng cấp cho Free user

### 10.5 UI Ghép cặp

- [ ] QueueOverlay với tag display + animation
- [ ] QueueStatus — "Đang tìm bạn cùng tag {tag}..."
- [ ] MatchFoundCard — hiển thị tags chung của người tham gia
- [ ] FallbackOffer, AIRoomOffer

### 10.6 UI Phòng (ChatWindow Tích hợp)

- [ ] `app/(dashboard)/room/[id]/page.tsx`
- [ ] RoomLayout: video grid (chính) + ChatWindow (sidebar)
- [ ] RoomHeader: topic, tags badge, đồng hồ, agent_level indicator
- [ ] **ChatWindow (trọng tâm):**
  - [ ] TranscriptPanel — hiển thị transcript NGAY LẬP TỨC (xám = tạm thời, trắng = cuối cùng)
  - [ ] CorrectionCard — text gốc (gạch đỏ) → text sửa (xanh) + giải thích + nút 🔊 TTS
  - [ ] ExpertResponse — câu trả lời với badge "🧠 Expert" + nguồn tham khảo
  - [ ] HeartbeatMessage — tin nhắn AI với avatar robot
  - [ ] TTSPlayer — nút play/pause + waveform animation
  - [ ] TextChat — tin nhắn văn bản thường + emoji reactions
- [ ] RoomControls: mic, video, chat toggle
- [ ] SessionEndOverlay, ReconnectingOverlay

### 10.7 Trang Session & Notes

- [ ] `app/(dashboard)/sessions/` — lịch sử phiên với infinite scroll
- [ ] `app/(dashboard)/sessions/[id]/` — đánh giá + transcript
- [ ] **MỚI:** `app/(dashboard)/notes/` — danh sách notes (Pro+)
- [ ] NoteViewer — render markdown với syntax highlighting
- [ ] Export note ra PDF/Markdown

### 10.8 Trang Series & Leaderboard (Pro+)

- [ ] `app/(dashboard)/series/` — danh sách series
- [ ] `app/(dashboard)/series/[id]/` — chi tiết series + đăng ký
- [ ] `app/(dashboard)/leaderboard/` — bảng xếp hạng theo tag + tuần
- [ ] Badge huy hiệu thành tích trên profile

### 10.9 Trang Subscription

- [ ] `app/(dashboard)/settings/billing/` — so sánh gói, nút nâng cấp
- [ ] `UpgradePrompt` popup khi Free user gặp giới hạn
- [ ] `QuotaIndicator` trong phòng: hiển thị quota agent còn lại
- [ ] Xác nhận hủy gói + lý do (feedback collection)

### 10.10 Moderation UI

- [ ] `SensitiveContentAlert` — cảnh báo NSFW trong ChatWindow
- [ ] `MisuseWarning` — cảnh báo lạm dụng agent
- [ ] Nút "Báo cáo" trong phòng (cờ)
- [ ] Admin dashboard: moderation queue (Giai đoạn 2)

### 10.11 Responsive & Performance

- [ ] Responsive: mobile (375px), tablet (768px), desktop (1024px+)
- [ ] Cross-browser: Chrome 120+, Firefox 120+, Safari 17+, Edge 120+
- [ ] Bundle size < 200KB JS initial (gzipped)
- [ ] Lazy load: room components, charts, TTS player
- [ ] Virtual scrolling cho transcript dài (react-virtuoso)
- [ ] WebSocket message batching: 100ms window

---

## 📊 Tổng kết Số lượng Tác vụ

| Phần | Mô tả | Số tác vụ |
|------|------|-----------|
| 1. DATABASE | PostgreSQL + Alembic + Bảng (17 bảng) + Redis | ~130 |
| 2. TAG SYSTEM | Backend + API + Matching + Frontend + Moderation | ~45 |
| 3. API | FastAPI + Auth + Endpoints (80+) + WebSocket + Celery | ~140 |
| 4. VIDEO SERVER | LiveKit setup + integration + scaling | ~35 |
| 5. AI ENGINE | FunASR + LLM + Prompts + Embeddings + Intent Classifier | ~65 |
| 6. MINIO & RAG | Setup + Documents + Query Pipeline + Agent Loading | ~30 |
| 7. TTS | Engine + Frontend + Fallback | ~15 |
| 8. IMAGE MODERATION | NSFW Detector + Pipeline + UI | ~20 |
| 9. SUBSCRIPTION | Stripe + Quota + Note + Series + Leaderboard + UI | ~45 |
| 10. UI | Setup + Auth + Onboarding + Dashboard + Room + Sessions + Notes + Series + Leaderboard + Subscription + Moderation + Responsive | ~150 |
| **TỔNG** | | **~675** |

---

## Thứ tự Triển khai

```
Giai đoạn 1 (MVP — ~350 tác vụ):
  DATABASE → TAG SYSTEM → API (Auth + Matching + Room + WebSocket cơ bản)
  → LIVEKIT → AI ENGINE (FunASR + Corrector + Review + Embeddings)
  → UI (Setup + Auth + Onboarding với Tag + Dashboard + Matching + Room cơ bản)

Giai đoạn 2 (AI Agent — ~200 tác vụ):
  MINIO & RAG → AI ENGINE (Expert RAG + Heartbeat + Intent Classifier)
  → MODERATION (NSFW + Anti-Misuse) → API (WebSocket events đầy đủ)
  → UI (ChatWindow đầy đủ: Expert + Heartbeat + CorrectionCard + Moderation alerts)

Giai đoạn 3 (Kiếm tiền — ~125 tác vụ):
  SUBSCRIPTION (Stripe + Quota + Note + Series + Leaderboard)
  → TTS → UI (Notes + Series + Leaderboard + Subscription pages)
```

---

## Liên quan

- [[ERoom/notes|Ghi chú kỹ thuật]] — SQL DDL, API contracts, Redis keys, RAG pipeline (tham khảo khi triển khai)
- [[ERoom/decisions|Quyết định kiến trúc]] — 16 ADR giải thích cơ sở kiến trúc
- [[ERoom/features|Tính năng]] — 26 đặc tả tính năng với AC
- [[ERoom/workflow|Luồng hoạt động]] — 10+ luồng với mục tiêu hiệu năng
- [[ERoom/overview|Tổng quan]] — Sơ đồ kiến trúc & cấu hình
