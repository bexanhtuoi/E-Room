---
name: Quy chuẩn kiến trúc Backend FastAPI
description: Quy ước tổ chức dự án Backend sử dụng FastAPI.
tags:
  - backend
  - fastapi
  - architecture
paths:
  - "**/*.py"
---

# Quy chuẩn kiến trúc Backend FastAPI

## Mục tiêu

Tổ chức dự án rõ ràng, dễ mở rộng, dễ bảo trì và phù hợp với môi trường production.

---

## Nguyên tắc tầng

Luồng phụ thuộc một chiều, từ trên xuống dưới:

```text
routers → services → repositories → models
   ↓          ↓           ↓
 shared ← shared ← shared (lá, không phụ thuộc app)
```

- `routers` chỉ điều phối: validate input → gọi service → trả response.
- `services` giữ business logic dưới dạng class (`RoomService`, `SessionService`...) + singleton (`room_service`, `session_service`...).
- `repositories` giữ CRUD/query dưới dạng class (`RoomCrud`...) + singleton (`room_crud`...).
- `shared` là lá: constants, keys, exceptions — không import bất kỳ module `app` nào khác.
- `schemas` chỉ validate, không import tầng logic (`ai`, `services`, `repositories`, `tasks`).
- `ai` chia package theo năng lực, `tasks` chứa Celery jobs cùng cấp `ai`.

---

# Cấu trúc dự án

```text
backend/
├── app/
│   ├── api/
│   │   ├── routers/        # endpoint mỏng (auth, user, room, ...)
│   │   ├── dependencies.py # require_auth, authorize_*, pagination
│   │   └── __init__.py
│   │
│   ├── services/           # BUSINESS: XxxService + x_service singleton
│   │   ├── base.py         # ServiceBase (one_or_404) + re-export CRUDRepository
│   │   ├── helpers.py      # hàm dùng chung giữa các service
│   │   └── __init__.py     # facade re-export crud singletons
│   │
│   ├── repositories/       # DATA ACCESS: XxxCrud + x_crud singleton
│   │   ├── base.py         # CRUDRepository
│   │   └── __init__.py
│   │
│   ├── models/             # SQLModel ORM (bảng + quan hệ, không logic)
│   ├── schemas/            # Pydantic request/response (không import tầng logic)
│   │
│   ├── shared/             # lá: constants, keys, exceptions
│   │   ├── constants.py    # hằng dùng chung (AI identities, SESSION_CHAT_KEY...)
│   │   ├── keys.py         # builders: room_presence_key, room_tag...
│   │   └── exceptions.py   # AppException + lỗi domain
│   │
│   ├── ai/                 # khả năng AI theo package + helpers.py mỗi nơi
│   │   ├── llm/            # client, prompt, query, tools, participant, observer
│   │   ├── rag/            # chunking, dense, sparse, reranker, retrieval, vector_store
│   │   ├── stt/            # local, server, cloud, dispatch, completion, paths, recorder...
│   │   ├── tts/            # speech
│   │   ├── vad/            # audio_vad
│   │   ├── pronunciation/  # audio, g2p, align, scorer, feedback, metrics, models...
│   │   └── prompts/        # file .md cho LLM
│   │
│   ├── tasks/              # Celery jobs: helpers, room_jobs, maintenance, scoring
│   │
│   ├── integration/        # celery, livekit, redis, minio (lá hạ tầng)
│   ├── utils/              # hàm dùng chung (file, retry, chat, upload...)
│   ├── seeds/
│   │
│   ├── config.py
│   ├── database.py
│   ├── security.py
│   ├── log.py
│   ├── server.py
│   └── main.py             # khởi tạo app + đăng ký exception handler
│
├── alembic/
├── tests/                  # unit / api / e2e / integration / security
│
├── .env (không commit)
├── .env.example
├── .dockerignore
├── Dockerfile
├── pyproject.toml
└── uv.lock
```

---

## app/api/routers

- Khai báo endpoint, validate request qua schema/`Depends`.
- Gọi đúng 1 service singleton (`room_service.list_rooms(...)`), không gọi lẫn nhau.
- Trả response trực tiếp (đã có `response_model`), không build thủ công.
- Cấm: `HTTPException`, `db.exec/add/commit/delete`, `select(`, import `app.ai`.

Ví dụ

```python
from app.services.room import room_service


@router.get("/{room_id}", response_model=RoomResponse)
def get_room(room_id: int, request: Request, db: Session = Depends(get_session)):
    room = room_service.get_room_or_404(db, room_id)
    room_service.ensure_room_access(room, request.state.current_user)

    return room
```

---

## app/services

