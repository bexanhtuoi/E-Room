---
title: ERoom — Ghi chú kỹ thuật
tags:
  - notes
  - technical
  - ERoom
  - reference
updated: 2026-06-02
---

# Ghi chú kỹ thuật

> [!abstract] Tham khảo kỹ thuật đầy đủ
> ERD database, API contracts, Redis keys, Minio buckets, RAG architecture, WebSocket events, và cấu hình cho ERoom thế hệ mới. Kiến trúc Tag, AI Agent 3-trong-1, RAG, TTS, Image Moderation, và Subscription Pro/Pro+.

> [!info] Điều hướng nhanh
> [[ERoom/overview|← Tổng quan]] · [[ERoom/features|← Tính năng]] · [[ERoom/workflow|← Luồng hoạt động]] · [[ERoom/tasks|Công việc →]] · **Ghi chú kỹ thuật** · [[ERoom/decisions|Quyết định kiến trúc →]]

---

## 1. DATABASE — ERD Tổng quan

```mermaid
erDiagram
    users ||--o{ user_tags : "has"
    tags ||--o{ user_tags : "tagged_as"
    users ||--o{ refresh_tokens : "owns"
    users ||--o{ subscriptions : "subscribes"
    users ||--o{ room_participants : "participates"
    users ||--o{ sessions : "has_session"
    users ||--o{ session_notes : "has_notes"
    users ||--o{ room_series : "creates"
    users ||--o{ leaderboard : "ranks_in"
    users ||--o{ moderation_events : "reported"
    users ||--o{ agent_misuse_logs : "misused"
    users ||--o{ notifications : "notified"
    users ||--o{ topic_room_registrations : "registers"

    rooms ||--o{ room_participants : "contains"
    rooms ||--o{ messages : "has_messages"
    rooms ||--o{ sessions : "generates"
    rooms ||--o{ moderation_events : "moderated_in"
    rooms ||--o{ agent_misuse_logs : "misuse_in"

    tags ||--o{ knowledge_documents : "categorized_as"
    tags ||--o{ room_series : "themed_as"
    tags ||--o{ topic_rooms : "tagged_with"

    knowledge_documents ||--o{ knowledge_chunks : "chunked_into"

    sessions ||--o{ session_notes : "summarized_in"

    room_series ||--o{ topic_rooms : "scheduled_in"
    topic_rooms ||--o{ topic_room_registrations : "has_registrations"

    users {
        uuid id PK "UUID v4"
        varchar email UK "UNIQUE NOT NULL"
        varchar password_hash
        varchar display_name
        text avatar_url
        varchar english_level "A1-C2, nullable"
        varchar career_field
        varchar job_title
        varchar learning_goal "work|interview|fluency|business|academic"
        boolean auto_join_enabled "DEFAULT TRUE"
        boolean profile_completed "DEFAULT FALSE"
        boolean email_verified "DEFAULT FALSE"
        boolean is_active "DEFAULT TRUE"
        boolean is_banned "DEFAULT FALSE"
        text ban_reason
        int strikes "0-5"
        timestamptz created_at
        timestamptz updated_at
        timestamptz last_login_at
    }

    tags {
        uuid id PK
        varchar name UK "NOT NULL"
        varchar slug UK "NOT NULL"
        varchar category "technology|business|science|creative|lifestyle|other"
        varchar icon
        boolean is_custom "DEFAULT FALSE"
        boolean approved "DEFAULT TRUE"
        int usage_count "DEFAULT 0"
        timestamptz created_at
    }

    user_tags {
        uuid id PK
        uuid user_id FK "→ users.id CASCADE"
        uuid tag_id FK "→ tags.id CASCADE"
        timestamptz created_at
    }

    refresh_tokens {
        uuid id PK
        uuid user_id FK "→ users.id CASCADE"
        varchar token_hash UK "NOT NULL"
        varchar device_info
        inet ip_address
        timestamptz expires_at
        boolean revoked "DEFAULT FALSE"
        timestamptz created_at
    }

    subscriptions {
        uuid id PK
        uuid user_id FK "→ users.id CASCADE, UNIQUE"
        varchar tier "free|pro|pro_plus, DEFAULT free"
        varchar stripe_customer_id UK
        varchar stripe_subscription_id UK
        varchar status "active|canceled|past_due|trialing"
        timestamptz trial_ends_at
        timestamptz current_period_start
        timestamptz current_period_end
        timestamptz canceled_at
        timestamptz created_at
        timestamptz updated_at
    }

    rooms {
        uuid id PK
        varchar livekit_room_name UK "NOT NULL"
        text topic
        text[] tags "Array of tag slugs"
        uuid primary_tag_id FK "→ tags.id"
        varchar agent_level "basic|advanced|full, DEFAULT basic"
        varchar english_level "A1-C2, nullable"
        varchar status "IDLE|MATCHING|AGENT_LOADING|ACTIVE|DEACTIVE|REVIEW|END"
        int max_participants "3-5, DEFAULT 5"
        int current_participants "DEFAULT 0"
        int session_duration_seconds "300-3600, DEFAULT 900"
        boolean is_private "DEFAULT FALSE"
        boolean is_public "DEFAULT TRUE"
        uuid creator_user_id FK "→ users.id"
        timestamptz created_at
        timestamptz started_at
        timestamptz ended_at
    }

    room_participants {
        uuid id PK
        uuid room_id FK "→ rooms.id CASCADE"
        uuid user_id FK "→ users.id CASCADE"
        timestamptz joined_at
        timestamptz left_at
        int speaking_time_seconds "DEFAULT 0"
        int words_spoken "DEFAULT 0"
        boolean is_muted "DEFAULT FALSE"
        varchar connection_quality "good|fair|poor"
    }

    messages {
        uuid id PK
        uuid room_id FK "→ rooms.id CASCADE"
        uuid user_id FK "→ users.id, nullable"
        text content "NOT NULL"
        varchar message_type "text|system|transcript|ai_correction|ai_expert|ai_heartbeat|ai_review|tts_audio"
        jsonb metadata
        timestamptz created_at
    }

    sessions {
        uuid id PK
        uuid room_id FK "→ rooms.id CASCADE"
        uuid user_id FK "→ users.id CASCADE"
        text topic
        text[] tags
        text transcript
        jsonb full_transcript
        jsonb corrections
        jsonb ai_review
        int speaking_time_seconds "DEFAULT 0"
        int words_spoken "DEFAULT 0"
        decimal participation_pct "5,2"
        decimal overall_score "0-10, 4,2"
        decimal grammar_score "4,2"
        decimal vocabulary_score "4,2"
        decimal fluency_score "4,2"
        decimal pronunciation_score "4,2"
        int duration_seconds
        timestamptz created_at
    }

    knowledge_documents {
        uuid id PK
        uuid tag_id FK "→ tags.id CASCADE"
        varchar title "NOT NULL"
        text description
        text file_path
        varchar minio_key UK "NOT NULL"
        varchar file_type "pdf|markdown|txt|html"
        bigint file_size_bytes
        int chunk_count "DEFAULT 0"
        varchar status "pending|indexing|ready|failed"
        uuid uploaded_by FK "→ users.id"
        timestamptz created_at
        timestamptz updated_at
    }

    knowledge_chunks {
        uuid id PK
        uuid document_id FK "→ knowledge_documents.id CASCADE"
        uuid tag_id FK "→ tags.id CASCADE"
        text content "NOT NULL"
        int chunk_index "NOT NULL"
        vector embedding "1536-dim"
        jsonb metadata
        timestamptz created_at
    }

    session_notes {
        uuid id PK
        uuid user_id FK "→ users.id CASCADE"
        uuid session_id FK "→ sessions.id CASCADE"
        text content "NOT NULL (Markdown)"
        text[] tags
        int word_count "DEFAULT 0"
        timestamptz created_at
    }

    room_series {
        uuid id PK
        varchar title "NOT NULL"
        text description
        uuid creator_id FK "→ users.id"
        uuid tag_id FK "→ tags.id"
        int total_sessions "2-20"
        varchar schedule_cron
        varchar status "active|completed|canceled"
        timestamptz created_at
    }

    leaderboard {
        uuid id PK
        uuid user_id FK "→ users.id CASCADE"
        uuid tag_id FK "→ tags.id"
        date week_start "NOT NULL"
        int speaking_time_seconds
        decimal avg_score "4,2"
        int sessions_count
        int rank
        timestamptz created_at
    }

    topic_rooms {
        uuid id PK
        varchar title "NOT NULL"
        text description
        uuid tag_id FK "→ tags.id"
        uuid series_id FK "→ room_series.id, nullable"
        timestamptz scheduled_at
        uuid host_user_id FK "→ users.id"
        boolean is_ai_hosted "DEFAULT FALSE"
        int max_participants "DEFAULT 5"
        int registered_count "DEFAULT 0"
        varchar status "upcoming|live|completed|canceled"
        timestamptz created_at
    }

    topic_room_registrations {
        uuid id PK
        uuid topic_room_id FK "→ topic_rooms.id CASCADE"
        uuid user_id FK "→ users.id CASCADE"
        timestamptz created_at
    }

    moderation_events {
        uuid id PK
        uuid user_id FK "→ users.id"
        uuid room_id FK "→ rooms.id, nullable"
        varchar event_type "video_nsfw|text_hate_speech|text_spam|user_report"
        text evidence_url
        decimal confidence "4,3"
        varchar action "warning|video_off|strike|ban_24h|ban_permanent"
        text moderator_notes
        timestamptz created_at
    }

    agent_misuse_logs {
        uuid id PK
        uuid user_id FK "→ users.id"
        uuid room_id FK "→ rooms.id CASCADE"
        text query "NOT NULL"
        varchar intent "english_practice|code_request|personal_task|unrelated|unsure"
        varchar action "allowed|declined|flagged"
        timestamptz created_at
    }

    notifications {
        uuid id PK
        uuid user_id FK "→ users.id CASCADE"
        varchar title "NOT NULL"
        text body
        varchar notification_type "match_found|session_starting|review_ready|note_ready|series_starting|leaderboard_update|subscription_expiring|system"
        text action_url
        boolean is_read "DEFAULT FALSE"
        timestamptz created_at
    }
```

