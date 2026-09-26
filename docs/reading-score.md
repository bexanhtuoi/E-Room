# Chấm điểm đọc bằng AI — logic & thiết kế UI

> Quy ước UX đã khóa: **điểm từng chữ bị ẨN mặc định sau khi chấm**.
> Muốn xem phải bấm **Thống kê điểm số** (bảng riêng).
> **Nhận xét AI** là nút độc lập thứ hai.

## 1. Luồng chấm điểm (backend — đã verify code)

```
Mic/user ──▶ VAD cắt câu ──▶ Whisper STT (raw, pronunciation=None)
      ──▶ user sửa corrected_text (PATCH)
      ──▶ POST .../score  → chấm trên corrected_text + audio ĐẦU–CUỐI lượt nói
      ──▶ POST .../feedback → LLM local đọc ScoringReport đã lưu, không chấm lại
```

| Bước | API | Luật |
|---|---|---|
| Sửa câu | `PATCH /rooms/{room_id}/speech-logs/{message_id}` `{corrected_text}` | Sửa sau khi đã chấm → `pronunciation` + `feedback` reset về `None`, bắt chấm lại (`app/ai/speech_log.py::update_corrected_text`) |
| Chấm điểm | `POST /rooms/{room_id}/speech-logs/{message_id}/score` | Dùng audio ĐẦU–CUỐI của attempt + toàn bộ `corrected_text` lượt nói; log cũ (không attempt) mới rớt về wav VAD từng câu (`app/api/routers/speech.py::rescore_utterance`) |
| Nhận xét | `POST /rooms/{room_id}/speech-logs/{message_id}/feedback` | Chỉ chạy khi đã có `pronunciation.report`; chưa chấm → **409** `"Chưa có điểm phát âm — chấm điểm trước"` |

### Scorer (deterministic, không phải LLM)

`app/ai/pronunciation.py::score_attempt_v2` (Part 9, gộp từ scoring_pipeline) trả `ScoringReport`:

- `scores`: `sounds` (âm), `stress` (nhấn), `fluency` (trôi chảy), `completeness` (đủ chữ), `overall` (trung bình trọng số). `intonation` = `None` ở MVP (chỉ detect monotone).
- `word_details[]`: `{word, score, status, expected_ipa}` — `status` ∈ `ok` (≥70) · `pronunciation_error` · `no_evidence` (loại khỏi mẫu số, UI hiện "Không nghe rõ").
- `phonemes[]`: `{word, expected, observed, type, gop, score}` — vd `/θ/ → /s/` ở "think".
- `top_errors[]`: `{pattern, count, examples}` — tối đa 5.
- Thứ tự thử model: local pipeline → Pronun service (`PRONUN_BASE_URL`) → heuristic chữ (không có `word_details`).

### Nhận xét AI (LLM local — chỉ giải thích, không tính điểm)

`app/ai/feedback_llm.py::generate_feedback` (LLM local qua get_llm) nhận **đúng 1 JSON `scoring_report`**, bị cấm đổi điểm / bịa lỗi (luật trong `app/ai/prompts/feedback.md`).
Trả: `summary`, `pronunciation_feedback`, `stress_feedback`, `intonation_feedback`,
`fluency_feedback`, `priority_errors[]`, `practice_plan[]` (hoặc `feedback_raw` khi model trả text thô).

## 2. Thiết kế UI (frontend)

Component: `frontend/src/features/profile/ReadingScoreCard.jsx`
(props: `utterance {text, corrected_text, pronunciation, feedback}`, `onScore`, `onFeedback`, `scoring`, `feedbackLoading`)

### Trạng thái

| State | Hiển thị |
|---|---|
| Chưa chấm (`pronunciation == null`) | Hướng dẫn + nút **Chấm điểm AI** |
| Đã chấm | Câu chấm **hiển thị trơn** (không tô màu/badge từng chữ) + 4 thanh tiêu chí + điểm tổng + **2 nút độc lập** |
| `showStats = true` | Thêm **bảng riêng**: `Chữ · Điểm · Trạng thái · IPA` + mục *Lỗi âm nổi bật* (`top_errors`) |
| `showFeedback = true` | Thêm **panel riêng**: summary → 4 góp ý → *Ưu tiên sửa* → *Luyện tiếp* |
| Sửa text sau khi chấm | Parent reset `pronunciation/feedback` → quay về "chưa chấm" (khớp luật backend) |

