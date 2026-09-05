# E-Room — Features

> Version: v2.0.0 · Mọi mục dưới đây đều đã chạy thật (trừ phần ghi rõ "chưa có API").

## 1. Rooms (phòng)

- **List**: sắp xếp live → open → ended, mới nhất trước trong mỗi nhóm; window 10 + infinite scroll; filter All/Live/Open/Ended; nút Reload; refresh 10s.
- **Home**: tối đa 4 phòng (live trước → open sau).
- **Tạo phòng**: tên + description + tối đa 5 topics + 2–4 seats. Tạo xong vào thẳng, list tự refresh (invalidate query).
- **Row**: tên, badge trạng thái, description, topics, host, ngày tạo, **faces người ĐANG trong phòng** (live, refresh 5s — không phải lịch sử chat).
- **Match/Quick match**: `POST /rooms/match` chọn phòng open phù hợp topic (ưu tiên live).

## 2. Video call trong phòng

| Nút | Hành vi |
|---|---|
| Mic / Cam | Toggle trực tiếp `setMicrophoneEnabled/CameraEnabled`, optimistic UI + force re-render theo events; lỗi hiện banner chữ đen (quyền/thiết bị/bận/in-app browser) |
| Share | Chỉ desktop (trình duyệt có `getDisplayMedia`). **Mobile (iOS Safari, Chrome Android) không hỗ trợ** — nút mờ + tooltip, bấm hiện hướng dẫn. Đây là giới hạn nền tảng, không phải bug |
| Hand | Gửi `hand_raise` qua LiveKit data → máy khác hiện thông báo ✋ 6s |
| React (emoji) | Publish `{type:'emoji'}` qua data channel → **mọi máy** cùng bay emoji 2s |
| Chat / People / Setup | Panel phải: chat, danh sách người (đã lọc AI), settings phòng |
| Leave / ← Back | Gọi `POST /rooms/{id}/leave` (xóa presence ngay) + ngắt LiveKit rồi mới thoát |

Video grid lọc `ai_*`; max 4 seats chỉ tính người thật.

## 3. Chat

- Gửi/nhận tin nhắn text, optimistic render, poll 4s bắt kịp khi miss realtime.
- Tin **voice** hiện như tin thường + **icon mic sau tên** (không card riêng).
- Lịch sử 100 tin + quote: AI trả lời luôn quote lại câu hỏi gốc.

## 4. Transcript live (nói → chữ)

- `ai-transcriber` join phòng, subscribe track audio từng người (bỏ qua `ai_*`).
- VAD năng lượng cắt câu (im ≥2s chốt câu), **cắt silence cuối** trước khi STT (chống Whisper bịa closing).
- STT local `faster-whisper base.en` (CPU int8), strict: `vad_filter`, `condition_on_previous_text=False`, loại lặp từ.
- Lưu DB (`source: speech_to_text` + confidence) + broadcast LiveKit cho cả phòng.
- Nói **"@ai ..."** vào mic → tự trigger agent như gõ `@ai`.

## 5. Trợ lý AI `@ai`

- Hỏi trong chat (`@ai ...`) hoặc bằng giọng nói.
- Stream **từng từ** qua LiveKit data channel (backend pace 40ms/từ).
- **Thinking stream trước đáp án**, gồm 2 nguồn thật:
  1. **Reasoning của model** (kênh `reasoning_content` — đã verify server có trả khi được yêu cầu; system prompt bắt nghĩ trước trừ chào hỏi).
  2. **Tool calls** ("Searching documents…") + "Got N result(s) — composing answer…" khi tool xong.
- Tool: `retrieval_documents` (Qdrant + reranker, lỗi thì trả rỗng để agent tự đáp chứ không chết stream), `web_search` (Tavily, thiếu key thì bỏ qua).
- Đáp án lưu DB kèm `source_message_id` để quote.
- Giới hạn thật: LLM CPU ~3.7 tok/s (đáp án dài ~1 phút), job RAG nặng có thể chạm trần worker 300s.

## 6. Heartbeat (chống im lặng)

- Beat 15s quét phòng `active` ≥2 người + hết `heartbeat_interval_seconds` im lặng → enqueue job hỏi 1 câu gợi chuyện.
- Phòng trống lâu (`ROOM_EMPTY_END_SECONDS`, mặc định 24h) → `ended` cho gọn list.
- Beat 60s `ensure-room-workers`: phòng live thiếu transcriber/observer (vd sau restart) thì enqueue lại — tự hồi không cần sờ tay.

## 7. Presence (ai đang trong phòng)

- Nguồn thật: Redis set `room:{room_id}:participants`, ghi bởi **webhook LiveKit** (bỏ qua `ai_*`) + **endpoint leave trực tiếp** (chống miss webhook khi tab đóng đột ngột).
- Hết người → phòng về `open` (vẫn hiện list để vào lại).

## 8. Auth / Onboarding / Profile

- Đăng ký/đăng nhập (cookie HttpOnly, session 7 ngày) + Google OAuth (cần OAuth Client ID; service-account dùng không được).
- Onboarding wizard (level, topics), Profile (sửa tên, hoạt động gần đây thật).

## 9. Trang public

Home / Pricing / Blog / Contact + Login 1 card + Rooms. Navbar: Home–Pricing–Blog–Contact + Go to Rooms + profile/sign-out.

## 10. Documents & Notifications (có API)

- Upload tài liệu RAG (`/documents/`), thông báo user (`/notifications/`).

## 11. Các trang UI chưa có API (mở được nhưng báo lỗi, chờ backend)

Sessions, SessionDetail, Notes, NoteDetail, Series, Leaderboard, Payment/subscription, Tags (`/tags/*`), Onboarding tag-picker dùng `/tags/*`. Đừng demo các trang này cho người ngoài cho tới khi có API.
