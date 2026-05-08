# E-Room

E-Room là bộ khung dự án fullstack tách `frontend` và `backend`, lấy cảm hứng từ cách tổ chức của FlowAssist để chuẩn bị chuyển dự án EngConnect sang tên mới **E-Room**.

## Mục tiêu

- Giữ cấu trúc rõ ràng giữa frontend/backend
- Backend dùng **uv** để quản lý môi trường và dependency
- Frontend khởi tạo bằng **Create React App** qua `npx create-react-app`
- Sẵn chỗ cho các module AI như `agent`, `mcp`, `rag`
- Có thêm `admin` app riêng tương tự FlowAssist

## Cấu trúc thư mục

```text
E-Room/
├─ backend/
│  ├─ app/
│  │  ├─ api/
│  │  ├─ agent/
│  │  ├─ mcp/
│  │  ├─ model/
│  │  ├─ rag/
│  │  ├─ schemas/
│  │  ├─ service/
│  │  └─ utils/
│  ├─ admin/
│  ├─ migrations/
│  ├─ static/
│  ├─ log/
│  └─ Researching/
├─ frontend/
└─ docker-compose.yml
```

## Khởi chạy backend

```bash
cd backend
uv sync
uv run python -m app.server
```

Admin:

```bash
cd backend
uv run python -m admin.server
```

## Khởi chạy frontend

```bash
cd frontend
npm start
```

## Docker

```bash
docker compose up --build
```

## Ghi chú

- Đây là **project skeleton**, chưa phải bản hoàn chỉnh của E-Room.
- Frontend được tạo bằng CRA để tránh lỗi khi dựng tay từ đầu.
- Backend dùng `uv` và đã tạo sẵn `.venv`.
