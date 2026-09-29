# PLAN — Refactor lớn: tách lớp Backend E-Room (nhánh `refactor/clean-architecture`)

> Trạng thái: ĐÃ DUYỆT — đang thực hiện. Quyết định đã chốt:
> lỗi trả `{code, detail}`; đổi hết HTTPException sang domain errors;
> helper nằm ở `helpers.py` mỗi package.

## 1. Vấn đề hiện tại (đã khảo sát)

- `app/ai/` phẳng 20 file, `pronunciation.py` 1484 dòng (God-file), khó tìm, khó test lẻ.
- `app/services/*` thực chất là CRUD (`room.py` 29 dòng, `notification.py` 6 dòng),
  trong khi business logic nằm rải trong routers (`session.py` chạm DB trực tiếp 16 chỗ,
  `room.py`/`speech.py`/`message.py` cũng có) và `app/ai/tasks.py` (466 dòng, hub nhập
  từ services + models + integration).
- Routers import thẳng `app.ai.tasks` (room/message/speech) và `get_agent` — vi phạm
  tầng: api phải chỉ gọi service.
- `ai/observer.py`, `ai/transcriber.py` import ngược `ai.tasks` — nguy cơ circular import.
- Celery tasks nằm trong `ai/`, nhập nhằng giữa "khả năng AI" và "job nền".
- Chưa có `shared/` — constants/types dùng chung dễ gây import vòng khi tách.

## 2. Mục tiêu

- Tầng rõ: `routers` (điều phối) → `services` (business logic) → `repositories` (CRUD/query).
- `ai/` chia package theo năng lực: `llm`, `rag`, `stt`, `tts`, `vad`, `pronunciation`.
- `tasks/` cùng cấp `ai/` chứa Celery jobs; routers enqueue qua service, không import `ai` trực tiếp.
- Thêm `shared/` cho constants/types/enums/exceptions chung, hết circular import.
- File dài (>~300 dòng hoặc đa trách nhiệm) chẻ thành package nhiều file con + `helpers.py` mỗi nơi.
- Không đổi API, DB schema, hành vi. Mỗi phase test xanh mới sang phase tiếp.

## 3. Cấu trúc đích

```text
backend/app/
├── api/routers/        # validate -> service -> response_model, KHÔNG chạm DB
├── services/           # BUSINESS LOGIC (orchestrate repos + ai + tasks)
├── repositories/       # MỚI: CRUD + query (chuyển từ services/* hiện tại)
├── models/             # ORM giữ nguyên
├── schemas/            # Pydantic giữ nguyên
├── ai/
│   ├── llm/            # get_llm/get_agent, prompt, query, tools, participant, observer
│   ├── rag/            # chunking, dense, sparse, reranker, retrieval, vector_store
│   ├── stt/            # stt, transcriber, raw_recorder
│   ├── tts/            # tts
│   ├── vad/            # audio_vad
│   └── pronunciation/  # pronunciation (tách nhỏ), articulation, speech_log
├── tasks/              # MỚI: celery jobs (scoring, room_jobs, maintenance, helpers)
├── shared/             # MỚI: constants, types, enums, exceptions chung
├── integration/        # celery/livekit/minio/redis giữ nguyên (celery.py trỏ tasks mới)
└── utils/              # giữ nguyên
```

## 4. Các phase (mỗi phase = commit nhỏ, test xanh)

- **P0. Baseline:** ghi nhận pytest + vitest + ruff hiện tại; khóa lại để so sánh.
- **P1. `repositories/` + `shared/`:** chuyển CRUD từ `services/*.py` sang
  `repositories/*.py`; `services/*` giữ re-export để code cũ chạy.
  `shared/exceptions.py`: `AppException(status_code, code, detail)` + lỗi domain
  (`RoomNotFoundError`, `SessionNotFoundError`, `NotAuthorizedError`,
  `AIServiceUnavailableError`...) + đăng ký handler trong `main.py` trả
  `{code, detail}`; `shared/constants.py`, `shared/types.py` khi cần chống import vòng.
  Test xanh.
- **P2. Business về `services/` + đổi exception hết:** dọn DB-trực-tiếp khỏi routers
  theo thứ tự `session.py` (16 chỗ) → `room.py` → `speech.py` → còn lại; routers chỉ
  gọi service. Đổi toàn bộ `raise HTTPException` sang domain errors (services raise,
  handler trung tâm chuyển). Mỗi service phình logic phụ thì có `helpers.py` riêng.
  Xóa re-export P1 khi không còn ai dùng.
- **P3. Tách `ai/`:** dọn từng package `vad` → `tts` → `stt` (chẻ `stt.py` thành
  `client.py`/`local.py`) → `rag` → `llm`; mỗi package có `helpers.py` +
  `__init__.py` re-export tên cũ để import cũ không vỡ.
- **P4. `tasks/` ra khỏi `ai/`:** chuyển `ai/tasks.py` → `app/tasks/` (chia
  `scoring.py`, `room_jobs.py`, `maintenance.py`, `helpers.py`);
  `integration/celery.py` và beat schedule trỏ mới; routers enqueue qua `services`,
  cấm import `app.ai` trực tiếp.
- **P5. Tách `pronunciation.py`:** thành package `ai/pronunciation/` theo cụm
  (`g2p.py`, `scorer.py`, `feedback.py`, `audio.py`, `helpers.py`); giữ signature
  hàm public.
- **P6. Dọn + chốt:** xóa re-export tạm, hết circular import, ruff sạch,
  full test, rebuild docker + smoke (health, chat 1 câu, chấm 1 câu, feedback session),
  đồng bộ UI đọc shape lỗi `{code, detail}`.

## 5. Ngoài phạm vi (KHÔNG làm đợt này)

- Không đổi REST API (giữ nguyên endpoint + response 200; chỉ shape lỗi HTTP
  đổi từ `{detail}` sang `{code, detail}` và UI đọc theo), DB schema/migration.
- Không đổi model AI, prompt nội dung, thuật toán chấm điểm.
- Không nâng cấp thư viện.

## 5b. Quy tắc style áp dụng xuyên suốt (khi chạm file + quét cuối P6)

- Khối logic cách nhau 1 dòng trống, early return, hàm >~50 dòng tách hàm con.
- Comment chỉ khi cần — dạng step-comment tiếng Việt CÓ DẤU theo từng bước,
  không comment trang trí; comment cũ không dấu sửa dần khi chạm file.

## 6. Rủi ro và cách né

- Import churn vỡ runtime → re-export tương thích từng phase, xóa ở P6.
- Circular import khi tách → gom types/constants về `shared/` trước khi dọn.
- Celery beat gọi sai path task → cập nhật `integration/celery.py` + test enqueue ở P4.
- Tốn thời gian → đi từng phase nhỏ, anh review từng commit, dừng/khóa phạm vi bất cứ lúc nào.

## 7. Nghiệm thu mỗi phase

`uv run pytest` xanh, `npx vitest run` xanh, `ruff check` không lỗi mới,
`docker compose build api ai-worker` + `/health` OK, smoke P6 đạt.
