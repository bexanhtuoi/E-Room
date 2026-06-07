---
title: ERoom — Dev Notes
tags:
  - dev-notes
  - development
  - testing
  - utils
  - ERoom
created: 2026-05-10
updated: 2026-06-06
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
| Docker Compose | ✅ Đầy đủ | 8 services (api, redis, minio, livekit, coturn, frontend, nginx) |
| LiveKit SFU | ✅ Chạy | Port 7880-7881, UDP 50000-50100 |
| coTURN | ✅ Chạy | Port 3478 TCP+UDP |
| FastAPI Backend | ✅ Chạy | Port 8000, 12 routers, 2 WS endpoints |
| Redis | ✅ Chạy | Cache, pub/sub, distributed locks |
| Minio | ✅ Chạy | 4 buckets (rag-docs, tts, avatars, evidence) |
| Nginx | ✅ Chạy | Reverse proxy port 80 |
| Frontend (React 19) | ✅ Chạy | Port 3000 (Vite 6, Bootstrap 5, Zustand 5) |
| MySQL | ✅ Kết nối | Local MySQL (SQLModel + PyMySQL) |
| RAG Pipeline (langchain) | ✅ Hoạt động | Nomic 768-dim, TiDBRawVectorStore + NumpyVectorStore fallback |
| Pronunciation Pipeline | ✅ Hoạt động | faster-whisper small.en + CMU Dict + confidence scoring |
| AI Agent (local LLM) | ✅ Hoạt động | llama.cpp endpoint (port 8012, OpenAI-compatible), 3 roles via system prompts |
| Alembic Migrations | ✅ Setup | 2 versions |
| Authentication | ✅ Đầy đủ | JWT access+refresh, Argon2, Redis blacklist, rate limiting |
| Tag System | ✅ Đầy đủ | 53 preset tags, CRUD, search, bulk-add, custom tags |
| Matching Engine | ✅ Đầy đủ | Jaccard similarity, 3-stage fallback (30s→45s→60s) |
| WebSocket Chat | ✅ Đầy đủ | Chat messages, audio chunks, VAD detection, transcript relay |
| WebSocket Audio | ✅ Đầy đủ | Audio streaming → Whisper → PronunciationPipeline |
| Unit/Integration Tests | ✅ 142+/147 pass | 12 test modules |

### Đang Phát triển

| Component | Trạng thái |
|-----------|-----------|
| Frontend ChatWindow (đầy đủ) | 🔄 Đang code — 9 components |
| Frontend Onboarding Wizard | 🔄 Đang code — 5 steps |
| TTS Integration | ✅ Hoạt động | Supertonic ONNX model (CPU) |
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
├── api/                              # API endpoint tests
│   ├── test_auth.py                  # Auth flows
│   ├── test_edge_cases.py            # Unicode, XSS, SQL injection
│   ├── test_health.py                # Health checks
│   ├── test_rooms.py                 # Room CRUD
│   └── test_users.py                 # User profile
├── e2e/                              # End-to-end tests
│   ├── test_full_flow.py             # Full pipeline (model inference, marked @slow)
│   └── test_model_cache.py           # Model caching behavior
├── integration/                      # Integration tests (cần DB/Redis thật)
│   ├── test_audio_pipeline_int.py    # Audio pipeline
│   ├── test_auth_service.py          # Auth service
│   ├── test_redis.py                 # Redis CRUD + rate limiter (cần Redis)
│   ├── test_token_store_int.py       # JWT blacklist
└── unit/                             # Unit tests (no external deps)
    ├── test_audio_buffer.py          # AudioBuffer VAD logic
    ├── test_audio_dictionary.py      # CMU Dictionary
    ├── test_audio_pipeline.py        # PronunciationPipeline (mocked)
    ├── test_auth_middleware.py        # Auth middleware
    ├── test_chunking.py              # Text chunking
    ├── test_config.py                # Settings
    ├── test_embedding.py             # Embedding service
    ├── test_event_bus.py             # EventBus lifecycle
    ├── test_logging_middleware.py    # Logging middleware
    ├── test_minio.py                 # MinIO client (mocked)
    ├── test_rate_limiter.py          # Rate limiter
    ├── test_redis_crud.py            # RedisCRUD (mocked)
    ├── test_security.py              # JWT + Argon2
    ├── test_serialize.py             # Serialize/deserialize
    └── test_vector_store.py          # Vector store
