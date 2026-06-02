---
title: ERoom — Quyết định kiến trúc
tags:
  - decisions
  - architecture
  - ERoom
  - adr
created: 2026-05-07
updated: 2026-06-02
---

# Hồ sơ Quyết định Kiến trúc

> [!abstract] Danh mục ADR
> Mỗi quyết định được ghi lại với **Bối cảnh**, **Quyết định**, **Hệ quả**, và **Phương án đã cân nhắc**. ADR mới (012-016) cho các công nghệ: Minio, TTS, Web Search, NSFW Detection, RAG Architecture.

> [!info] Điều hướng nhanh
> [[ERoom/overview|← Tổng quan]] · [[ERoom/features|← Tính năng]] · [[ERoom/workflow|← Luồng hoạt động]] · [[ERoom/tasks|← Công việc]] · [[ERoom/notes|← Ghi chú kỹ thuật]] · **Quyết định kiến trúc**

---

## ADR-001: LiveKit cho Video Thời gian thực

**Trạng thái:** ✅ Đã chấp nhận | **Ngày:** 2026-05-04

### Bối cảnh
ERoom yêu cầu giao tiếp video/âm thanh thời gian thực cho 3-5 người trong môi trường nhóm. Giải pháp phải hỗ trợ WebRTC, xử lý NAT traversal, và mở rộng lên hàng trăm phòng đồng thời.

### Quyết định
Dùng **LiveKit** (SFU tự host) làm máy chủ media thời gian thực.

### Hệ quả
- Mã nguồn mở, SFU architecture, SDK đa nền tảng
- Quản lý phòng + token auth + WebHooks tích hợp sẵn
- Cần TURN server (coTURN) riêng cho NAT traversal

### Phương án đã cân nhắc
| Phương án | Lý do từ chối |
|-------------|-------------|
| Agora | Độc quyền, đắt, vendor lock-in |
| Jitsi | Khó tùy chỉnh, SDK kém trau chuốt |
| Twilio Video | Đã EOL 2024 |
| WebRTC P2P mesh | O(N²) bandwidth |

---

## ADR-002: Whisper cho Chuyển Giọng nói thành Văn bản

**Trạng thái:** ✅ Đã chấp nhận (Đã thay đổi) | **Ngày:** 2026-05-04 | **Cập nhật:** 2026-06-02

### Bối cảnh
Cần STT thời gian thực cho transcript trực tiếp và làm đầu vào cho pipeline sửa lỗi AI. Phải hỗ trợ tiếng Anh chính, độ trễ < 2s.

### Quyết định (Đã thay đổi)
**Chuyển sang faster-whisper local** (model `base`, CPU) thay vì OpenAI Whisper API. Lý do: giảm chi phí, chạy offline, tích hợp sâu với Wav2Vec2 alignment.

### Hệ quả
- **faster-whisper `base`** (~1.5GB) chạy local trên CPU, real-time factor < 1
- Không cần kết nối internet cho STT
- **Tích hợp trong PronunciationPipeline**: Whisper + Wav2Vec2 + CMU Dictionary
- Code: `infrastructure/audio_whisper.py` (model singleton)
- Giai đoạn sau: nâng lên `large-v3` nếu cần accuracy cao hơn

### Cập nhật từ code thực tế
```python
# backend/app/infrastructure/audio_whisper.py
whisper_model = WhisperModel("base", device="cpu", compute_type="default")
```

### Phương án đã cân nhắc
| Phương án | Lý do từ chối |
|-------------|-------------|
| OpenAI Whisper API | Tốn chi phí, phụ thuộc internet |
| Browser Web Speech API | Không nhất quán, không streaming |
| Deepgram | Độc quyền, tiếng Việt kém |

---

## ADR-003: Local MySQL + Redis

**Trạng thái:** ✅ Đã chấp nhận (Đã thay đổi) | **Ngày:** 2026-05-04 | **Cập nhật:** 2026-06-02