> [!tip] Xem chi tiết
> Mỗi bảng có đầy đủ columns, types, constraints trong ERD trên. Mối quan hệ giữa các bảng thể hiện bằng đường nối `||--o{` (one-to-many).

### 1.1 Database Connection (Actual)

| Môi trường | Database | Connection String |
|-----------|----------|-------------------|
| Dev | MySQL local | `mysql+pymysql://root:password@localhost:3306/eroom` |
| Test | SQLite | `sqlite:///./test_eroom.db` (tự động trong pytest conftest) |
| Production (trước) | ~~TiDB Cloud~~ | Đã hủy — xem [[ERoom/decisions#ADR-021|ADR-021]] |

**Config**: `app/config.py` → `Settings.database_url` (mặc định `""`, fallback `mysql+pymysql://{user}:{pass}@{host}:{port}/{db_name}`)

**Vector Store**:
- `TiDBRawVectorStore` — MySQL table `rag_embeddings` (LONGBLOB pickle numpy array, brute-force cosine)
- `NumpyVectorStore` — In-memory fallback (mất khi restart)
- `VectorStore` wrapper — tự động fallback nếu MySQL fail

---

## 2. REDIS — Tham khảo Cấu trúc Key

### 2.1 Quy ước

```
ERoom:{entity}:{identifier}:{subkey}
```

### 2.2 Định nghĩa Key (Mở rộng)

| Mẫu Key | Kiểu | TTL | Mục đích |
|------------|------|-----|---------|
| `ERoom:queue:tag:{tag_slug}` | Sorted Set | Không | Hàng đợi ghép cặp theo tag |
| `ERoom:room:{room_id}` | Hash | Vĩnh viễn | Trạng thái phòng + agent_level |
| `ERoom:user:{user_id}:presence` | String | 5 phút | Trạng thái online |
| `ERoom:ws:{user_id}` | Hash | TTL kết nối | WebSocket connection info |
| `ERoom:heartbeat:{room_id}` | String | Vĩnh viễn | Bộ đếm heartbeat |
| `ERoom:correction:{room_id}:{user_id}` | String | Vĩnh viễn | Bộ đếm sửa lỗi |
| `ERoom:expert:{room_id}` | String | Vĩnh viễn | Bộ đếm câu hỏi expert |
| `ERoom:misuse:{room_id}:{user_id}` | String | Vĩnh viễn | Bộ đếm misuse |
| `ERoom:ratelimit:login:{ip}` | String | 15 phút | Rate limit đăng nhập |
| `ERoom:ratelimit:tts:{user_id}` | String | 1h | Rate limit TTS (10/h) |
| `ERoom:lock:matching` | String (NX) | 10s | Distributed lock ghép cặp |
| `ERoom:lock:matching:tag:{tag_slug}` | String (NX) | 10s | Lock ghép cặp theo tag |
| `ERoom:cache:correction:{hash}` | String | 1h | Cache sửa lỗi LLM |
| `ERoom:cache:rag:{tag_slug}:{query_hash}` | String | 1h | Cache RAG query |
| `ERoom:cache:websearch:{hash}` | String | 1h | Cache web search |
| `ERoom:cache:tts:{sha256}` | String | 24h | Cache TTS audio URL |
| `ERoom:cache:embedding:{hash}` | String | 24h | Cache OpenAI embeddings |
| `ERoom:blacklist:token:{jti}` | String | TTL còn lại | JWT blacklist (RedisCRUD) |
| `ERoom:agent:{room_id}:rag_loaded` | String | Vĩnh viễn | Cờ RAG đã nạp |
| `ERoom:moderation:scan:{room_id}` | String | 10s | Lock quét NSFW |
| `room:transcript` | PubSub | — | Channel transcript |
| `room:correction` | PubSub | — | Channel correction |
| `room:heartbeat` | PubSub | — | Channel heartbeat |

---

## 3. MINIO — Buckets & Cấu trúc

| Bucket | Mục đích | Cấu trúc key | TTL |
|--------|----------|-------------|-----|
| `ERoom-rag-docs` | Tài liệu RAG | `{tag_slug}/{filename}` | Vĩnh viễn |
| `ERoom-tts` | Audio TTS | `{sha256}.mp3` | 24h |
| `ERoom-avatars` | Avatar agent | `{tag_slug}.png` | Vĩnh viễn |
| `ERoom-evidence` | Ảnh moderation | `{room_id}/{user_id}/{timestamp}.jpg` | 30 ngày |

---

## 4. API CONTRACTS — Điểm cuối MỚI

### 4.1 Tag Endpoints

#### `GET /api/tags/popular`
```json
{
  "data": {
    "tags": [
      {"id": "uuid", "name": "Vibe Coding", "slug": "vibe-coding", "category": "technology", "usage_count": 1234}
    ]
  }
}
```

#### `GET /api/tags/search?q=vibe&limit=10`
#### `POST /api/tags/custom` — Tạo tag tùy chỉnh [Auth Required]
```json
{"name": "Quantum Computing", "category": "science"}
```

#### `POST /api/tags/bulk-add` — Thêm nhiều tag cho user [Auth Required]
```json
{"tag_ids": ["uuid1", "uuid2", "uuid3"]}
```

#### `GET /api/users/me/tags` — Lấy tags của user hiện tại [Auth Required]

### 4.2 Room Endpoints (Cập nhật)

#### `POST /api/rooms` — Tạo room [Auth Required, Pro+]
```json
{
  "tag_ids": ["uuid1", "uuid2"],
  "topic": "Thảo luận về Vibe Coding với Claude",
  "max_participants": 5,
  "is_public": true
}
```
Response: `{"data": {"room_id": "uuid", "agent_level": "advanced"}}`

#### `POST /api/rooms/{room_id}/invite` — Mời guest Free [Auth Required, Pro+]
```json
{"email": "guest@example.com"}
```

### 4.3 TTS Endpoint

#### `POST /api/tts/generate` — Tạo audio phát âm [Auth Required, Pro+]
```json
{
  "text": "I have been working here for 3 years",
  "language": "en",
  "speed": 1.0
}
```
Response: `{"data": {"audio_url": "https://minio/ERoom-tts/abc123.mp3", "duration": 3.5}}`

### 4.4 RAG Endpoints

#### `GET /api/knowledge/search?tag=devops&query=docker+kubernetes` [Auth Required, Pro+]

#### `POST /api/knowledge/documents` — Upload tài liệu RAG [Auth Required, Admin]

### 4.5 Session Notes Endpoints

#### `GET /api/sessions/{session_id}/note` — Lấy note của phiên [Auth Required, Pro+]
#### `GET /api/users/me/notes?tag=vibe-coding&page=1` — Danh sách notes [Auth Required, Pro+]

### 4.6 Room Series Endpoints

#### `POST /api/series` — Tạo series [Auth Required, Pro+]
```json
{
  "title": "Tiếng Anh DevOps",
  "tag_id": "uuid",
  "total_sessions": 5,
  "schedule_cron": "0 19 * * 2"
}
```

#### `GET /api/series?tag=devops` — Danh sách series

### 4.7 Leaderboard Endpoints

#### `GET /api/leaderboard?tag=vibe-coding&week=2026-05-04` [Auth Required, Pro+]

### 4.8 Agent Misuse Report

#### `GET /api/moderation/misuse-logs?user_id=uuid` [Auth Required, Admin]

---

## 5. WEBSOCKET EVENTS (Mở rộng)

### 5.1 Sự kiện Client → Server (Mới)

| Sự kiện | Payload | Mô tả |
|-------|---------|-------------|
| `ask_expert` | `{"query": "Kubernetes là gì?", "tag": "devops"}` | Hỏi AI Expert |
| `request_tts` | `{"correction_id": "uuid", "text": "..."}` | Yêu cầu phát âm TTS |
| `video_frame_capture` | `{"frame": "<base64 jpeg>"}` | Gửi frame để NSFW scan |
| `report_agent_misuse` | `{"message_id": "uuid"}` | Báo cáo agent từ chối sai |

### 5.2 Sự kiện Server → Client (Mới)

| Sự kiện | Payload | Mô tả |
|-------|---------|-------------|
| `ai_expert_response` | `{"query": "...", "answer": "...", "sources": [...], "confidence": 0.9}` | Expert trả lời |
| `tts_audio_ready` | `{"correction_id": "uuid", "audio_url": "https://...", "duration": 3.5}` | TTS sẵn sàng |
| `sensitive_content_alert` | `{"user_id": "...", "reason": "nsfw", "action": "video_off"}` | Cảnh báo NSFW |
| `agent_misuse_warning` | `{"reason": "Chỉ hỗ trợ tiếng Anh + chuyên ngành", "count": 2}` | Cảnh báo lạm dụng |
| `agent_level_changed` | `{"level": "advanced", "reason": "pro_user_joined"}` | Thay đổi cấp agent |
| `note_ready` | `{"session_id": "uuid"}` | Note đã sẵn sàng |
| `request_video_frame` | `{}` | Server yêu cầu frame để scan |
| `tag_suggestions` | `{"tags": [...]}` | Gợi ý tag khi khởi tạo |

---

## 6. RAG ARCHITECTURE (Đã refactor sang LangChain)

> [!tip] Cập nhật 2026-06-02
> Toàn bộ RAG pipeline đã refactor sang LangChain. Không dùng TiDB Cloud. Không dùng pgvector. Chi tiết: [[ERoom/decisions#ADR-016|ADR-016 (đã cập nhật)]].

### 6.1 Dependencies (Actual)

```toml
"langchain>=1.2.2",
"langchain-community>=0.4.1",
"langchain-openai>=1.1.7",
"langchain-text-splitters>=1.1.0",
"langchain-openai>=1.1.7",
```

### 6.2 Vector Store — TiDBRawVectorStore + NumpyVectorStore

**Thực tế**: KHÔNG dùng pgvector. KHÔNG dùng TiDB Cloud Vector. Dùng 2 store:

| Store | Storage | Query | Persistent | Notes |
|-------|---------|-------|-----------|-------|
| `TiDBRawVectorStore` | MySQL table `rag_embeddings` | Brute-force cosine (load all → numpy → sort) | ✅ | LONGBLOB pickle numpy array |
| `NumpyVectorStore` | In-memory dict | Brute-force cosine | ❌ Mất khi restart | Fallback khi MySQL down |

**TiDBRawVectorStore schema**: Cột `id` (VARCHAR 64 PK), `text` (TEXT), `meta` (JSON), `embedding` (LONGBLOB — pickle numpy array)

**VectorStore wrapper**: `app/rag/vector_store.py:VectorStore` — tự động thử TiDBRawVectorStore đầu tiên, fallback sang NumpyVectorStore nếu lỗi.

```python
# app/rag/vector_store.py
class TiDBRawVectorStore:
    def similarity_search_by_vector(self, query_vector, k=10, filter=None):
        # SELECT * FROM rag_embeddings
        # Pickle.load → np.array từng row
        # np.dot / np.linalg.norm → cosine similarity
        # Sort → return top-k

class NumpyVectorStore:
    def store_embeddings(self, items): ...  # dict in-memory

class VectorStore:
    # Wrapper: thử TiDBRawVectorStore → fallback NumpyVectorStore
```

### 6.3 Pipeline Nạp Knowledge

```
Document Upload → Minio (ERoom-rag-docs/{tag_slug}/)
    │
    ▼
Background Task: index_document(doc_id)
    ├─ Parse (PyPDF2 / markdown parser)
    ├─ Chunk (TextChunker: RecursiveCharacterTextSplitter, 512 chars, overlap 64)
    ├─ Embed (EmbeddingService: OpenAIEmbeddings via LM Studio)
    │  └─ Cache: dict (in-memory) + Redis (TTL 24h)
    └─ Store (TiDBRawVectorStore / NumpyVectorStore)
```

### 6.4 Pipeline Query (Expert Q&A)

```
User hỏi: "Kubernetes là gì?"
    │
    ▼
Agent.query.build_query() → phân loại intent (regex)
    │ (nếu expert pattern)
    ▼
EmbeddingService.embed(query) → 768-dim vector
    │
    ├─ TiDBRawVectorStore.search() → top-5 chunks (cosine)
    │   └─ RetrievalService (vector + keyword hybrid)
    │       └─ Dedup by first 100 chars
    │
    ├─ Brave Search API (nếu Pro+) → top-3 results
    │   └─ Cache Redis (TTL 1h)
    │
    ▼
Combine: RAG chunks + Web Search results
    │
    ▼
agent.expert.answer_expert() → LLM (local) → answer
    │
    ▼
WebSocket: ai_expert_response (via Redis PubSub)
```

### 6.5 Pronunciation Pipeline (thực tế)

> [!warning] Tài liệu này mô tả kiến trúc **mục tiêu** cũ (FunASR + Wav2Vec2 + GOP).
> Code thực tế dùng **faster-whisper small.en** + CMU Dictionary + confidence scoring.
> Xem [[pronunciation-workflow]] và [[workflow#3. Luồng Dữ liệu Âm thanh]] cho phiên bản cập nhật.

```
Audio PCM (16kHz, mono, int16)
    │
    ├─► faster-whisper small.en (CUDA)
    │   └─ segments, text, avg_logprob
    │
    ├─► CMU Dictionary (ARPAbet)
    │   └─ lookup(word) → expected phonemes
    │
    ▼
Confidence scoring
    ├─ scale: min(max((avg_logprob+2)/4, 0.1), 1.0)
    ├─ word_score: probability × 100
    └─ overall: mean of word scores
    │
    ▼
Output: {text, scores: {overall, words: [{word, score, phonemes}]}, needs_remediation}
    │
    ▼
Nếu overall < 70 → LLM correction (agent.corrector.correct_text)
Nếu overall >= 70 → chỉ lưu transcript, bỏ qua correction
```

---

## 7. NSFW DETECTION PIPELINE

```
Background task: Mỗi 8-10s / phòng ACTIVE
    │
    ▼
Với mỗi participant đang bật video:
    │
    ├─► WebSocket: request_video_frame → client
    │
    ├─► Client gửi: video_frame_capture (JPEG 320x240)
    │
    ├─► NSFW Detector: score = model.predict(frame)
    │
    └─► Nếu score > 0.85:
         ├─ Lần 1: action = video_off + warning
         ├─ Lần 2: action = video_off + strike
         └─ Lần 3: action = ban_24h
```

---

## 8. SUBSCRIPTION QUOTA ENFORCEMENT (Actual)

```python
# app/service/room.py — resolve_agent_level
def resolve_agent_level(subscription_service, user_id: str) -> str:
    sub = subscription_service.get_subscription(user_id)
    if sub is None:
        return "basic"
    tier = sub.tier.lower()
    if tier == "pro_plus":
        return "full"
    elif tier == "pro":
        return "advanced"
    return "basic"

# app/service/subscription.py — SubscriptionService
class SubscriptionService:
    def get_subscription(self, user_id):
        return self.get_one(user_id=user_id)
    
    def get_room_agent_level(self, room_id, participant_ids):
        tiers = [self.get_subscription(uid) for uid in participant_ids]
        tier_names = [s.tier if s else "free" for s in tiers]
        if "pro_plus" in tier_names:
            return "full"
        if "pro" in tier_names:
            return "advanced"
        return "basic"
```

### Actual Agent Level Mapping (từ subscription_store.js)

```javascript
// frontend/src/stores/subscriptionStore.js
const TIER_DEFAULTS = {
  free: { maxRoomsPerDay: 2, agentLevel: "basic" },
  pro: { maxRoomsPerDay: Infinity, agentLevel: "advanced" },
  pro_plus: { maxRoomsPerDay: Infinity, agentLevel: "full" },
};
```

---

## 9. ANTI-MISUSE PROMPT GUARDRAIL

Agent CHỈ được phép trả lời 2 loại câu hỏi:
1. **Luyện tập tiếng Anh** — sửa lỗi, giải thích ngữ pháp, từ vựng
2. **Chuyên ngành trong room** — câu hỏi liên quan đến tag của phòng hiện tại

```
SYSTEM PROMPT GUARDRAIL:

You are an English practice assistant. You ONLY respond to these categories:

ALLOWED — Answer normally:
1. English language questions: corrections, grammar, vocabulary, pronunciation
2. Domain questions about {room_tags}: professional/technical questions related to the room's topic

STRICTLY FORBIDDEN — Politely DECLINE:
- Writing, debugging, or reviewing code
- Personal tasks (emails, reports, scheduling)
- Any question unrelated to English practice OR the room's topic ({room_tags})

DECLINE RESPONSE:
"Xin lỗi, tôi là trợ lý luyện tập tiếng Anh trong phòng {room_tags}. 
Tôi chỉ có thể giúp bạn cải thiện tiếng Anh hoặc trả lời câu hỏi về {room_tags}. 
Bạn muốn thảo luận về chủ đề này không?"
```

---

## 10. MỤC TIÊU HIỆU NĂNG

| Chỉ số | Mục tiêu | Đo lường |
|--------|--------|-------------|
| API response (không AI) | P95 < 200ms | Middleware logging |
| Transcript hiển thị lần đầu | < 1s | WebSocket latency |
| Sửa lỗi AI | P95 < 5s | Async task duration |
| Expert RAG Q&A | P95 < 8s | Async task duration |
| TTS audio generation | P95 < 3s | API + TTS engine |
| Web Search | P95 < 1s | Brave API latency |
| NSFW detection | P95 < 2s | Frame capture → result |
| RAG knowledge loading | < 15s (khởi tạo phòng) | Async task duration |
| Agent loading (Pro+) | < 15s | Room MATCHING→ACTIVE |
| Ghép cặp tag | P95 < 5s | Queue → room created |
| WebSocket events | P95 < 100ms | Publish → client receive |
| Audio/video latency | P95 < 200ms | WebRTC getStats |

---

## 11. BẢO MẬT

| Mối lo | Giảm thiểu (Actual) |
|---------|-----------|
| Đánh cắp JWT | Access token 15 phút, xoay refresh, Redis blacklist (TokenStore) |
| Mật khẩu | Argon2 (argon2-cffi, không còn Passlib) |
| Prompt injection vào Agent | Guardrail prompt + intent classifier (regex) + misuse counter (3 strikes/h) |
| Lạm dụng Agent (coding) | `agent/query.py:build_query()` regex pattern detection + intent classifier |
| Ảnh nhạy cảm video call | ⏳ Chưa implement |
| RAG document poisoning | Chỉ admin upload docs |
| TTS abuse | ⏳ Chưa implement (RateLimiter.check_tts có code) |
| Minio data leak | Presigned URLs, lifecycle rules (TTL audio 1d, evidence 30d) |
| WebSocket hijack | JWT auth on connect (query param `token` or Authorization header) |
| Rate limiting | `RateLimiter`: login 5/IP/15ph, TTS 10/user/h |

### Actual Auth Chain (dependencies.py)

```
get_current_user
  └─ get_token
       ├─ _extract_access_token (cookie / Authorization header)
       ├─ _check_blacklist (Redis TokenStore)
       └─ _validate_payload (JWT decode + sub + exp)
            └─ _check_user_banned (raw SQL: is_banned, strikes count)
                 └─ 3 strikes → ban 24h, 5 strikes → permanent
```

---

## 12. TESTING

> [!tip] Xem thêm
> Chi tiết về test structure, kết quả hiện tại, và cách chạy: **[[ERoom/dev-notes|Dev Notes]]**.

### 12.1 Cấu trúc Test

```
backend/tests/
├── conftest.py                       # Shared fixtures (DB, client, factories)
├── test_edge_cases.py                # Unicode, XSS, SQL injection (4 pass)
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

### 12.2 Kết quả Hiện tại: 142/147 Pass (97%)

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

### 12.3 Chạy Test

```bash
cd backend
uv run python -m pytest tests/ -v --tb=short          # Tất cả
uv run python -m pytest tests/test_unit/ -v            # Unit only
uv run python -m pytest tests/test_integration/ -v     # Integration only
uv run python -m pytest tests/ --cov=app --cov-report=term-missing  # Coverage
```

---

## Liên quan

- [[ERoom/decisions|Quyết định kiến trúc]] — ADR-003 (MySQL+Redis), ADR-012 (Minio), ADR-013 (TTS), ADR-014 (Web Search), ADR-015 (NSFW), ADR-016 (RAG), ADR-021 (Local DB)
- [[ERoom/overview|Tổng quan]] — Sơ đồ kiến trúc, cấu hình cổng, biến môi trường
- [[ERoom/features|Tính năng]] — 26 đặc tả tính năng
- [[ERoom/workflow|Luồng hoạt động]] — Luồng người dùng tiêu thụ các API này
- [[ERoom/tasks|Công việc]] — Kế hoạch triển khai tham chiếu schema và contracts

