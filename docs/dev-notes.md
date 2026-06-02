---
title: ERoom — Dev Notes
tags:
  - dev-notes
  - development
  - testing
  - utils
  - ERoom
created: 2026-05-10
updated: 2026-06-02
---

# Dev Notes

> [!abstract] Trạng thái phát triển hiện tại & tài liệu tham khảo cho dev
> Current state, utils reference, testing guide, known issues, và cách chạy project.

> [!info] Điều hướng nhanh
> [[ERoom/overview|← Tổng quan]] · [[ERoom/project-structure|Cấu trúc dự án →]] · [[ERoom/deployment|Triển khai →]]

---

## 1. Trạng thái Hiện tại (2026-06-02)

### Đã Implement & Chạy được

| Component | Trạng thái | Chi tiết |
|-----------|-----------|----------|
| Docker Compose | ✅ Đầy đủ | 9 services (api, celery_worker, celery_beat, redis, minio, livekit, coturn, frontend, nginx) |
| LiveKit SFU | ✅ Chạy | Port 7880-7881, UDP 50000-50100 |
| coTURN | ✅ Chạy | Port 3478 TCP+UDP |
| FastAPI Backend | ✅ Chạy | Port 8000, 12 routers, 2 WS endpoints |
| Celery Worker + Beat | ✅ Chạy | 6 periodic tasks (matching 5s, heartbeat 45s, moderation 10s...) |
| Redis | ✅ Chạy | Queue (Celery), cache, pub/sub (CeleryBridge) |
| Minio | ✅ Chạy | 4 buckets (rag-docs, tts, avatars, evidence) |
| Nginx | ✅ Chạy | Reverse proxy port 80 |
| Frontend (React 19) | ✅ Chạy | Port 3000 (Vite 6, Bootstrap 5, Zustand 5) |
| MySQL | ✅ Kết nối | Local MySQL (SQLModel + PyMySQL) |
| RAG Pipeline (langchain) | ✅ Hoạt động | Nomic 768-dim, TiDBRawVectorStore + NumpyVectorStore fallback |
| Pronunciation Pipeline | ✅ Hoạt động | Whisper base (CPU) + Wav2Vec2 + CMU Dict + GOP Scorer |
| AI Agent (local LLM) | ✅ Hoạt động | LM Studio endpoint (OpenAI-compatible), 3 roles via system prompts |
| Alembic Migrations | ✅ Setup | 2 versions |
| Authentication | ✅ Đầy đủ | JWT access+refresh, Argon2, Redis blacklist, rate limiting |
| Tag System | ✅ Đầy đủ | 53 preset tags, CRUD, search, bulk-add, custom tags |
| Matching Engine | ✅ Đầy đủ | Jaccard similarity, 3-stage fallback (30s→45s→60s) |
| WebSocket Chat | ✅ Đầy đủ | Chat messages, audio chunks, VAD detection, transcript relay |
| WebSocket Audio | ✅ Đầy đủ | Audio streaming → Whisper → Wav2Vec2 → PronunciationPipeline |
| Unit/Integration Tests | ✅ 142+/147 pass | 12 test modules |

### Đang Phát triển

| Component | Trạng thái |
|-----------|-----------|
| Frontend ChatWindow (đầy đủ) | 🔄 Đang code — 9 components |
| Frontend Onboarding Wizard | 🔄 Đang code — 5 steps |
| TTS Integration | ⏳ Pending — ElevenLabs/OpenAI |
| NSFW Detection | ⏳ Pending — self-host nsfw_detector |
| Subscription (Stripe) | ⏳ Pending — config có sẵn |
| Expert RAG WebSocket events | 🔄 Đang code |
| Frontend Dashboard | 🔄 Đang code |
| Auto Take Note (Pro+) | ⏳ Pending |

### Database