### Bối cảnh
Hai nhu cầu dữ liệu: (1) Dữ liệu quan hệ có cấu trúc (users, rooms, sessions, subscriptions), (2) Trạng thái thời gian thực tạm thời (matching queue, room state, rate limits).

### Quyết định (Đã thay đổi)
**Local MySQL** (hoặc MySQL-compatible) làm database chính + **Redis** (thời gian thực). Vector search dùng **NumpyVectorStore** in-memory hoặc MySQL table với brute-force cosine.

### Hệ quả
- **Local MySQL**: ACID, JSON, free, không dependency cloud
- **Redis**: sub-ms latency, sorted sets cho matching, pub/sub cho service communication
- **Vector search**: NumpyVectorStore (in-memory, mất khi restart) hoặc MySQL table `rag_embeddings` với pickle numpy array + brute-force cosine
- Không cần kết nối internet cho database
- Dễ dàng switch sang PostgreSQL/TiDB Cloud sau nếu cần

---

## ADR-004: FastAPI

**Trạng thái:** ✅ Đã chấp nhận | **Ngày:** 2026-05-04

### Quyết định
**FastAPI** làm backend framework.

### Hệ quả
- Async-first (asyncio), auto OpenAPI docs, Pydantic v2
- Tích hợp AI/ML tự nhiên (Whisper, LLM, SentenceTransformer)
- WebSocket tích hợp sẵn, Celery cho tác vụ nền

---

## ADR-005: React + Vite + React Router

**Trạng thái:** ✅ Đã chấp nhận | **Ngày:** 2026-05-04 | **Cập nhật:** 2026-05-07

### Bối cảnh
Frontend cần: SPA client-side rendering, tích hợp LiveKit WebRTC (client-side only), routing phía client. Không cần SSR/SSG cho ứng dụng real-time.

### Quyết định
**React 18+** với **Vite** (build tool) và **React Router v6+** (client-side routing). **TypeScript**, **TailwindCSS**, **shadcn/ui**.

### Hệ quả
- Vite: HMR cực nhanh, build nhanh, deploy tĩnh đơn giản (Nginx serve static)
- React Router: nested routes, loaders, client-side navigation
- Tất cả component LiveKit là client-side tự nhiên, không cần 'use client' directive
- Zustand + React Query cho state management
- i18next cho đa ngôn ngữ (en + vi)

---

## ADR-006: Local LLM (LM Studio) cho Sửa lỗi/Đánh giá/Nhịp tim

**Trạng thái:** ✅ Đã chấp nhận (Đã thay đổi) | **Ngày:** 2026-05-04 | **Cập nhật:** 2026-06-02

### Bối cảnh
Ba use case LLM riêng biệt: (1) Sửa lỗi — nhanh, JSON có cấu trúc, (2) Đánh giá — đầu vào dài, (3) Nhịp tim — rất nhanh, độ phức tạp thấp. Thêm use case mới: (4) Expert RAG Q&A, (5) Intent classifier chống lạm dụng.

### Quyết định (Đã thay đổi)
**Đã chuyển sang local LLM qua LM Studio** (OpenAI-compatible endpoint). Model: `google/gemma-4-e2b` tại `http://127.0.0.1:1234/v1`. Lý do: miễn phí, không dependency OpenAI, privacy.

### Hệ quả
- **Chi phí $0** cho LLM inference (chạy local)
- **OpenAI-compatible API**: Dùng `ChatOpenAI` từ langchain-openai với `base_url` trỏ đến LM Studio
- **Chung 1 model** cho mọi use case (không phân biệt GPT-4o/GPT-4o-mini)
- Chất lượng thấp hơn GPT-4o nhưng đủ cho MVP
- Cần GPU (hoặc CPU mạnh) để chạy model local
- Có thể switch sang OpenAI/Gemini API bất kỳ lúc nào (chỉ cần đổi `llm_base_url` + `llm_model` trong config)

### Config
```python
# backend/app/config.py
llm_base_url: str = "http://127.0.0.1:1234/v1"
llm_model: str = "google/gemma-4-e2b"
llm_api_key: str = "..."  # LM Studio key
```

