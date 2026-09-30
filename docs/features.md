# E-Room — Features

> Cập nhật: 09/2026 · Mọi mục (trừ ghi rõ "dự kiến") đều đã chạy thật, đối chiếu code.

## 1. Room nói chuyện theo chủ đề (tối đa 6 người)

- **List**: sắp xếp live → open → ended, mới nhất trước trong mỗi nhóm; window 10 + infinite scroll; filter All/Live/Open/Ended; nút Reload; refresh 10s. Phòng riêng (`is_private`) ẩn với người lạ.
- **Home**: live trước → open sau.
- **Tạo phòng**: tên + description + tối đa 5 topics + 1–6 seats (mặc định 4) + tùy chọn private + hẹn giờ (`scheduled_at`). Tạo xong vào thẳng, list tự refresh (invalidate query).
- **Row**: tên, badge trạng thái, description, topics, host, ngày tạo, **faces người ĐANG trong phòng** (live, refresh 5s — không phải lịch sử chat), badge `PRIVATE` nếu là phòng riêng.
- **Match/Quick match**: `POST /api/v1/rooms/match` chọn phòng public phù hợp topic (ưu tiên active trước idle, loại ended).
- **Config** (`/rooms/:roomId/config`): host sửa tên/topics/seats/private.

## 2. Video call trong phòng

| Nút | Hành vi |
|---|---|
| Mic / Cam | Toggle trực tiếp `setMicrophoneEnabled/CameraEnabled`, optimistic UI + force re-render theo events; lỗi hiện banner chữ đen (quyền/thiết bị/bận/in-app browser) |
| Share | Chỉ desktop (trình duyệt có `getDisplayMedia`). **Mobile (iOS Safari, Chrome Android) không hỗ trợ** — nút mờ + tooltip, bấm hiện hướng dẫn. Đây là giới hạn nền tảng, không phải bug |
| Hand | Gửi `hand_raise` qua LiveKit data → máy khác hiện thông báo ✋ 6s |
| React (emoji) | Publish `{type:'emoji'}` qua data channel → **mọi máy** cùng bay emoji 2s |
| Chat / People / Setup | Panel phải: chat, danh sách người (đã lọc `ai_*`), settings phòng |
| Leave / ← Back | Gọi `POST /api/v1/rooms/{id}/leave` (xóa presence ngay) + ngắt LiveKit rồi mới thoát |

Video grid lọc `ai_*`; trần 6 seats chỉ tính người thật (token endpoint chặn 403 khi full).

## 3. Chat + `@ai` trò chuyện

- Gửi/nhận tin nhắn text (`POST /api/v1/messages/`), optimistic render, poll 4s bắt kịp khi miss realtime.
- Tin **voice** hiện như tin thường + **icon mic sau tên** (không card riêng).
- Lịch sử + quote: AI trả lời luôn quote lại câu hỏi gốc (`source_message_id`).
- Hỏi AI: gõ `@ai ...` trong chat **hoặc nói "@ai ..." vào mic** → agent stream **từng từ** qua LiveKit data channel (pace 40ms/từ).
- **Thinking stream trước đáp án**, gồm 2 nguồn thật:
  1. **Reasoning của model** (kênh `reasoning_content`; system prompt bắt nghĩ trước trừ chào hỏi).
  2. **Tool calls** ("Searching documents…") + "Got N result(s) — composing answer…" khi tool xong.
- Tool: `retrieval_documents` (Qdrant + reranker, lỗi thì trả rỗng để agent tự đáp chứ không chết stream), `web_search` (Tavily, thiếu key thì bỏ qua), `transcript_info` / `get_more_messages` / `search_transcript` (đọc transcript session).
- Giới hạn thật: đáp án dài ~1 phút là bình thường, job RAG nặng có thể chạm trần `AI_TIMEOUT_SECONDS` (mặc định 900s).

## 4. RAG tài liệu trong room

- Upload (host-only): `POST /api/v1/rooms/{id}/documents` (pdf/md/txt ≤10MB) → chunk + embed + index Qdrant với tag `room:{id}`; list/tải/xóa giữ nguyên quyền host.
- Agent chỉ search đúng doc của room hiện tại (`make_room_retrieval_tool` đóng tag), rerank bằng Qwen3 trước khi đưa vào context.
- CRUD global ở `/api/v1/documents/` (phân quyền theo chủ sở hữu), thông báo ở `/api/v1/notifications/`.

## 5. AI Summary / Recap / Analyze / Q&A session

- **Feedback cả session**: `POST /api/v1/sessions/{session_id}/feedback` — gộp các câu đã chấm trong session (đọc DB `pronunciation_scores`, fallback JSONL cho điểm cũ), gửi LLM với prompt `assessment.md` (gọn, chỉ nêu phần sai kèm quote + cách sửa + bước luyện). Chưa chấm câu nào → `409`. Chỉ chính chủ / host / admin được xem.
- **Hỏi đáp trên transcript**: `POST /api/v1/sessions/{session_id}/chat` (sync) và `/chat/stream` (SSE `text/event-stream`) — agent có tool đọc transcript.
- **Transcript gộp**: `GET /api/v1/rooms/{room_id}/speech-logs/summary` — toàn room sort theo giờ.
- UI: Assessment (`/assessment/:sessionId`) = session mới nhất của bạn (chọn lại được): AI feedbacks + điểm từng câu + transcript kèm loa. Trang session (`/session/:id`) giữ bản classic: transcript + hỏi đáp AI.

## 6. AI heartbeat (chống im lặng)