- Mỗi domain một class `XxxService(ServiceBase)` + singleton `x_service`.
- Method nhận `db` làm tham số đầu, orchestrate repositories/services khác/ai/tasks.
- Hàm thuần dùng chung → `services/helpers.py`, không để lẫn trong service.
- Lỗi domain raise từ `shared.exceptions`, không bao giờ `raise HTTPException`.
- Dùng `self.one_or_404(repo.get_one, NotFoundError, db, ...)` cho mẫu fetch-or-404.

Ví dụ

```python
class RoomService(ServiceBase):
    def get_room_or_404(self, db: Session, room_id: int) -> Room:
        return self.one_or_404(room_crud.get_one, RoomNotFoundError, db, id=room_id)


room_service = RoomService()
```

---

## app/repositories

- Mỗi domain một class `XxxCrud(CRUDRepository)` + singleton `x_crud`.
- Chỉ CRUD/query/transaction, không business logic, không import `services`/`api`.
- Query riêng của domain viết thành method (`find_for_utterance`, `scored_in_window`...).

---

## app/models, app/schemas

- `models`: SQLModel ORM — bảng + quan hệ, không business logic, không query.
- `schemas`: Pydantic request/response/validation — không business logic,
  không thao tác DB, không import `ai`/`services`/`repositories`/`tasks`.

---

## app/shared

- `constants.py`: hằng dùng chung (không hard-code chuỗi key/identity rải rác).
- `keys.py`: builder cho Redis key, RAG tag (`room_presence_key`, `room_tag`...).
- `exceptions.py`: `AppException(status_code, code, detail)` + lỗi domain
  (`RoomNotFoundError`, `NotAuthorizedError`, `NoScoreReportError`...).
- Message lỗi luôn tiếng Việt có dấu.
- Cấm import bất kỳ module `app` nào khác ngoài `app.shared`.

---

## app/ai

- Một package một năng lực, mỗi package có `helpers.py` cho hàm phụ.
- Mỗi package có `__init__.py` re-export API public để import ngắn gọn.
- File >~300 dòng hoặc đa trách nhiệm thì chẻ tiếp (xem `stt/`, `pronunciation/`).
- Hàm dài tách helper có tên rõ nghĩa, tái dùng qua `helpers.py` thay vì copy code.
- Không tên `_` ở đầu cho hàm/biến module (ngoại lệ: backing-field của `@property`,
  API private của thư viện ngoài).

---

## app/tasks

- Celery jobs tách theo cụm: `helpers` (locks/keys), `room_jobs`, `maintenance`, `scoring`.
- Tên task = đường dẫn module đầy đủ (`app.tasks.scoring.score_single_utterance`).
- Task gọi service/repository, không chứa business mới.

---

## Xử lý lỗi

- Services raise lỗi domain từ `shared.exceptions`.
- `main.py` đăng ký đúng 1 handler:

```python
@app.exception_handler(AppException)
async def handle_app_exception(request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "detail": exc.detail},
    )
```

- Không `try/except` nuốt lỗi trong routers/services. Không tự build response lỗi.

---

## app/utils, config, database, security, main

- `utils`: hàm dùng chung (decorator, file, retry, helper, validation).
  Không business logic, không thao tác DB.
- `config.py`: Pydantic Settings + env duy nhất. Không hard-code, không khai báo rải rác.
- `database.py`: engine/session/metadata. Không truy vấn nghiệp vụ.
- `security.py`: JWT, hash, authentication, authorization.
- `main.py`: khởi tạo FastAPI, middleware, router, exception handler, lifespan.
  Không business logic.

---

## tests

- Đặt trong `tests/`, không đặt trong `app`.
- Bao phủ: unit, api, integration, e2e, security.
- `tests/unit/test_architecture.py` khóa kiến trúc: quét AST cấm routers dùng
  `HTTPException`/DB/ai-import, cấm import ngược tầng, khóa tên task Celery
  và facade surfaces — refactor làm vỡ tầng là test đỏ ngay.

---

## Không được phép

- Đặt truy vấn cơ sở dữ liệu trong API.
- Raise `HTTPException` trong routers/services (dùng lỗi domain).
- Đặt business logic trong Repository/Model/Schema.
- Import ngược tầng (`repositories` → `services`, `services` → `api`,
  `schemas` → tầng logic, `shared` → bất kỳ module `app` nào).
- Đặt tên `_` ở đầu hàm/biến module (trừ backing-field property và API thư viện ngoài).
- Viết comment trang trí/docstring dư thừa (xem quy chuẩn Python).
- Hard-code thông tin cấu hình.
- Khai báo cấu hình ở nhiều nơi.
- Đặt mã không liên quan trong cùng một module.