---

## ADR-007: Nhóm Nhỏ (3-5)

**Trạng thái:** ✅ Đã chấp nhận | **Ngày:** 2026-05-04

### Quyết định
Phòng 3-5 người tham gia. Lý tưởng: 4. Đây là quy mô tối ưu cho luyện tập ngôn ngữ: đủ thời gian nói, đủ năng động, AI điều phối hiệu quả.

---

## ADR-008: Celery cho Xử lý Bất đồng bộ

**Trạng thái:** ✅ Đã chấp nhận | **Ngày:** 2026-05-04

### Quyết định
**Celery** với **Redis** làm broker và result backend.

### Hệ quả
- Hàng đợi ưu tiên, thử lại exponential backoff, Celery Beat cho tác vụ định kỳ
- Celery tasks mới: RAG knowledge loading, TTS generation, NSFW scanning, auto note-taking, intent classification

---

## ADR-009: JWT với Xoay Refresh Token

**Trạng thái:** ✅ Đã chấp nhận | **Ngày:** 2026-05-04

---

## ADR-010: `uv` cho Quản lý Gói Python

**Trạng thái:** ✅ Đã chấp nhận | **Ngày:** 2026-05-04

---

## ADR-011: Zustand cho Quản lý State

**Trạng thái:** ✅ Đã chấp nhận | **Ngày:** 2026-05-04

### Quyết định
**Zustand** cho client state (auth, room, tags, subscription). React Query cho server state.

### Stores mới
- `tag-store`: Quản lý tags đã chọn, tag suggestions, tag cloud
- `subscription-store`: Quản lý tier, quota indicators, upgrade prompts
- `agent-store`: Agent level trong room hiện tại, quota counters

---

## ADR-012: Minio cho RAG Document Storage & Object Storage

**Trạng thái:** ✅ Đã chấp nhận | **Ngày:** 2026-05-07

### Bối cảnh
ERoom cần lưu trữ: (1) Tài liệu RAG cho AI Expert (PDF, markdown, txt), (2) Audio TTS tạm thời, (3) Avatar của AI Agent theo tag, (4) Ảnh evidence từ moderation. Cần giải pháp S3-compatible, tự host được, chi phí thấp.

### Quyết định
Dùng **Minio** (self-hosted S3-compatible object storage) cho tất cả nhu cầu object storage.

### Hệ quả

**Tích cực:**
- S3-compatible API — tích hợp dễ dàng với mọi SDK (boto3, minio-py)
- Tự host — không chi phí bandwidth/storage như AWS S3
- Hỗ trợ bucket policy, presigned URLs (bảo mật truy cập tài liệu RAG)
- Object TTL (auto-expire TTS audio sau 24h)
- Web console để quản lý (port 9001)
- Docker deployment đơn giản, 1 container là đủ cho dev

**Tiêu cực:**
- Thêm 1 service để vận hành (nhưng nhẹ — 1 container, ~100MB RAM)
- Cần backup strategy cho RAG documents (quan trọng)
- Không có CDN tích hợp (cần thêm CloudFront/CDN nếu scale lớn)

### Phương án đã cân nhắc
| Phương án | Lý do từ chối |
|-------------|-------------|
| AWS S3 | Tốt nhưng chi phí bandwidth + storage, không cần cho MVP |
| Local filesystem | Không scale, không S3 API, khó backup |
| Cloudflare R2 | Tốt nhưng vẫn là dịch vụ bên ngoài, phụ thuộc internet |
| Supabase Storage | Tốt nếu đã dùng Supabase, nhưng giới hạn free tier |

### Cấu trúc Bucket
| Bucket | Mục đích | TTL |
|--------|----------|-----|
| `ERoom-rag-docs` | Tài liệu RAG theo tag | Vĩnh viễn |
| `ERoom-tts` | Audio TTS | 24h |
| `ERoom-avatars` | Avatar agent | Vĩnh viễn |
| `ERoom-evidence` | Ảnh moderation | 30 ngày |

