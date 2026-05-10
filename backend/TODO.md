# TODO.md — ERoom Backend

## ✅ Done
- [x] Fix critical bugs: livekit import json, redis prefix engconnect→eroom
- [x] Celery tasks (5 files: ai, matching, moderation, rag, tts)
- [x] Audio pipeline (AudioBuffer, AudioProcessor, AudioBufferManager)
- [x] AI Agent 3-trong-1 (Corrector, Expert, Heartbeat)
- [x] RAG Layer (chunking, embedding, file_handle, vector_store, retrieval)
- [x] Config: llm_base_url, llm_model, llm_api_key
- [x] Agent API key: uses llm_api_key (not secret_key)
- [x] Test conftest.py

## 🔄 In Progress
- [ ] Test suite (unit + integration + pipeline) — need 30+ files
- [ ] WebSocket /ws/audio/{room_id} endpoint
- [ ] Infrastructure __init__.py audio exports
- [ ] Remove comment lines from all code (#)

## ⏳ Priority 7 — Improvements
- [ ] Matching engine upgrade (Jaccard + level proximity + subscription tier)
- [ ] PostgreSQL + pgvector migration
- [ ] Dockerfile layer caching optimization
- [ ] Alembic migration for missing tables
- [ ] Health check endpoints (Redis, Minio, LiveKit)
- [ ] FlowAssist RAG patterns fully integrated