```

### 3.2 Chạy Test

```bash
cd backend
uv run pytest -v --tb=short                     # Tất cả (trừ @slow)
uv run pytest -v -m "not slow"                  # Chỉ fast tests
uv run pytest tests/unit/ -v                    # Unit only
uv run pytest tests/integration/ -v             # Integration only
uv run pytest -v -m slow                        # Slow (cần model thật)
uv run pytest --cov=app --cov-report=term-missing  # Coverage
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
- **Heartbeat loop**: Asyncio loop (`service/heartbeat.py`) — chỉ còn 1 hệ thống

### 4.3 Code
- **LangChain agent**: Đã refactor từ StateGraph → create_agent (single agent). Dùng langchain v1.2+ (không phải 0.3.x như docs cũ)
- **Embedding service**: Dùng Nomic API (768-dim), không phải OpenAI text-embedding-3-small
- **Vector store**: TiDBRawVectorStore (MySQL `rag_embeddings` table, pickle numpy arrays), KHÔNG phải pgvector thật
- **Alembic vs migrations/**: Có 2 thư mục migration (alembic + migrations), cần cleanup
- **Mixed CRA/Vite env vars**: `api/client.js` dùng `process.env.REACT_APP_*`, `websocket.js` dùng `import.meta.env.VITE_*` — cần đồng bộ
- **EventBus blocking**: `event_bus.py` dùng synchronous Redis polling trong async context
- **Chồng chéo speech pipeline**: `audio_pipeline.py:assess` và `process_speech` cần gọn lại

### 4.4 So sánh Docs vs Code

| Docs nói | Thực tế | Ghi chú |
|----------|---------|---------|
| Frontend TypeScript | JavaScript (JSX) | Tất cả file .jsx |
| TailwindCSS + shadcn/ui | Bootstrap 5 + react-bootstrap | UI framework hoàn toàn khác |
| CRA | Vite 6 + vitest | Build toolchain khác |
| howler.js | ❌ Chưa có | TTS chưa implement |
| Supertonic TTS | ONNX model local | Chạy local CPU |
| recharts | ❌ Chưa dùng | Dashboard đang xây dựng |
| react-hook-form + zod | ❌ Chưa dùng | Form validation thủ công |
| FunASR (design doc) | faster-whisper small.en (CUDA) | Chạy local — docs cũ ghi FunASR |
| GPT-4o | Gemma 4 E2B Q8_0 (llama.cpp port 8012) | Local LLM, không OpenAI
| Nomic Embeddings | Qwen3 Embedding 0.6B (llama.cpp port 8013) | Local embedding, không Nomic API

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
uv sync                            # Cài dependencies (faster-whisper, langchain, ...)
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
> - **LLM**: Cần llama.cpp server chạy model `gemma-4-E2B-it-Q8_0.gguf` tại port 8012
> - **Embedding**: Cần llama.cpp server chạy model `Qwen3-Embedding-0.6B-Q8_0.gguf` tại port 8013
> - **Whisper**: `faster-whisper small.en` — tự động tải lần đầu chạy (cache tại `weight/whisper/`)
> - **CMU Dictionary**: `weight/cmudict.json` — tự động download từ GitHub nếu chưa có
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
4. LangChain OpenAI embeddings: `langchain_openai.OpenAIEmbeddings`

### Pronunciation Pipeline (không dùng langchain)

```
Audio PCM (16kHz, mono) → faster-whisper small.en (CUDA)
    └── transcript text + avg_logprob per segment
        └── CMU Dictionary (ARPAbet lookup per word)
            └── confidence scoring (avg_logprob → 0-100)
                └── overall score 0-100
                    └── Nếu < 70: LLM correction
```

---

## Liên quan

- [[ERoom/project-structure|Cấu trúc dự án]] — Map file-to-file
- [[ERoom/deployment|Triển khai & Vận hành]] — Docker, config, deploy
- [[ERoom/notes|Ghi chú kỹ thuật]] — API contracts, Redis keys
- [[ERoom/decisions|Quyết định kiến trúc]] — ADRs
