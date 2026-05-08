# TODO.md — E-Room

## Done
- [x] Nunit font + Bootstrap + React Bootstrap integration
- [x] react-icons (Heroicons v2) on all pages
- [x] Rename Dashboard → Learning
- [x] Rewrite HomePage, LearningPage, ProfilePage, PaymentPage, LoginPage with react-icons
- [x] Fix room creation API bug (livekit token method)
- [x] Add 10 seed rooms to seed_data.py
- [x] Add seed_rooms startup logic to main.py
- [x] Production-grade infrastructure rewrite (redis, minio, livekit, websocket, etc.)
- [x] Comprehensive utils (retry, text, datetime, validation, logging)
- [x] Remove redundant BaseService, refactor services to use CRUDRepository
- [x] Docker compose with 10 services running

## In Progress
- [ ] Rebuild backend Docker container to run room seeding
- [ ] Verify 10 rooms appear at /api/v1/rooms

## To Do — Next Priority
- [ ] pgvector + PostgreSQL migration (from SQLite)
- [ ] AI Corrector (GPT-4o prompt + JSON correction schema)
- [ ] Matching engine (Jaccard similarity)
- [ ] Expert RAG pipeline (Minio → embed → pgvector → Brave Search → LLM)
- [ ] TTS (OpenAI tts-1 + Minio cache)
- [ ] NSFW image moderation
- [ ] Anti-misuse intent classifier
- [ ] Subscription + Stripe integration
- [ ] Leaderboard + Room Series UI
- [ ] Session notes UI