**Tính năng bị ảnh hưởng:** [[ERoom/features#F-AI-02|F-AI-02 (Expert RAG)]], [[ERoom/features#F-AI-04|F-AI-04 (TTS)]], [[ERoom/features#F-MOD-01|F-MOD-01 (NSFW)]]

---

## ADR-013: OpenAI TTS cho Text-to-Speech Phát âm

**Trạng thái:** ✅ Đã chấp nhận | **Ngày:** 2026-05-07

### Bối cảnh
Tính năng TTS cho phép người dùng Pro+ nghe phát âm chuẩn của từ/câu đã được AI sửa lỗi. Yêu cầu: giọng tự nhiên, hỗ trợ tiếng Anh (chính) + tiếng Việt (phụ), độ trễ < 3s, chi phí hợp lý.

### Quyết định
**OpenAI TTS API** (`tts-1` model, `alloy` voice) cho Giai đoạn 3. Đánh giá **ElevenLabs Multilingual v2** làm alternative nếu cần chất lượng cao hơn.

### Hệ quả

**Tích cực:**
- Tích hợp đơn giản — cùng API key với Whisper + LLM
- 6 giọng có sẵn, giọng `alloy` tự nhiên cho phát âm
- Định dạng MP3/Opus, streaming support
- $0.015/1K characters — rẻ cho use case phát âm từng câu (~$0.001/correction)
- Hỗ trợ tiếng Anh xuất sắc, tiếng Việt khá

**Tiêu cực:**
- Tiếng Việt phát âm chưa hoàn hảo như ElevenLabs
- Không tùy chỉnh được voice cloning
- Cache required để tránh generate lại cùng 1 text (tốn chi phí)

### Phương án đã cân nhắc
| Phương án | Lý do từ chối |
|-------------|-------------|
| ElevenLabs | Chất lượng cao nhất, voice cloning, nhưng đắt hơn ($0.30/1K chars ≈ 20x OpenAI) |
| Browser Web Speech API | Miễn phí nhưng không nhất quán giữa browser, giọng robotic |
| Coqui AI (tự host) | Miễn phí, privacy tốt, nhưng cần GPU + setup phức tạp |
| Google Cloud TTS | Tốt, nhưng thêm 1 provider phụ thuộc |

### Chiến lược cache
- Redis cache key: `ERoom:cache:tts:{sha256(text+lang)}` TTL 24h
- Audio lưu trong Minio `ERoom-tts` TTL 24h
- Với cùng 1 câu sửa lỗi → dùng lại audio đã generate

**Tính năng bị ảnh hưởng:** [[ERoom/features#F-AI-04|F-AI-04 (TTS Phát âm)]]

---

## ADR-014: Brave Search API cho Web Search

**Trạng thái:** ✅ Đã chấp nhận | **Ngày:** 2026-05-07

### Bối cảnh
AI Agent cần khả năng tìm kiếm web thời gian thực để trả lời câu hỏi chuyên môn với kiến thức up-to-date. Yêu cầu: API đơn giản, chi phí thấp, kết quả chất lượng.

### Quyết định
**Brave Search API** cho web search trong RAG Expert pipeline.

### Hệ quả

**Tích cực:**
- Independent search index (không phụ thuộc Google)
- API đơn giản, REST, JSON response
- Free tier: 2,000 queries/tháng. Pro: $5/1,000 queries
- Hỗ trợ freshness filter, language filter
- Privacy-respecting (Brave không track)
- Đủ cho use case tìm kiếm context chuyên môn

**Tiêu cực:**
- Index nhỏ hơn Google (nhưng đủ cho technical topics)
- Không hỗ trợ tiếng Việt tốt bằng Google
- Cần cache để tránh query trùng lặp

### Phương án đã cân nhắc
| Phương án | Lý do từ chối |
|-------------|-------------|
| Google Custom Search API | $5/1K queries nhưng index lớn hơn. Phụ thuộc Google |
| SerpAPI | Tốt nhưng đắt hơn ($50/tháng minimum) |
| Bing Search API | Tốt, nhưng phức tạp hơn về auth |
| DuckDuckGo Instant Answer | Miễn phí nhưng không có API chính thức, dễ bị block |

### Chiến lược cache
- Redis: `ERoom:cache:websearch:{sha256(query)}` TTL 1h
- Kết quả tìm kiếm ít thay đổi trong ngắn hạn → cache giảm 80%+ API calls

**Tính năng bị ảnh hưởng:** [[ERoom/features#F-AI-02|F-AI-02 (Expert)]]

---

## ADR-015: NSFW Detector cho Kiểm duyệt Ảnh

**Trạng thái:** ✅ Đã chấp nhận | **Ngày:** 2026-05-07

### Bối cảnh
Khi người dùng bật video call 3-5 người, cần phát hiện ảnh nhạy cảm (NSFW) để bảo vệ trải nghiệm cộng đồng. Yêu cầu: độ chính xác cao, độ trễ thấp (< 2s), privacy-respecting (ưu tiên xử lý local).

### Quyết định
**Tự host NSFW Detector** (TensorFlow/Keras `nsfw_detector` model) làm primary. **Google Vision SafeSearch API** làm fallback nếu model local không khả dụng.

### Hệ quả

**Tích cực:**
- Tự host → privacy (ảnh không rời khỏi server)
- Model nhẹ, chạy trên CPU (không cần GPU)
- Độ chính xác > 95% cho nội dung rõ ràng
- Không chi phí API
- Có thể fine-tune nếu cần

**Tiêu cực:**
- Cần tải model (~50MB) khi khởi động worker
- False positive có thể xảy ra (ảnh bình thường bị gắn cờ)
- Không phát hiện được nội dung tinh vi (cần review thủ công)
- Chỉ hoạt động trên ảnh, không phát hiện trên video stream (cần chụp frame)

### Phương án đã cân nhắc
| Phương án | Lý do từ chối |
|-------------|-------------|
| Google Vision SafeSearch | Chính xác cao nhưng gửi ảnh ra ngoài (privacy), chi phí $1.50/1K images |
| Amazon Rekognition | Tương tự Google Vision, vendor lock-in AWS |
| Sightengine API | Tốt nhưng đắt ($79/tháng minimum) |
| Không có moderation | Rủi ro quá cao — bắt buộc với video call public |

### Chiến lược 3-strike
- **Lần 1:** Cảnh báo + tắt video
- **Lần 2:** Tắt video + ghi strike vào DB
- **Lần 3:** Tự động ban 24h
- Tất cả sự kiện lưu vào `moderation_events` với evidence

**Tính năng bị ảnh hưởng:** [[ERoom/features#F-MOD-01|F-MOD-01 (Ảnh nhạy cảm)]], [[ERoom/features#F-MOD-03|F-MOD-03 (Strike)]]

---

## ADR-016: RAG Architecture — TiDBRawVectorStore + LangChain

**Trạng thái:** ✅ Đã chấp nhận (Đã thay đổi) | **Ngày:** 2026-05-07 | **Cập nhật:** 2026-06-02

### Bối cảnh
AI Expert trong phòng cần nạp kiến thức chuyên ngành từ tài liệu. Yêu cầu: (1) Lưu trữ document theo tag, (2) Index + embed tự động, (3) Query nhanh (< 1s cho vector search), (4) Kết hợp với Web Search context, (5) Tái sử dụng hạ tầng có sẵn.

### Quyết định (Đã thay đổi)
Dùng **TiDBRawVectorStore** (MySQL table `rag_embeddings` với pickle numpy array) hoặc **NumpyVectorStore** (in-memory) làm vector store + **LangChain** cho document processing pipeline (chunking, embedding). Không dùng vector database riêng (Pinecone, Weaviate, Qdrant, pgvector).

### Hệ quả

**Tích cực:**
- **Không cần vector database riêng** — dùng MySQL table có sẵn
- Pickle numpy array trong MySQL LONGBLOB → brute-force cosine similarity
- Fallback NumpyVectorStore khi MySQL không khả dụng
- LangChain document loaders hỗ trợ PDF, Markdown, TXT, HTML
- Query: embed → load all → numpy cosine → sort → top-k

**Tiêu cực:**
- **Brute-force cosine**: load ALL rows → tính numpy → sort → O(n). Chậm khi > 10K chunks
- Không có ANN index (ivfflat, HNSW) — brute-force thuần
- Pickle numpy array không phải format chuẩn cho vector DB
- NumpyVectorStore mất data khi restart
- LangChain hơi nặng, nhưng document processing chỉ chạy khi upload

### Phương án đã cân nhắc
| Phương án | Lý do từ chối |
|-------------|-------------|
| Pinecone | Thêm infrastructure + cost ($70/tháng minimum) |
| pgvector | Cần PostgreSQL — không dùng PostgreSQL |
| Weaviate / Qdrant | Nặng, overkill cho MVP |
| FAISS (in-memory) | Nhanh nhưng không persistent |

### Cập nhật — LangChain Refactoring

**Đã refactor toàn bộ RAG pipeline sang LangChain:**
- **Chunking**: `RecursiveCharacterTextSplitter` (500 chars, overlap 50)
- **Embedding**: Nomic API (768-dim), không dùng OpenAI embeddings
- **Vector Store**: `TiDBRawVectorStore` (custom, không phải langchain built-in)
- **Retrieval**: Vector search + Web Search (Brave) combine
- **Agent**: Dùng `call_llm_json`/`call_llm_text` trực tiếp, không dùng `create_agent`

### Kiến trúc RAG (thực tế)
```
Document Upload (Minio)
    │
    ▼
Celery Task: index_document()
    │
    ├─ Parse (PyPDF2 / markdown parser)
    ├─ Chunk (RecursiveCharacterTextSplitter, 500 chars, overlap 50)
    ├─ Embed (Nomic API, 768-dim, cached 24h trong Redis)
    └─ Store (rag_embeddings table → TiDBRawVectorStore / NumpyVectorStore)

Query Time:
    │
    ├─ Embed query (Nomic)
    ├─ Vector search (TiDBRawVectorStore, brute-force cosine, top-5)
    ├─ Web Search (Brave API, top-3)
    ├─ Combine context
    └─ LLM answer (call_llm_json trực tiếp)
```

**Tính năng bị ảnh hưởng:** [[ERoom/features#F-AI-02|F-AI-02 (Expert RAG)]]

---

## ADR-017: TiDB Cloud → Local MySQL (Đã hủy)

**Trạng thái:** ❌ Đã hủy — thay bằng ADR-021 | **Ngày:** 2026-05-08 | **Cập nhật:** 2026-06-02

### Quyết định gốc (đã hủy)
Dùng **TiDB Cloud** (MySQL-compatible, serverless) làm database chính.

### Lý do hủy
- Cần dependency internet cho database
- Free tier TiDB Cloud có giới hạn (5GB storage, limited row count)
- Latency 50-100ms đến Singapore ảnh hưởng dev experience
- Cần connection string phức tạp, SSL config rắc rối
- Vector search không tự nhiên trên TiDB Cloud (pickle numpy brute-force)

### Thay thế
Chuyển sang **Local MySQL** — xem [[#ADR-021|ADR-021]].

**Tính năng bị ảnh hưởng:** [[ERoom/features#F-AI-05|F-AI-05 (RAG)]], toàn bộ database schema

---

---

## ADR-018: Pronunciation Pipeline — Whisper + Wav2Vec2 + CMU Dictionary

**Trạng thái:** ✅ Đã chấp nhận | **Ngày:** 2026-06-02

### Bối cảnh
ERoom cần chấm điểm phát âm thời gian thực cho người học tiếng Anh. Yêu cầu: accuracy phoneme-level, độ trễ < 5s, chạy local (không gọi API), không cần GPU.

### Quyết định
**Xây dựng PronunciationPipeline local** với 3 thành phần song song:
1. **faster-whisper `base`** (CPU) — ASR → transcript + word confidence
2. **Wav2Vec2-BASE-960h** (CPU) — forced alignment Viterbi → phoneme-level alignment
3. **CMU Dictionary** (ARPAbet) — lookup expected phonemes
4. **PronunciationScorer** — 4 chỉ số: Accuracy (40%), GOP (20%), Fluency (25%), Prosody (15%)

### Hệ quả

**Tích cực:**
- Chạy hoàn toàn local, không chi phí API
- Phoneme-level scoring: phát hiện chính xác từ nào sai âm nào
- GOP (Goodness of Pronunciation) cho mỗi phoneme riêng
- Graceful degradation: Whisper fail → Wav2Vec2 vẫn chạy, và ngược lại
- Tích hợp trong pipeline `ws/speech.py:process_speech()` — synchronous nhưng non-blocking (ThreadPoolExecutor)

**Tiêu cực:**
- Cần tải 2 model (~2.7GB tổng) lần đầu: faster-whisper base + Wav2Vec2
- Wav2Vec2 alignment ~1.5-3s trên CPU cho 3s audio
- Độ chính xác phoneme phụ thuộc vào Wav2Vec2 (base model, có thể fine-tune)
- CMU Dictionary chỉ hỗ trợ tiếng Anh Mỹ

### Files triển khai
- `infrastructure/audio_whisper.py` — WhisperModel singleton
- `infrastructure/audio_wav2vec2.py` — Aligner class (Viterbi forced alignment)
- `infrastructure/audio_dictionary.py` — CMU Dictionary lookup
- `infrastructure/audio_scorer.py` — PronunciationScorer (4 metrics)
- `infrastructure/audio_pipeline.py` — PronunciationPipeline (orchestrator)
- `infrastructure/phoneme_compare.py` — PhonemeComparator

### Scoring Formula
```
PronScore = AccuracyScore × 0.40 + GOP × 0.20 + FluencyScore × 0.25 + Prosody × 0.15
AccuracyScore = 100 × max(0, 1 - edit_distance/total_phonemes)
GOP = log(P(p|audio) / max P(q≠p|audio))  — threshold: -0.1
FluencyScore = 100 - abs(silence_ratio - 0.10) × 300
```

---

## ADR-019: Frontend — Bootstrap 5 thay vì TailwindCSS/shadcn

**Trạng thái:** ✅ Đã chấp nhận | **Ngày:** 2026-06-02

### Bối cảnh
Doc thiết kế chọn TailwindCSS + shadcn/ui. Code thực tế dùng Bootstrap 5 + react-bootstrap.

### Quyết định
**Bootstrap 5 + react-bootstrap**. Lý do: familiarity, component library có sẵn (modal, toast, card, navbar), không cần build-time CSS pipeline phức tạp.

### Hệ quả
- CSS framework hoàn chỉnh, responsive grid
- Component library: Modal, Toast, Card, Navbar, Badge, Spinner...
- react-bootstrap: React-native Bootstrap components
- Không cần PostCSS config, purging
- i18next cho đa ngôn ngữ, react-markdown cho note rendering

---

## ADR-020: JavaScript thay vì TypeScript cho Frontend

**Trạng thái:** ✅ Đã chấp nhận | **Ngày:** 2026-06-02

### Bối cảnh
Doc thiết kế chọn TypeScript. Code thực tế dùng JavaScript (JSX).

### Quyết định
**JavaScript (JSX)** với Vite 6 + vitest. Lý do: phát triển nhanh hơn, phù hợp MVP. Có thể thêm TypeScript sau.

---

## ADR-021: Local MySQL Database

**Trạng thái:** ✅ Đã chấp nhận | **Ngày:** 2026-06-02

### Bối cảnh
ERoom cần database cho toàn bộ dữ liệu quan hệ (users, rooms, sessions, messages, subscriptions, tags). Yêu cầu: (1) ACID, (2) Không dependency cloud, (3) Dễ setup cho dev, (4) MySQL-compatible với SQLModel/PyMySQL, (5) Chi phí $0.

### Quyết định
**Local MySQL** (hoặc MySQL-compatible) làm database chính thay vì TiDB Cloud. Cụ thể:
- **Dev**: MySQL local (Docker container hoặc XAMPP/WAMP)
- **Test**: SQLite (`sqlite:///./test_eroom.db`) — tự động trong pytest
- **Vector search**: `TiDBRawVectorStore` (MySQL table `rag_embeddings`, pickle numpy array, brute-force cosine) + `NumpyVectorStore` fallback

### Hệ quả

**Tích cực:**
- **$0 chi phí** — chạy local, không cloud bill
- Không cần internet, không latency mạng
- MySQL-compatible — dùng `mysql+pymysql://` driver, SQLModel
- Đơn giản: chỉ cài MySQL là chạy được
- Test tự động dùng SQLite, không cần MySQL cho CI

**Tiêu cực:**
- Cần tự quản lý backup (không có auto point-in-recovery như TiDB Cloud)
- Không auto-scale — phải tự nâng cấp khi cần
- Cài đặt MySQL thủ công cho dev
- Vector search brute-force: O(n) trên toàn bộ rows, không có ANN index
- NumpyVectorStore fallback mất data khi restart

### Config

```env
# Dev: MySQL local
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/eroom

# Test: tự động dùng SQLite trong pytest
# conftest.py: TEST_DATABASE_URL = "sqlite:///./test_eroom.db"
```

### Phương án đã cân nhắc

| Phương án | Lý do từ chối |
|-------------|-------------|
| TiDB Cloud | Cần internet, latency, giới hạn free tier |
| PostgreSQL + pgvector | Tốt nhưng cần setup khác MySQL, thêm 1 infra cho vector |
| SQLite production | Không hỗ trợ concurrent writes, không production-ready |
| Supabase / PlanetScale | Vendor lock-in, giới hạn free tier |

### Files triển khai
- `backend/app/config.py`: `database_url` + `db_url` property (MySQL URL)
- `backend/app/database.py`: `SQLModel.create_engine(database_url)`
- `backend/app/rag/vector_store.py`: `TiDBRawVectorStore` + `NumpyVectorStore` fallback
- `backend/app/alembic/`: Migration scripts (MySQL dialect)
- `backend/tests/conftest.py`: SQLite auto setup

---

## Dòng thời gian Quyết định

```mermaid
timeline
    title Quyết định Kiến trúc ERoom
    2026-05-04 : ADR-001 LiveKit
               : ADR-002 Whisper (API→Local)
               : ADR-003 MySQL+Redis
               : ADR-004 FastAPI
               : ADR-005 React+Vite
               : ADR-006 GPT-4o→Local LLM
               : ADR-007 Nhóm Nhỏ
               : ADR-008 Celery
               : ADR-009 JWT Auth
               : ADR-010 uv
               : ADR-011 Zustand
    2026-05-07 : ADR-012 Minio
               : ADR-013 TTS (OpenAI→Pending)
               : ADR-014 Web Search (Brave)
               : ADR-015 NSFW Detector
               : ADR-016 RAG (TiDBRawVectorStore + LangChain)
    2026-05-08 : ADR-017 TiDB Cloud (Đã hủy 06-02)
    2026-06-02 : ADR-018 Pronunciation Pipeline
               : ADR-019 Bootstrap 5
               : ADR-020 JavaScript (JSX)
               : ADR-021 Local MySQL (thay TiDB Cloud)
```

---

## Liên quan

- [[ERoom/features|Tính năng]] — Tính năng bị ảnh hưởng bởi các quyết định này
- [[ERoom/notes|Ghi chú kỹ thuật]] — Chi tiết triển khai (DB schemas, API, Redis, Minio, RAG pipeline)
- [[ERoom/workflow|Luồng hoạt động]] — Luồng phụ thuộc vào các lựa chọn kiến trúc
- [[ERoom/tasks|Công việc]] — Kế hoạch triển khai tuân theo kiến trúc này
- [[ERoom/overview|Tổng quan]] — Tóm tắt & sơ đồ kiến trúc

