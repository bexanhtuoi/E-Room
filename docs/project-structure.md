---
title: ERoom — Cấu trúc Dự án (Thực tế)
tags:
  - structure
  - reference
  - ERoom
  - codebase
created: 2026-05-10
updated: 2026-06-02
---

# Cấu trúc Dự án (Thực tế)

> [!abstract] Map file-to-file của codebase ERoom hiện tại
> Cập nhật 2026-06-02 dựa trên code thực tế. Cấu trúc phản ánh codebase thật tại `C:\Users\PC\Downloads\E-Room`.

> [!info] Điều hướng nhanh
> [[ERoom/overview|← Tổng quan]] · [[ERoom/deployment|Triển khai →]] · [[ERoom/dev-notes|Dev Notes →]]

---

## 1. Backend (`backend/`)

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                       # FastAPI app factory, lifespan, CORS, WS routes
│   ├── config.py                     # pydantic-settings (TiDB, Redis, LLM, LiveKit...)
│   ├── database.py                   # SQLModel engine (MySQL / SQLite cho test)
│   ├── security.py                   # Argon2 hashing + JWT (access/refresh)
│   ├── server.py                     # uvicorn runner
│   ├── log.py                        # Structured logging (console + file)
│   │
│   ├── agent/                        # AI Agent (langchain + local LLM)
│   │   ├── __init__.py               # Exports: correct_text, answer_expert, generate_heartbeat
│   │   ├── base.py                   # call_llm_json(), call_llm_text()
│   │   ├── corrector.py              # Pronunciation correction + LLM
│   │   ├── expert.py                 # RAG + Brave Search + LLM Q&A
│   │   ├── heartbeat.py              # Heartbeat question generator
│   │   ├── llm.py                    # get_llm() - ChatOpenAI (LM Studio endpoint)
│   │   ├── prompt.py                 # System prompt templates (3 roles)
│   │   └── query.py                  # Query router + intent classifier + misuse detection
│   │
│   ├── api/                          # Presentation layer
│   │   ├── __init__.py               # 12 routers registered under /api/v1
│   │   ├── dependencies.py           # Auth chain, ban check, DB session
│   │   └── routers/
│   │       ├── auth.py               # POST register, login, refresh, logout, PATCH me
│   │       ├── conversation.py       # Session history
│   │       ├── health.py             # GET /health
│   │       ├── infra.py              # Rate limit dependency
│   │       ├── leaderboard.py        # Leaderboard CRUD
│   │       ├── message.py            # Message CRUD
│   │       ├── notes.py              # Session notes
│   │       ├── notification.py       # Notifications
│   │       ├── room.py               # Room CRUD + match + join/leave + LiveKit token
│   │       ├── series.py             # Room series
│   │       ├── subscription.py       # Subscriptions
│   │       ├── tag.py                # Tag CRUD + search + popular
│   │       ├── user.py               # User profile
│   │       └── websocket_routes.py   # WS route definitions (mounted in main.py)
│   │
│   ├── ws/                           # WebSocket handlers (riêng)
│   │   ├── __init__.py
│   │   ├── auth.py                   # WS JWT authentication
│   │   ├── handlers.py               # handle_room_ws + handle_audio_ws
│   │   ├── messages.py               # save_message + generate_expert_reply
│   │   └── speech.py                 # process_speech (PronunciationPipeline + LLM)
│   │
│   ├── seed/                         # Database seeding
│   │   ├── __init__.py
│   │   ├── seed_data.py              # 10 seed rooms
│   │   └── tag_seed.py               # 53 default tags (5 categories)
│   │
│   ├── model/                        # SQLModel entities
│   │   ├── __init__.py               # Re-export all models
│   │   ├── common.py                 # TimestampedModel mixin
│   │   ├── user.py                   # User (strikes, ban, english_level, profile)
│   │   ├── tag.py                    # Tag + UserTag (many-to-many)
│   │   ├── room.py                   # Room + RoomParticipant + RoomStatus enum
│   │   ├── conversation.py           # Session (per-user per-room)
│   │   ├── message.py                # Message (transcript, correction, expert...)
│   │   ├── auth.py                   # RefreshToken
│   │   ├── document.py               # KnowledgeDocument + KnowledgeChunk
│   │   ├── subscription.py           # Subscription (tier, stripe)
│   │   ├── series.py                 # RoomSeries + TopicRoom
│   │   ├── notification.py           # Notification
│   │   ├── moderation.py             # ModerationEvent + AgentMisuseLog
│   │   └── series.py                 # LeaderboardEntry
│   │
│   ├── schemas/                      # Pydantic request/response
│   │   ├── __init__.py
│   │   ├── auth.py                   # AuthTokenResponse, LoginRequest, RegisterRequest
│   │   ├── common.py                 # Pagination, shared DTOs
│   │   ├── room.py                   # RoomCreateRequest, RoomResponse, RoomMatchRequest...
│   │   ├── tag.py                    # TagResponse, TagBulkAddRequest
│   │   ├── conversation.py           # Session DTOs
│   │   ├── message.py                # Message DTOs
│   │   ├── user.py                   # UserProfile, UserUpdate
│   │   ├── agent.py                  # Agent request/response
│   │   ├── subscription.py           # Subscription DTOs
│   │   └── series.py                 # Series DTOs
│   │
│   ├── service/                      # Business logic
│   │   ├── __init__.py
│   │   ├── base.py                   # CRUDRepository (get_one, get_many, create, update, delete)
│   │   ├── auth.py                   # AuthService (register, authenticate, tokens)
│   │   ├── room.py                   # RoomService + RoomParticipantService
│   │   ├── tag.py                    # TagService + UserTagService
│   │   ├── user.py                   # UserService
│   │   ├── conversation.py           # SessionService
│   │   ├── message.py                # MessageService
│   │   ├── subscription.py           # SubscriptionService
│   │   ├── series.py                 # SeriesService
│   │   ├── notification.py           # NotificationService
│   │   ├── heartbeat.py              # Asyncio heartbeat loop
│   │   ├── room_state.py             # Room state management
│   │   ├── token_store.py            # JWT blacklist (Redis)
│   │   └── model_warmup.py           # Model warmup on startup
│   │
│   ├── rag/                          # RAG pipeline (langchain)
│   │   ├── __init__.py               # Exports all components
│   │   ├── chunking.py               # TextChunker (RecursiveCharacterTextSplitter)
│   │   ├── embedding.py              # EmbeddingService (Nomic 768-dim + cache)
│   │   ├── file_handle.py            # File parsing (PDF, MD, TXT)
│   │   ├── retrieval.py              # RetrievalService (vector + keyword hybrid)
│   │   └── vector_store.py           # TiDBRawVectorStore + NumpyVectorStore fallback
│   │
│   ├── infrastructure/               # External services & core pipelines
│   │   ├── __init__.py               # Exports all singletons
│   │   ├── audio.py                  # AudioConfig, AudioBuffer, AudioBufferManager
│   │   ├── audio_whisper.py          # faster-whisper small.en (CUDA float16)
│   │   ├── audio_pipeline.py         # PronunciationPipeline (Whisper + CMU + scoring)
│   │   ├── audio_dictionary.py       # CMU Dictionary (ARPAbet lookup from cmudict.json)
│   │   ├── pronunciation_audio.py    # gTTS pronunciation audio generation
│   │   ├── event_bus.py              # EventBus (Redis pub/sub)
│   │   ├── livekit.py                # LiveKitService (token, admin, webhook)
│   │   ├── minio.py                  # MinioCRUD (S3-compatible object storage)
│   │   ├── redis_client.py           # RedisCRUD + RateLimiter
│   │   ├── video.py                  # VideoRoomService
│   │
│   └── utils/                        # Utility functions
│       ├── __init__.py
│       ├── datetime_utils.py         # now_utc(), format_iso(), parse_duration()
│       ├── file_handle.py            # safe_read(), get_extension(), validate_file_size()
│       ├── retry.py                  # retry_on_failure decorator
│       ├── text.py                   # truncate(), sanitize_html(), slugify()
│       └── validation.py             # is_valid_email(), sanitize_input()
│
├── alembic/                          # Alembic migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       ├── 7a41f215585b_add_pgvector_extension_and_vector_.py
│       └── 9344b2bf093f_initial_all_eroom_tables.py
│
├── tests/                            # Test suite
│   ├── conftest.py                   # Shared fixtures (SQLite engine, client, auth)
│   ├── test_edge_cases.py            # Unicode, XSS, SQL injection
│   ├── test_infrastructure.py        # Infrastructure tests
│   ├── test_minio.py                 # MinIO operations tests
│   ├── test_real_speech.py           # Real speech pipeline tests
│   ├── test_redis.py                 # Redis operations tests
│   ├── test_token_store.py           # JWT blacklist tests
│   ├── test_websocket.py             # WebSocket tests
│   ├── test_integration/
│   │   ├── test_api_health.py        # Health checks (6 pass)
│   │   ├── test_auth_api.py          # Auth flow (15 pass)
│   │   ├── test_matching_pipeline.py # Matching flow (10 pass)
│   │   └── test_room_api.py          # Room CRUD (12 pass)
│   └── test_unit/
│       ├── test_agent.py             # Corrector, Expert, Heartbeat
│       ├── test_audio_pipeline.py    # Audio processing
│       ├── test_core.py              # Core RAG imports
│       ├── test_matching.py          # Matching engine
│       ├── test_models.py            # SQLModel entities
│       ├── test_rag.py               # Chunking, embedding, retrieval
│       └── test_security.py          # Auth, rate limiting
│
├── .env                              # Dev environment (git-ignored)
├── .env.docker                       # Docker environment
├── .env.example                      # Template
├── .python-version                   # Python 3.13
├── pyproject.toml                    # Dependencies (uv, Python 3.13+)
├── uv.lock                           # Lock file
├── Dockerfile                        # Backend container
├── README.md
└── TODO.md
```

---

## 2. Frontend (`frontend/`)

```
frontend/
├── src/
│   ├── main.jsx                      # Entry point (React 19, QueryClient, Theme, i18n)
│   ├── App.test.jsx                  # Basic app test
│   │
│   ├── api/                          # HTTP client
│   │   ├── client.js                 # ApiClient (fetch wrapper, auto-refresh 401)
│   │   └── index.js                  # Re-export
│   │
│   ├── app/                          # App shell
│   │   ├── App.jsx                   # Router config (public + protected + lazy routes)
│   │   ├── AppShell.jsx              # Layout (navbar, footer, theme toggle, i18n)
│   │   ├── AuthContext.jsx           # Auth state + login/register/logout
│   │   ├── AuthGuard.jsx             # Route guard (redirect if unauthenticated)
│   │   ├── OnboardingGuard.jsx       # Onboarding completion guard
│   │   └── pages/
│   │       ├── HomePage.jsx          # Landing page
│   │       ├── LearningPage.jsx      # Learning dashboard
│   │       ├── ProfilePage.jsx       # User profile
│   │       ├── PaymentPage.jsx       # Subscription checkout
│   │       ├── PricingPage.jsx       # Pricing comparison
│   │       ├── BlogPage.jsx          # Blog listing
│   │       ├── BlogDetailPage.jsx    # Blog post detail
│   │       └── ContactPage.jsx       # Contact form
│   │
│   ├── features/                     # Feature modules
│   │   ├── ai/
│   │   │   └── AIAssistantScaffold.js
│   │   ├── auth/
│   │   │   ├── AuthPanel.jsx
│   │   │   └── LoginPage.jsx
│   │   ├── chat/                     # ChatWindow components
│   │   │   ├── ChatTranscript.jsx
│   │   │   ├── ChatWindow.jsx
│   │   │   ├── CorrectionCard.jsx
│   │   │   ├── ExpertResponse.jsx
│   │   │   ├── HeartbeatMessage.jsx
│   │   │   ├── MatchFoundCard.jsx
│   │   │   ├── QueueOverlay.jsx
│   │   │   ├── TTSPlayer.jsx
│   │   │   └── useChatState.js
│   │   ├── dashboard/
│   │   ├── leaderboard/
│   │   ├── notes/
│   │   ├── onboarding/               # 5-step wizard
│   │   │   ├── OnboardingWizard.jsx
│   │   │   ├── StepConfirm.jsx
│   │   │   ├── StepEnglishLevel.jsx
│   │   │   ├── StepJobTitle.jsx
│   │   │   ├── StepLearningGoal.jsx
│   │   │   └── StepTagPicker.jsx
│   │   ├── realtime/
│   │   │   └── RealtimeRoomPanel.jsx
│   │   ├── rooms/
│   │   │   ├── CreateRoomModal.jsx
│   │   │   ├── RoomDetail.jsx
│   │   │   ├── RoomList.jsx
│   │   │   ├── RoomPage.jsx
│   │   │   └── RoomSocketPreview.jsx
│   │   ├── series/
│   │   ├── sessions/
│   │   ├── subscription/
│   │   └── tags/
│   │       └── TagPanel.jsx
│   │
│   ├── components/                   # Shared components
│   │   ├── base/
│   │   │   ├── hooks.js
│   │   │   └── index.js
│   │   ├── layout/
│   │   ├── tags/
│   │   └── ui/
│   │       ├── Avatar.jsx
│   │       ├── Badge.jsx
│   │       ├── ChatBox.jsx
│   │       ├── EmptyState.jsx
│   │       ├── RoomCard.jsx
│   │       ├── Skeleton.jsx
│   │       ├── ThemeToggle.jsx
│   │       └── Toast.jsx
│   │
│   ├── stores/                       # Zustand stores
│   │   ├── roomStore.js
│   │   ├── authStore.js
│   │   ├── tagStore.js
│   │   ├── agentStore.js
│   │   └── subscriptionStore.js
│   │
│   ├── hooks/
│   │   └── useAsyncResource.js
│   │
│   ├── lib/
│   │   ├── api.js                    # API helpers
│   │   ├── websocket.js              # RoomSocket (auto-reconnect + exponential backoff)
│   │   ├── audioCapture.js           # Audio capture
│   │   ├── constants.js              # App constants
│   │   ├── formatters.js             # Format helpers
│   │   ├── queryClient.js            # TanStack Query config
│   │   └── styles.js                 # Shared styles
│   │
│   ├── context/
│   │   └── ThemeContext.jsx           # Dark/light theme
│   │
│   ├── i18n/                         # Internationalization
│   │   ├── index.js
│   │   ├── locales/
│   │   │   ├── en.json
│   │   │   └── vi.json
│   │
│   ├── styles/
│   │   └── theme.css                 # CSS variables
│   │
│   └── __mocks__/                    # Vitest mocks
│       ├── @livekit/
│       │   ├── components-react.js
│       │   └── components-styles.js
│       ├── livekit-client.js
│       └── react-router-dom.js
│
├── public/
├── build/
├── package.json                      # React 19, Vite 6, Bootstrap 5, Zustand 5
├── Dockerfile
└── README.md
```

---

## 3. Root Config Files

```
E-Room/
├── docker-compose.yml                # 8 services (api, redis, minio, livekit, coturn, frontend, nginx)
├── livekit.yaml                      # LiveKit SFU config (port 7880-7881, UDP 50000-50100)
├── turnserver.conf                   # coTURN config (port 3478 TCP+UDP)
├── nginx.conf                        # Reverse proxy (api, ws, frontend static)
├── nginx-ssl.conf                    # Nginx + SSL certbot template
├── scripts/                          # Utility scripts (empty)
├── README.md
└── .gitignore
```

---

## 4. Mapping: Docs vs Actual Code (Discrepancies)

| Docs (cũ) | Code thực tế | Ghi chú |
|-----------|-------------|---------|
| Infra dạng `infrastructure/skill/` | Infra dạng `infrastructure/file.py` | Flat files, không subpackage con |
| `infrastructure/audio/` | `infrastructure/audio_pipeline.py` + `audio_whisper.py` | Pronunciation pipeline riêng |
| `infrastructure/audio.py` | `infrastructure/audio.py` | AudioBuffer + AudioBufferManager (giống) |
| `service/background_task.py` | ❌ Không tồn tại | Đã xóa |
| `service/moderation.py` | ❌ Không tồn tại | Chưa implement |
| `service/agent.py` | ❌ Không tồn tại | Agent logic trong `ws/speech.py` + `agent/` |
| `rag/vector_store.py` (PGVector) | `rag/vector_store.py` (TiDBRawVectorStore + NumpyVectorStore fallback) | Không dùng pgvector thật |
| WebSocket trong `api/routers/` | `ws/` riêng | WS handlers tách riêng khỏi API routers |
| `seed_data.py` + `tag_seed.py` trong `infrastructure/` | `seed/seed_data.py` + `seed/tag_seed.py` | Seed riêng |
| Frontend TypeScript | Frontend JavaScript (JSX) | Tất cả file .jsx, không .tsx |
| TailwindCSS + shadcn/ui | Bootstrap 5 + react-bootstrap | UI framework khác |
| CRA (Create React App) | Vite 6 + vitest | Build tool khác |
| react-hook-form + zod | Không dùng | Form validation thủ công |
| howler.js | ❌ Chưa tích hợp | TTS chưa implement |
| recharts | ❌ Chưa thấy dùng | Dashboard đang xây dựng |
| sonner | ❌ Chưa thấy dùng | Dùng react-bootstrap Toast |
| TTS | Supertonic ONNX | TTS local (CPU) |
| faster-whisper small.en (CUDA) | faster-whisper base (CPU) | Model Whisper, chạy local |

---

## Liên quan

- [[ERoom/deployment|Triển khai & Vận hành]] — Docker, config, deploy
- [[ERoom/dev-notes|Dev Notes]] — Trạng thái hiện tại, testing, known issues
- [[ERoom/overview|Tổng quan]] — Kiến trúc tổng thể
- [[ERoom/notes|Ghi chú kỹ thuật]] — API contracts, Redis keys, DB schemas