### Quy tắc bắt buộc khi sửa UI này

1. **Không** render điểm từng chữ ra ngoài `word-stats-table` (không highlight chữ trong câu).
2. Hai nút **không gộp**: `Thống kê điểm số` chỉ toggle bảng, `Nhận xét AI` chỉ toggle/gọi feedback.
3. Nút `Nhận xét AI` disable khi chưa có `report` (backend sẽ 409).
4. Chấm lại → reset cả 2 panel về đóng (ẩn mặc định).
5. Bản heuristic (không `word_details`) → bảng hiện dòng "Chưa có chi tiết từng chữ".

## 3. Demo & test

- Test: `ReadingScoreCard.test.jsx` — 4 case (chưa chấm / ẩn mặc định / mở bảng / panel feedback độc lập), dữ liệu mẫu inline trong file test.
- Chạy:

```bash
cd frontend
npx vitest run src/features/profile/ReadingScoreCard.test.jsx
npm run build        # verify build
```

## 4. Gắn backend (đã gắn ở Assessment)

`SessionScoringView` gọi thật:

```js
await fetchJson(`/rooms/${roomId}/speech-logs/${messageId}/score`, { method: 'POST' });
await fetchJson(`/rooms/${roomId}/speech-logs/${messageId}/feedback`, { method: 'POST', body: {} });
```

`PATCH .../speech-logs/{message_id}` khi user sửa câu. `ReadingScoreCard` giữ nguyên — nó chỉ đọc `utterance.pronunciation` / `utterance.feedback` theo đúng schema `SpeechUtterance`.

## 5. Session wiring + DB + chấm tuần tự (v2.1)

- **Máy host tự tính**: scorer local (wav2vec2 + XLSR phoneme) chạy trên backend máy host.
  `PRONUN_BASE_URL` để trống. TTS (`:8002`) và STT (`:8001`) chạy Docker cùng máy host.
- **Chấm tuần tự**: `threading.Semaphore(SCORING_MAX_PARALLEL=1)` quanh `score_local`
  (`app/ai/pronunciation.py`) — 3-4 người bấm chấm cùng lúc thì xếp hàng, không OOM.
  Frontend khóa các nút chấm khác khi đang có 1 lượt chạy (`scoreDisabled`).
- **Điểm vào DB**: bảng `pronunciation_scores` (`app/models/pronunciation_score.py`,
  tự tạo bởi `create_all`). POST `.../score` upsert (chấm lại cùng câu không đẻ dòng mới,
  reset feedback cũ); POST `.../feedback` điền `feedback_json`. JSONL giữ làm log raw/audio.
  Lỗi ghi DB không làm rớt điểm vừa chấm (log warning).
- **Session**: `SessionDetailPage` đọc `GET /rooms/{id}/speech-logs/me`, lọc theo
  `joined_at–left_at`, render `ReadingScoreCard` từng câu (mục *My pronunciation scores*).
- **AI feedbacks**: `POST /sessions/{id}/feedback` — gộp câu đã chấm trong session (đọc DB,
  fallback JSONL cho điểm cũ), gửi LLM local với `SESSION_FEEDBACK_PROMPT` (mục ## session trong feedback.md, gọn ~120 từ,
  chỉ nêu từ sai/mất hơi + tip + 3 bước luyện). Chưa chấm câu nào → 409.
- **Nghe mẫu**: mỗi dòng *What was said* có nút loa (Kokoro `POST /tts/speak`, cache theo
  giọng+câu) + `VoicePicker` 4 giọng (Heart/Adam/Emma/George). Giọng chỉ ảnh hưởng phần
  nghe, **không đổi điểm** (scorer không so sánh audio TTS — DTW vs Kokoro hoãn v1.1).
