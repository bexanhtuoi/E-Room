---
name: Quy chuẩn thiết kế API FastAPI (Clean & Modern)
description: Quy ước thiết kế REST API hiện đại với FastAPI - clean, direct response, OpenAPI-first, service-based execution
tags:
  - api
  - fastapi
  - openapi
  - rest
paths:
  - "**/*.py"
---

# Quy chuẩn thiết kế API FastAPI

## Mục tiêu

Thiết kế API rõ ràng, nhất quán, dễ mở rộng, tuân thủ REST và OpenAPI, tối ưu cho FastAPI ecosystem, tận dụng tối đa FastAPI + Pydantic + SQLModel, đảm bảo tách biệt hợp lý giữa tầng điều phối và tầng xử lý dữ liệu, hướng tới cấu trúc clean, dễ bảo trì và dễ tích hợp client.

---

## 1. Endpoint Design Style

- Resource-based URL
- Không dùng động từ trong endpoint
- Dùng danh từ số nhiều

### Nên

```http
GET    /users
GET    /users/{user_id}
POST   /users
PATCH  /users/{user_id}
DELETE /users/{user_id}
```

### Không nên

```http
POST /createUser
POST /deleteUser
GET  /getUsers
```

---

## 2. Response Style

- API luôn khai báo response_model để đảm bảo contract giữa server và client.
- Không sử dụng response wrapper/envelope.
- Response phải nhất quán theo contract.

### Nên

```python
@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
)
async def get_user(
    user_id: int,
):

    # Gọi service lấy user qua id
    user = await user_service.get_one(user_id)

    return user
```

### Không nên

```python
return {"user": user}
```

```python
return user.dict()
```

---

## 3. Request Handling

- Input request nên được chuẩn hoá bằng Pydantic và Depends.
- Schemas Pydantic nên kế thừa nhau và dùng typing, enum...
- Path parameter dùng để định danh resource.
- Query parameter nên được gom qua Depends (pagination/filter/sort).
- Request body luôn dùng schema rõ ràng.
- Không xử lý raw query logic trực tiếp trong router.

### Nên

```python
from fastapi import Depends, Query
from pydantic import BaseModel


class ItemCreate(BaseModel):
    field_a: str
    field_b: str


def get_pagination_params(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> tuple[int, int]:
    skip = (page - 1) * size
    return skip, size


@router.get("/{item_id}")
def get_item(item_id: int):
    ...


@router.get("/", response_model=list[ItemResponse])
def list_items(
    db: Session = Depends(get_session),
    pagination: tuple[int, int] = Depends(get_pagination_params),
):
    skip, limit = pagination
    return item_crud.get_many(db, skip=skip, limit=limit)


@router.post("/")
def create_item(data: ItemCreate):
    ...
```

### Không nên

```python
@router.get("/")
def list_items(page: int, size: int):
    ...

@router.post("/")
def create_item(data: dict):
    ...

@router.get("/")
def list_items(skip: int = 0, limit: int = 20):
    ...
```

---

## 4. Router Pattern

- Router xử lý business flow ở mức điều phối.
- Có thể validate input, kiểm tra điều kiện nghiệp vụ cơ bản.
- Gọi service để xử lý data access.
- Không truy cập DB trực tiếp trong router.
- Không build response thủ công nếu đã có `response_model`.

### Nên

```python
@router.post(
    "/users",
    response_model=UserResponse,
    status_code=201
)
async def create_user(
    data: UserCreate
):
    existing = await user_service.get_by_email(data.email)

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Email already exists",
        )

    user = await user_service.create(data)
    return user
```

### Không nên

```python
@router.post("/users")
async def create_user(data: dict):
    db.add(...)
    db.commit()
    return {"success": True}
```

```python
@router.post("/users")
async def create_user(data: UserCreate):
    user = user_service.create(data)
    return {"data": user}
```

---

## 5. Middleware

- Middleware dùng cho các xử lý dùng chung cho toàn bộ request/response.
- Không chứa business logic.
- Luôn là `async`.
- Có thể sử dụng để logging, authentication, request ID, rate limiting, metrics...
- Hạn chế truy cập database và không xử lý business logic.

### Nên

```python
from fastapi import Request


@app.middleware("http")
async def middleware(
    request: Request,
    call_next,
):
    response = await call_next(request)
    return response
```

### Không nên

```python
@app.middleware("http")
async def middleware(request: Request, call_next):
    user = await user_service.get_current_user()
    ...
```

---

## 6. Application Configuration

- Khởi tạo `FastAPI` tại một nơi duy nhất.
- Khai báo middleware và cấu hình ứng dụng ngay sau khi tạo app.
- Mỗi resource có một `APIRouter`.
- Router được include tại file khởi tạo ứng dụng.

### Nên

```python
from fastapi import APIRouter

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)
```

```python
from fastapi import FastAPI
from app.config import settings

@asynccontextmanager
async def app_lifespan(app: FastAPI):
    ...
    yield
    ...

app = FastAPI(
    title="Example API",
    description="REST API built with FastAPI",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)
```

```python
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

```python
from app.api import users

app.include_router(
    users.router,
    prefix="/api/v1"
)
```

### Không nên

```python
router = APIRouter()
```

```python
app.include_router(
    APIRouter(),
)
```

```python
app.add_middleware(...)
app.add_middleware(...)
app.add_middleware(...)
# Khai báo middleware rải rác nhiều nơi
```

---
## 7. Async Programming

- Ưu tiên sử dụng `async` cho endpoint và service khi thực hiện I/O.
- Luôn `await` các hàm bất đồng bộ.
- Không thực hiện blocking I/O trong async context.
- Không trộn lẫn sync và async nếu thư viện đã hỗ trợ async.

### Nên

```python
@router.get("/{user_id}")
async def get_user(user_id: int):
    return await user_service.get_one(user_id)
```

```python
class UserService:

    async def get_one(
        self,
        user_id: int,
    ):
        return await user_repository.get_one(user_id)
```

### Không nên

```python
@router.get("/{user_id}")
async def get_user(user_id: int):
    return user_service.get_one(user_id)
```

```python
@router.get("/{user_id}")
def get_user(user_id: int):
    return await user_service.get_one(user_id)
```

```python
@router.get("/{user_id}")
async def get_user(user_id: int):
    time.sleep(1)
    return await user_service.get_one(user_id)
```

```python
class UserService:

    async def get_one(
        self,
        user_id: int,
    ):
        return user_repository.get_one(user_id)
```

--- 

## 8. Error Handling

- Xử lý lỗi tập trung bằng Exception Handler.
- Chỉ raise exception trong router/service.
- Không tự build response lỗi trong endpoint.
- Tạo custom exception cho lỗi nghiệp vụ.
- Trả về mã HTTP phù hợp.

### Nên

```python
from fastapi import HTTPException

if user is None:
    raise HTTPException(
        status_code=404,
        detail="User not found",
    )
```

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()


@app.exception_handler(Exception)
async def exception_handler(
    request: Request,
    exc: Exception,
):
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal Server Error",
        },
    )
```

### Không nên

```python
return {
    "success": False,
    "message": "User not found",
}
```

```python
return JSONResponse(
    status_code=400,
    content={
        "error": "...",
    },
)
```

```python
try:
    ...
except Exception:
    pass
```

