# EXPLORE.md

## 1. Yêu cầu

Dọn sạch chú thích và giãn dòng hợp lí theo quy tắc có sẵn trong `.opencode/rules/`.

## 2. Phạm vi đã chốt với người dùng

- **Chỉ `backend/app`** (134 file Python, không gồm tests/scripts/alembic/ec2).
- Mức giãn dòng: **nghiêm ngặt theo rule** — dòng trống sau mỗi câu lệnh/khối logic, trước/sau mỗi khối if/for/while/try (kể cả 2 phép gán liên tiếp cũng cách nhau).

## 3. Quy tắc liên quan (trích `.opencode/rules/python-coding-style.md`)

- Dãn dòng: dòng trống sau MỖI câu lệnh/khối logic; trước/sau mỗi khối `if/for/while/try`; giữa các bước xử lý.
- Dict/list nhiều key thì mỗi key 1 dòng.
- KHÔNG viết comment trang trí/docstring dư thừa — chỉ giữ comment theo bước hoặc ghi chú ràng buộc quan trọng, luôn tiếng Việt có dấu.
- Không để lại mã đã comment, không giữ mã không còn dùng.
- (backend-architecture.md) Cấm import ngược tầng, routers không HTTPException/DB/ai — sẽ kiểm tra bằng test hiện có.

## 4. Công cụ đã khảo sát

| Công cụ | Thông tin |
| --- | --- |
| `tempt/scan_style.py` | Script tự viết: AST phát hiện thiếu dòng trống giữa các khối logic + tokenize phát hiện chú thích thiếu dấu/trang trí/mã chết. Chạy bằng `uv run --project backend python tempt/scan_style.py <dir> [--full]`. |
| `tempt/comment_list.py` | Liệt kê đầy đủ chú thích/docstring cần dọn theo file. |
| ruff | Có sẵn (`backend/.venv`), config `select = E,F,I,W`, line-length 160. Dùng để verify sau khi sửa. |
| pytest | Bộ test đầy đủ (unit/api/e2e/integration/security, gồm `test_architecture.py` khóa tầng). |
| uv | Bắt buộc theo rule, dùng để chạy mọi script Python. |

## 5. Hiện trạng (số liệu quét `backend/app`)

- **134 file**, trong đó:
  - **1.057 điểm thiếu dòng trống** giữa 2 khối logic (nhiều nhất: pronunciation, rag, stt, utils, tasks).
  - **61 chú thích chưa đạt chuẩn** (thiếu dấu tiếng Việt, phần lớn ở `config.py` ~40 dòng).
  - **7 docstring** cần xem xét (6 ở `ai/pronunciation/feedback.py`, 1 ở `ai/pronunciation/metrics.py`).
  - **4 chú thích bị heuristic đánh dấu "mã chết"** — kiểm tra thực tế đều là ghi chú hợp lệ (không phải code bị comment-out).
  - **5 file có BOM UTF-8** ở đầu file (`ai/llm/prompt.py`, `ai/rag/chunking.py`, `ai/rag/dense.py`, `ai/rag/reranker.py`, `ai/rag/sparse.py`).
- Các file vi phạm nặng về dãn dòng: `app/ai/pronunciation/g2p.py` (55), `app/ai/pronunciation/phonemes.py` (49), `app/ai/stt/transcriber.py`, `app/utils/*`, `app/tasks/*`.

## 6. Kết luận khảo sát

- Không có mã bị comment-out thực sự trong `app/`; trọng tâm là (1) chèn dòng trống theo rule, (2) Việt hóa chú thích (thêm dấu), (3) bỏ docstring dư thừa ở `feedback.py` nếu chúng chỉ nhắc lại tên hàm.
- Có thể tự động hóa phần dãn dòng bằng AST (chèn dòng trống, không đổi logic), sau đó verify bằng `compileall`, ruff và pytest.

## 7. Kết quả thực hiện (2026-10-16)

- Công cụ: `tempt/fix_style.py` (đọc `tempt/style_fixes.json`) — thay chú thích theo token COMMENT, gộp separator `# ─── Tên ───` thành nhãn `# Tên`, chuyển 7 docstring thành comment ngay trên `def`, chèn 1.050 dòng trống theo AST cho toàn bộ 134 file. Giữ EOL từng file, gỡ BOM 5 file.
- Kết quả quét lại `backend/app` (cùng scanner, sau khi tinh chỉnh heuristic):
  | Chỉ số | Trước | Sau |
  | --- | --- | --- |
  | Thiếu dòng trống | 1.057 | 0 |
  | Chú thích không dấu (văn xuôi) | 61 | 0 |
  | Nhãn section 1 từ (chủ ý giữ khớp .env) | (3) | 15 |
  | Nghi "mã chết" | 4 | 0 |
  | Docstring | 7 | 0 |
- Ghi chú: 15 nhãn section (`# App`, `# Redis`, `# LLM`...) giữ nguyên theo quy ước `'# Ten nhom'` của 3 file `.env` (đã Việt hóa phần diễn giải đi kèm, vd `# Speech logs (file transcript theo từng user...)`).
- Verify bất biến logic: so AST 134/134 file khớp tuyệt đối; 2 file khác đúng phần 7 docstring đã chuyển thành comment (`feedback.py`, `metrics.py`) — không đổi hành vi.
- `ruff check app` sau đợt dọn: 21 lỗi có sẵn (16 F821 quan hệ chuỗi SQLModel, 2 E501 prompt dài, 2 I001 import block, 1 F401 import thừa) — 0 lỗi mới. `compileall`: sạch.
- Đợt tiếp (theo yêu cầu người dùng): `ruff check app --fix` xử lý 3 lỗi cơ học (I001×2 + F401) → còn **đúng 18 lỗi** không thể tự sửa (F821 + E501); compileall sạch; smoke import facade `app.schemas` đủ 38 tên. Đã commit lên nhánh `student`: `e7f3a07` (style: dọn chú thích + giãn dòng) và `980b70b` (style: sort import + drop Any).
- Pytest full-suite: 3 fail `tests/unit/test_transcriber.py` — bản HEAD nguyên gốc cũng fail đúng 3 test đó. Nguyên nhân có sẵn: `tests/unit/test_ai_timeout.py` `importlib.reload(app.config)` giữa suite làm `settings` singleton lệch, monkeypatch của test không tác dụng (đã tái hiện độc lập: ai_timeout + 1 test transcriber cùng tiến trình → fail, chạy riêng → pass).
- `test_generate_feedback_sends_exclude` từng fail trong lần chạy trên snapshot do thiếu `.env` (cần `LLM_BASE_URL` openrouter) — bổ sung `.env` thì pass trên cả hai bản; không liên quan code.
- Chạy lại full-suite sau đợt fix ruff (`980b70b`): **khớp baseline** — 3 failed (đúng 3 test transcriber đã phân tích) / 516 passed (733s).
