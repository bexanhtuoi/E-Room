# PLAN.md

## 1. Vấn đề hiện tại

`backend/app` (134 file) chưa tuân thủ đầy đủ quy chuẩn Python của dự án:

- 1.057 điểm thiếu dòng trống giữa các câu lệnh/khối logic (rule: dòng trống sau MỖI câu lệnh, kể cả 2 phép gán liên tiếp).
- 61 chú thích viết tiếng Việt không dấu hoặc tiếng Anh (rule: chú thích luôn tiếng Việt có dấu, không trang trí).
- 7 docstring cần xem xét (rule: không docstring dư thừa).

## 2. Cách giải quyết (Phương án A — tự động hóa có kiểm chứng)

1. **Chèn dòng trống tự động** bằng `tempt/fix_spacing.py`:
   - Duyệt AST, với mỗi cặp câu lệnh liên tiếp trong cùng thân khối (module, class, function, if/for/while/with/try, match-case).
   - Nếu giữa chúng chưa có dòng trống → chèn 1 dòng trống, ưu tiên chèn trước khối comment gắn với câu lệnh sau.
   - Không chèn trong: cặp import-import liền nhau, docstring với câu lệnh kế, các nhánh elif/else/except của cùng một khối.
   - Ghi lại file giữ nguyên kiểu xuống dòng, bỏ BOM UTF-8 (5 file ai/ có BOM).
2. **Việt hóa chú thích** bằng mapping `tempt/style_fixes.json` + `tempt/apply_comments.py`:
   - Khớp chú thích theo nội dung chính xác (không phụ thuộc số dòng) → thay bằng bản tiếng Việt có dấu.
   - Chú thích thuần kỹ thuật không chứa chữ Việt (`# <pad>`, `# 20ms`, `# noqa`) giữ nguyên.
   - Dòng trang trí `# ─── Tên ───` trong `config.py` → rút gọn thành nhãn mục `# Tên`.
3. **Bỏ docstring dư thừa** ở `ai/pronunciation/feedback.py` + `metrics.py` nếu chỉ nhắc lại tên hàm (quyết định sau khi đọc từng docstring).
4. **Kiểm chứng bắt buộc**:
   - `uv run python -m compileall` toàn `app/` — không lỗi cú pháp.
   - Chạy lại `tempt/scan_style.py backend/app` — kỳ vọng 0 vi phạm (trừ ngoại lệ đã giải thích).
   - `uv run ruff check app` — không lỗi mới.
   - `uv run pytest` — toàn bộ test hiện có phải pass (đặc biệt `tests/unit/test_architecture.py`).
   - `git diff --stat` — chỉ thay đổi dang dòng/chú thích, không đổi logic.

## 3. Phương án dự phòng (B)

- Nếu script chèn dòng trống gây lỗi ở file phức tạp (match-case, decorator, comment nội suy): chạy theo từng cụm thư mục nhỏ, file lỗi thì sửa tay bằng `edit` dựa trên báo cáo quét.
- Nếu mapping chú thích khớp sai vị trí: đối chiếu `git diff`, khôi phục file bằng `git restore` rồi sửa tay từng file.
- Toàn bộ thay đổi nằm trên working tree (nhánh `student`, trạng thái sạch trước khi bắt đầu) nên có thể `git restore .` để quay lại bất cứ lúc nào.

## 4. Công cụ sử dụng

- `uv` + Python 3.13 (AST, tokenize) — chạy script.
- `ruff` — kiểm tra style/logic tĩnh sau khi sửa.
- `pytest` — kiểm thử hồi quy.
- Công cụ sửa file của harness (`edit`) cho các chỉnh sửa thủ công cuối.

## 5. Đầu ra mong đợi

- `backend/app` đạt chuẩn: 0 điểm thiếu dãn dòng, 0 chú thích thiếu dấu/trang trí, không docstring dư thừa, không BOM.
- Không thay đổi hành vi: toàn bộ test hiện có pass, ruff sạch, compileall sạch.
- Báo cáo kết quả kèm thống kê trước/sau trong TODO.md.