- Beat 15s (`check_room_heartbeats`): phòng `active` + ≥2 người + bật `enable_heartbeat` + im lặng quá `heartbeat_interval_seconds` → enqueue job hỏi 1 câu gợi chuyện (stream qua LiveKit như `@ai`).
- Phòng trống lâu (`ROOM_EMPTY_END_SECONDS`, mặc định 24h) → `ended` cho gọn list (`end_stale_empty_rooms`).
- Phòng hẹn (`scheduled_at`) quá 24h → xóa hẳn (`delete_expired_scheduled_rooms`).
- Beat 60s (`ensure_room_workers`): phòng live thiếu transcriber/observer (vd sau restart) thì enqueue lại — tự hồi không cần sờ tay.

## 7. AI transcript (nói → chữ)

- `ai-transcriber` join phòng, subscribe track audio từng người (bỏ qua `ai_*`).
- VAD năng lượng cắt câu (im ≥2s chốt câu), **cắt silence cuối** trước khi STT (chống Whisper bịa closing), chống lặp từ/hallucination.
- Dispatch STT (`STT_PROVIDER=auto` mặc định): ping server `:8001` — sống thì dùng host (`large-v3-turbo`, GPU), chết hoặc trả rỗng thì fallback whisper local. Ép cứng: `whisper_server` (chỉ host) hoặc `faster_whisper` (chỉ local). Hàng đợi ≥4 job thì tràn sang cloud (tiếng Anh + có key).
- Lưu DB (`source: speech_to_text` + confidence) + broadcast LiveKit cho cả phòng.
- Sửa câu (`PATCH`, chỉ câu của mình): reset điểm + feedback cũ, bắt chấm lại (khớp `reading-score.md`).

## 8. AI đánh giá phát âm và ngữ pháp

- Luồng `raw → sửa → chấm → nhận xét`: STT lưu raw (`pronunciation=None`) → user sửa `corrected_text` → `POST .../score` chấm trên bản đã sửa + audio ĐẦU–CUỐI lượt nói (audio nặng → `202 {queued}`, chấm nền) → `POST .../feedback` xin góp ý AI (chưa chấm thì `409` `NO_SCORE_REPORT`).
- Kết quả: điểm tổng + 4 tiêu chí (Sounds / Stress / Fluency / Completeness). **Điểm từng chữ ẩn mặc định** — bấm **Thống kê điểm số** mới mở bảng riêng (Chữ · Điểm · Trạng thái · IPA + lỗi âm nổi bật); nút **Nhận xét AI** độc lập (gồm cả ngữ pháp/từ vựng, cấm bịa lỗi).
- Mỗi từ yếu kèm hướng dẫn sửa: khẩu hình (`how_to`) + phiên âm Việt (`vi`) từ `articulation.py`.
- Máy host tự tính (wav2vec2 + phoneme GOP local), chấm tuần tự (`SCORING_MAX_PARALLEL=1`) chống OOM khi nhiều người bấm dồn. Điểm lưu DB (`pronunciation_scores`), JSONL giữ làm log raw/audio.
- Người cuối rời phòng → auto chấm nốt các câu chưa chấm. Chi tiết: `reading-score.md`.

## 9. TTS giọng đọc mẫu

- Server TTS riêng (`:8002`, OpenAI-compatible), 4 giọng: `af_heart` (nữ Mỹ, mặc định), `am_adam` (nam Mỹ), `bf_emma` (nữ Anh), `bm_george` (nam Anh).
- Mỗi dòng *What was said* có nút loa nghe mẫu đọc đúng (cache theo giọng+câu) + `VoicePicker` chọn giọng chung. Giọng chỉ ảnh hưởng phần nghe, **không đổi điểm**.

## 10. Agent live — dự kiến

Chưa có code. Khi làm sẽ là participant AI real-time trong phòng (nói + nghe liên tục), tái dùng hạ tầng transcriber/observer/stream hiện có.

## 11. Schedule Room và Private Room

- **Schedule**: modal đặt lịch (tên, topics, seats, `is_private`, emails, `when`) ở mục Schedule của Profile; thêm email → tự bật private. Phòng hẹn quá 24h tự xóa (task maintenance).
- **Private**: flag `is_private` + `allowed_emails`. Ẩn khỏi list/match với người lạ; vào phòng (xem, lấy token, participants, speech-logs) chỉ host/admin/email được mời (`ensure_room_access`). Badge `PRIVATE` ở list. Gói Pro quảng cáo "Create private rooms" (Pricing/Payment).

## 12. Presence (ai đang trong phòng)

- Nguồn thật: Redis set `room:{id}:participants`, ghi bởi **webhook LiveKit** (bỏ qua `ai_*`) + **endpoint join/leave trực tiếp** (idempotent, chống miss webhook khi tab đóng đột ngột).
- Join trực tiếp mở session + enqueue observer/transcriber; hết người → phòng về `idle` + đóng session + enqueue chấm nốt.
- Hết người → phòng về `idle` (vẫn hiện list để vào lại).

## 13. Auth / Onboarding / Profile / Subscription

- Đăng ký/đăng nhập (cookie HttpOnly, session 7 ngày) + Google OAuth (cần OAuth Client ID; service-account dùng không được) + logout xóa cookie.
- Onboarding wizard (level, topics, mục tiêu), Profile (sửa tên/avatar, hoạt động gần đây, thống kê cá nhân `/users/me/stats`).
- Subscription: gói quota (giới hạn seats/tính năng) + `QuotaIndicator`/`UpgradePrompt` ở Pricing/Payment.

## 14. Trang public

Home / Pricing / Blog / Contact + Login 1 card + Rooms. Navbar: Home–Pricing–Blog–Contact + Go to Rooms + profile/sign-out.
