# TODO.md

## Dọn chú thích + giãn dòng `backend/app` (theo `.opencode/rules/`)

- [x] Khảo sát 134 file trong `backend/app`, viết công cụ quét (`tempt/scan_style.py`, `tempt/comment_list.py`)
- [x] Chốt phạm vi (`backend/app`) và mức giãn dòng (nghiêm ngặt theo rule) với người dùng
- [x] Lập EXPLORE.md + PLAN.md
- [x] Đọc ngữ cảnh các chú thích cần Việt hóa (config.py, scoring.py, phonemes.py, ...)
- [x] Soạn mapping chú thích mới + quyết định docstring dư thừa (`tempt/style_fixes.json`)
- [x] Viết `tempt/fix_style.py` (gộp: thay chú thích theo token + chuyển docstring thành comment + chèn dòng trống theo AST)
- [x] Chạy fix trên `backend/app` (88 file, +1.253/−116 dòng), bỏ BOM 5 file
- [x] Verify quét lại: spacing 1.057→0, không dấu 61→0, mã chết 4→0, docstring 7→0; `ruff check app` y hệt HEAD (21 lỗi có sẵn); `compileall` sạch
- [x] Verify pytest: full-suite 516 pass / 3 fail `test_transcriber` — bản HEAD gốc cũng fail y hệt (pollution `test_ai_timeout` reload config, đã tái hiện); pronun fail trên snapshot chỉ do thiếu `.env`, có `.env` thì pass
- [x] Rà `git diff --stat`: ngoài `backend/app` chỉ có 3 file `.opencode/*.md`
- [x] Dọn thư mục `tempt/`, chốt báo cáo cuối

## Đợt tiếp: fix 3 lỗi ruff cơ học + commit (yêu cầu người dùng)

- [x] Giải thích phương án (b), chạy xem trước `--diff`, chốt an toàn với người dùng
- [x] `uv run ruff check app --fix` (I001×2 + F401); verify: còn đúng 18 lỗi có sẵn, compileall sạch, smoke import facade `app.schemas` OK (38 tên)
- [x] Commit `e7f3a07` (style: dọn chú thích + giãn dòng) và `980b70b` (style: sort import + drop Any) lên nhánh `student`
- [x] Verify full-suite pytest sau fix: khớp baseline 516 pass / 3 fail có sẵn (733s)
- [x] Cập nhật EXPLORE.md mục 7, xoá backup tạm, chốt báo cáo
