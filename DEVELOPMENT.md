# ERoom — Development Guide

## Prerequisites

- Python 3.13+
- Node.js 22+
- uv (Python package manager)
- Docker & Docker Compose (for infra services)

## Setup

```bash
git clone <repo-url> e-room
cd e-room

# ---- Backend ----
cd backend
uv sync                    # Install dependencies
cp .env.docker.sample .env # Configure locally (or use .env.docker for Docker)
cd ..

# ---- Frontend ----
cd frontend
npm install
cd ..

# ---- Infra (Redis, MinIO, LiveKit, coTURN) ----
docker compose up -d redis minio livekit coturn nginx
# Note: api, celery_worker, celery_beat, frontend run locally for dev
```

## Running Locally

### Backend
```bash
cd backend
uv run python -m app.server   # Starts at http://localhost:8000
# API docs: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc
```

### Frontend
```bash
cd frontend
npm start                     # Starts at http://localhost:3000
```

### Celery (background tasks)
```bash
cd backend
uv run celery -A app.infrastructure.celery.celery_app worker --loglevel=info
uv run celery -A app.infrastructure.celery.celery_app beat --loglevel=info
```

## Project Structure

```
e-room/
├── backend/
│   ├── app/
│   │   ├── agent/          # AI agents (Corrector, Expert, Heartbeat)
│   │   ├── api/            # FastAPI routes + dependencies
│   │   │   └── routers/    # auth, room, message, tag, user, infra, health
│   │   ├── infrastructure/ # Celery, Redis, MinIO, LiveKit, WebSocket
│   │   │   ├── celery/     # Tasks: ai, matching, moderation, rag, tts
│   │   │   ├── redis/      # Redis client + rate limiter
│   │   │   ├── minio/      # Object storage client
│   │   │   ├── livekit/    # LiveKit service
│   │   │   ├── audio/      # Audio processing
│   │   │   └── websocket/  # WebSocket manager
│   │   ├── model/          # SQLModel tables (13 models)
│   │   ├── schemas/        # Pydantic request/response schemas
│   │   ├── service/        # Business logic layer
│   │   ├── rag/            # RAG: chunking, embedding, vector store
│   │   ├── utils/          # Utilities (text, validation, retry, etc.)
│   │   ├── config.py       # Pydantic settings
│   │   ├── database.py     # DB engine + table creation
│   │   ├── main.py         # FastAPI app + middleware
│   │   ├── security.py     # JWT + password hashing
│   │   └── log.py          # Structured logging
│   ├── alembic/            # Database migrations
│   │   └── versions/       # Migration scripts
│   ├── scripts/            # Utility scripts
│   │   └── migrate_to_postgres.py
│   ├── tests/
│   │   ├── conftest.py     # Test fixtures (client, test_user, mocks)
│   │   ├── test_unit/      # Unit tests (8 files)
│   │   └── test_integration/ # Integration tests (4 files)
│   ├── pyproject.toml      # Dependencies (uv)
│   ├── .env.docker         # Docker environment variables
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/            # API client (ApiClient.js)
│   │   ├── app/            # App + pages + auth context
│   │   │   └── pages/      # HomePage, LearningPage, PaymentPage, ProfilePage
│   │   ├── components/
│   │   │   ├── base/       # Hooks, base components
│   │   │   └── ui/         # Avatar, Badge, ChatBox, RoomCard, Toast, etc.
│   │   ├── context/        # ThemeContext
│   │   ├── features/       # Feature modules (auth, rooms, realtime, tags, AI)
│   │   ├── hooks/          # useAsyncResource
│   │   ├── lib/            # api.js, websocket.js
│   │   └── __mocks__/      # Jest mocks (LiveKit, react-router)
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml      # All services
├── nginx.conf              # Reverse proxy config
├── livekit.yaml            # LiveKit server config
├── turnserver.conf         # coTURN config
├── init-buckets.sh         # MinIO bucket init script
├── .github/workflows/ci.yml # CI/CD pipeline
├── DEPLOYMENT.md           # Deployment guide
└── DEVELOPMENT.md          # This file
```

## Key Commands

```bash
# ---- Backend ----
uv run pytest tests/ -q                    # All tests
uv run pytest tests/ --cov=app --cov-report=term  # Coverage
uv run ruff check app/ tests/              # Lint
uv run alembic revision --autogenerate -m "message"  # New migration
uv run alembic upgrade head                # Apply migrations

# ---- Frontend ----
npm test -- --watchAll=false               # Run tests
npx eslint src/                            # Lint
npm run build                              # Production build

# ---- Docker ----
docker compose up -d                       # Start all services
docker compose ps                          # List services
docker compose logs -f api                 # Tail backend logs
docker compose restart api                 # Restart backend
docker compose down -v                     # Stop all + remove volumes
```

## Testing

- **208 tests** across 12 test files (unit + integration)
- **Coverage**: 58% (improving)
- **Test DB**: SQLite in-memory (`tests/conftest.py`)
- **Fixtures**: `client` (TestClient), `test_user`, `auth_headers`, `mock_redis`, `mock_livekit`
- **Rate limit override**: `rate_limit_login` is no-op in tests

### Running specific tests
```bash
uv run pytest tests/test_unit/test_matching.py -v
uv run pytest tests/test_integration/test_matching_pipeline.py -v
uv run pytest tests/ -k "test_login" -v
```

## Code Style

- **Backend**: Ruff (replaces flake8 + isort + black)
- **Frontend**: ESLint (extends react-app)
- **Pre-commit**: Not yet configured (TODO)

## Adding a New Feature

1. **Model**: Add SQLModel class in `app/model/`
2. **Schema**: Add Pydantic schemas in `app/schemas/`
3. **Service**: Add business logic in `app/service/`
4. **Router**: Add FastAPI routes in `app/api/routers/`
5. **Test**: Add tests in `tests/`
6. **Migration**: `cd backend && uv run alembic revision --autogenerate -m "add X table"`