- **Chính**: Local MySQL — `mysql+pymysql://root:password@localhost:3306/eroom`
- **Test**: SQLite tự động — `sqlite:///./test_eroom.db` (pytest conftest)
- **Vector store**: TiDBRawVectorStore (MySQL table `rag_embeddings`, pickle numpy arrays, brute-force cosine) + NumpyVectorStore fallback
- Đã switch từ TiDB Cloud → Local MySQL (xem [[ERoom/decisions#ADR-021|ADR-021]])

---

## 2. Utils Reference (`app/utils/`)

> [!tip] Anh dặn: "tận dụng utils" — đây là reference nhanh

### `datetime_utils.py`
```python
# Hàm xử lý datetime: now_utc(), format_iso(), parse_duration()
from app.utils.datetime_utils import now_utc, format_iso
```

### `file_handle.py`
```python
# Hàm xử lý file: safe_read(), get_extension(), validate_file_size()
from app.utils.file_handle import safe_read, get_extension
```

### `logging_setup.py`
```python
# Cấu hình structured logging (structlog)
from app.utils.logging_setup import setup_logging
setup_logging(level="INFO")
```

### `retry.py`
```python
# Decorator retry với exponential backoff
from app.utils.retry import retry_on_failure

@retry_on_failure(max_attempts=3, base_delay=1.0)
async def call_external_api():
    ...
```

### `text.py`
```python
# Xử lý text: truncate(), sanitize_html(), slugify()
from app.utils.text import truncate, sanitize_html, slugify
```

### `validation.py`
```python
# Validate input: is_valid_email(), is_valid_password(), sanitize_input()
from app.utils.validation import is_valid_email, sanitize_input
```

---

## 3. Testing

### 3.1 Cấu trúc Test (thực tế)

```
backend/tests/
├── conftest.py                       # Fixtures: engine (SQLite), db_session, client, test_user, auth_headers, mock_redis, mock_livekit
├── test_edge_cases.py                # Unicode, XSS, SQL injection
├── test_infrastructure.py            # Infrastructure tests
├── test_minio.py                     # MinIO CRUD operations
├── test_real_speech.py               # PronunciationPipeline tests
├── test_redis.py                     # Redis CRUD + rate limiter
├── test_token_store.py               # JWT blacklist
├── test_websocket.py                 # WebSocket handler tests
├── test_integration/
│   ├── test_api_health.py            # Health checks (6 pass)
│   ├── test_auth_api.py              # Auth flow (15 pass)
│   ├── test_matching_pipeline.py     # Matching flow (10 pass)
│   └── test_room_api.py              # Room CRUD (12 pass)
└── test_unit/
    ├── test_agent.py                 # Corrector, Expert, Heartbeat (16 pass)
    ├── test_audio_pipeline.py        # Audio processing (8 pass)
    ├── test_core.py                  # Core RAG imports (17 pass)
    ├── test_matching.py              # Matching engine (9 pass)
    ├── test_models.py                # SQLModel entities (8 pass)
    ├── test_rag.py                   # Chunking, embedding, retrieval (25 pass)
    └── test_security.py              # Auth, rate limiting (12 pass)
```

### 3.2 Chạy Test

```bash
cd backend
uv run python -m pytest tests/ -v --tb=short          # Tất cả
uv run python -m pytest tests/test_unit/ -v            # Unit only
uv run python -m pytest tests/test_integration/ -v     # Integration only
uv run python -m pytest tests/test_rag.py -v           # RAG cụ thể
uv run python -m pytest tests/ --cov=app --cov-report=term-missing  # Coverage
```

### 3.3 Test Fixtures (conftest.py)

- **engine** (session scope): SQLite (`sqlite:///./test_eroom.db`), auto-create tables, cleanup on teardown
- **db_session** (function scope): Transaction rollback giữa các test
- **client**: TestClient với `get_db_session` + `rate_limit_login` overridden
- **test_user**: Pre-seeded user (B1, learning_goal="Improve speaking")
- **auth_headers**: Login response → Bearer token
- **mock_redis**: `unittest.mock.patch` → RedisCRUD
- **mock_livekit**: `unittest.mock.patch` → LiveKitService

### 3.4 Kết quả Hiện tại: ~142/147 Pass (~97%)

| Module | Pass | Fail | Error |
|--------|------|------|-------|
| test_agent | 16 | 0 | 0 |
| test_rag | 25 | 2 | 0 |
| test_core | 17 | 2 | 0 |
| test_matching | 9 | 0 | 0 |
| test_models | 8 | 0 | 1 |
| test_security | 12 | 0 | 0 |
| test_audio_pipeline | 8 | 0 | 0 |
| test_auth_api | 15 | 0 | 0 |
| test_room_api | 12 | 0 | 0 |
| test_matching_pipeline | 10 | 0 | 0 |
| test_api_health | 6 | 0 | 0 |
| test_edge_cases | 4 | 0 | 0 |

**Lỗi đã biết:**
- 2 test_rag: dimension mismatch (1536 vs 768) — cache venv, fix bằng `uv sync --reinstall`
- 2 test_core: đã fix (check `_dim` thay `_model`, dùng `NumpyVectorStore`)
- 1 test_models: missing `db_session` fixture — cần DB TiDB chạy

### 3.4 Test Features vs ERoom Docs

| Tính năng | Có test? | Ghi chú |
|-----------|----------|---------|
| F-AUTH-01 (Auth) | ✅ | test_auth_api, test_security |
| F-TAG-01 (Tags) | ⚠️ | Logic trong matching tests |
| F-MATCH-01 (Matching) | ✅ | test_matching, test_matching_pipeline |
| F-ROOM-01/02 (Room) | ✅ | test_room_api, test_audio_pipeline |
| F-AI-01/02/03 (Agent) | ✅ | test_agent |
| F-AI-05 (RAG) | ✅ | test_rag |
| F-AI-04 (TTS) | ❌ | Chưa implement |
| F-AI-06 (Notes) | ❌ | Chưa implement |
| F-MOD-01/02 (Moderation) | ❌ | Chưa implement |
| F-BILL-01/02 (Subscription) | ❌ | Chưa implement |

---

## 4. Known Issues

### 4.1 Test Failures
- **Embedding dimension mismatch**: `uv sync --reinstall` để fix cache venv
- **Missing db_session fixture**: Cần MySQL hoặc SQLite connection cho integration tests
- **test_real_speech.py**: Cần model và audio thật, không chạy trong CI

### 4.2 Infrastructure
- ~~**TiDB Cloud latency**: ~50-100ms~~ ✅ **Không còn vấn đề** — đã switch sang MySQL local
- **coTURN logs trống**: Log level mặc định thấp, thêm `--verbose` nếu cần debug
- **LiveKit high CPU warning**: Thỉnh thoảng xuất hiện khi idle, không ảnh hưởng
- **Hai hệ thống heartbeat song song**: Celery beat (`room_heartbeat_tick` 45s) + asyncio loop (`service/heartbeat.py`) — cần cleanup

### 4.3 Code
- **LangChain agent**: Đã refactor từ StateGraph → create_agent (single agent). Dùng langchain v1.2+ (không phải 0.3.x như docs cũ)
- **Embedding service**: Dùng Nomic API (768-dim), không phải OpenAI text-embedding-3-small
- **Vector store**: TiDBRawVectorStore (MySQL `rag_embeddings` table, pickle numpy arrays), KHÔNG phải pgvector thật
- **Alembic vs migrations/**: Có 2 thư mục migration (alembic + migrations), cần cleanup
- **Mixed CRA/Vite env vars**: `api/client.js` dùng `process.env.REACT_APP_*`, `websocket.js` dùng `import.meta.env.VITE_*` — cần đồng bộ
- **EventBus blocking**: `event_bus.py` dùng synchronous Redis polling trong async context
- **Chồng chéo speech pipeline**: `celery/ai.py:transcribe_audio` và `ws/speech.py:process_speech` có overlapping functionality

### 4.4 So sánh Docs vs Code

| Docs nói | Thực tế | Ghi chú |
|----------|---------|---------|
| Frontend TypeScript | JavaScript (JSX) | Tất cả file .jsx |
| TailwindCSS + shadcn/ui | Bootstrap 5 + react-bootstrap | UI framework hoàn toàn khác |
| CRA | Vite 6 + vitest | Build toolchain khác |
| howler.js | ❌ Chưa có | TTS chưa implement |
| OpenAI TTS | Config ElevenLabs | API key có, chưa code |
| recharts | ❌ Chưa dùng | Dashboard đang xây dựng |
| react-hook-form + zod | ❌ Chưa dùng | Form validation thủ công |
| Whisper API | faster-whisper base (CPU local) | Không gọi API, chạy local |
| GPT-4o | google/gemma-4-e2b (LM Studio) | Local LLM, không OpenAI

---

## 5. Quick Start (Development)

```bash
# 1. Khởi động infrastructure services
docker compose up -d redis minio livekit coturn nginx

# 2. Kiểm tra
docker compose ps
curl http://localhost:8000/health
curl http://localhost:7880          # → "OK"

# 3. Backend (cần Python 3.13+)
cd backend
uv sync                            # Cài dependencies (có faster-whisper + torch)
uv run python -m app.server        # Chạy FastAPI (port 8000)

# 4. Frontend (terminal khác)
cd frontend
npm install
npm run dev                        # Vite dev server (port 3000)

# 5. Chạy tests
cd backend
uv run python -m pytest tests/ -v --tb=short

# 6. Truy cập
# Frontend: http://localhost:3000
# API docs: http://localhost:8000/docs
# Minio console: http://localhost:9001 (minioadmin/minioadmin)
# LiveKit: http://localhost:7880 (trả về "OK")
```

> [!warning] Yêu cầu
> - **LLM**: Cần LM Studio (hoặc OpenAI-compatible endpoint) tại `http://127.0.0.1:1234/v1` với model `google/gemma-4-e2b`
> - **faster-whisper**: Tự động tải model `base` (~1.5GB) lần đầu chạy
> - **Wav2Vec2**: Tự động tải `facebook/wav2vec2-base-960h` (~1.2GB) lần đầu chạy
> - **MySQL**: Cần MySQL local (hoặc SQLite cho test tự động)

---

## 6. LangChain Integration Notes (Actual)

### Dependencies (pyproject.toml)

```toml
"langchain>=1.2.2",
"langchain-community>=0.4.1",
"langchain-openai>=1.1.7",
"langchain-text-splitters>=1.1.0",
"langgraph>=1.0.5",
"langgraph-prebuilt>=1.0.5",
"langchain-nomic>=1.0.1",
"nomic>=3.9.0",
```

### RAG Pipeline

```
Document Upload (Minio) → TextChunker (RecursiveCharacterTextSplitter, 512 chars, overlap 64)
    → EmbeddingService (Nomic API, 768-dim, cache 24h)
    → TiDBRawVectorStore OR NumpyVectorStore (fallback)
    → RetrievalService (cosine similarity + keyword scoring)
    → LLM Answer (LM Studio endpoint)
```

### Agent (3 roles, single agent)

```python
from app.agent.base import call_llm_json, call_llm_text
from app.agent.llm import get_llm

# Corrector
from app.agent.corrector import correct_text
correct_text(text="I go to school yesterday", scores={...}, word_phonemes=[...])
# → {"corrected": "...", "errors": [...], "score": 7, "pronunciation_feedback": "...", "tts_text": "..."}

# Expert
from app.agent.expert import answer_expert
answer_expert(query="Kubernetes là gì?", tag_ids=[...])
# → Hybrid RAG + Web Search → LLM answer

# Heartbeat
from app.agent.heartbeat import generate_heartbeat_question
generate_heartbeat_question(tags=[...], participants=[...], heartbeat_count=1)
# → {"question": "...", "context": "...", "suggested_response": "..."}
```

### LlamaIndex / LangChain Usage Pattern

Không dùng `create_agent` từ langchain.agents. Code thực tế gọi LLM qua:
1. `get_llm()` → `ChatOpenAI` (OpenAI-compatible endpoint)
2. LangChain `@tool` decorator cho `search_knowledge` (RAG retrieval tool)
3. LangGraph (langgraph>=1.0.5) import sẵn nhưng chưa dùng
4. LangChain Nomic embeddings: `langchain_nomic.NomicEmbeddings`

### Pronunciation Pipeline (không dùng langchain)

```
Audio PCM (16kHz, mono) → faster-whisper base (CPU)
    └── transcript text (song song với Wav2Vec2)
        └── Wav2Vec2 Aligner (forced alignment Viterbi)
            └── CMU Dictionary (ARPAbet lookup)
                └── PronunciationScorer (Accuracy + GOP + Fluency + Prosody)
                    └── overall score 0-100
                        └── Nếu < 70: LLM correction
```

---

## Liên quan

- [[ERoom/project-structure|Cấu trúc dự án]] — Map file-to-file
- [[ERoom/deployment|Triển khai & Vận hành]] — Docker, config, deploy
- [[ERoom/notes|Ghi chú kỹ thuật]] — API contracts, Redis keys
- [[ERoom/decisions|Quyết định kiến trúc]] — ADRs
