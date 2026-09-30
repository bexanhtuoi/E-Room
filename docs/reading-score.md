# Chấm điểm đọc bằng AI — logic & thiết kế UI

> Cập nhật: 09/2026 · Quy ước UX đã khóa: **điểm từng chữ bị ẨN mặc định sau khi chấm**.
> Muốn xem phải bấm **Thống kê điểm số** (bảng riêng).
> **Nhận xét AI** là nút độc lập thứ hai.

## 1. Luồng chấm điểm (backend — đã verify code)

```
Mic/user ──▶ VAD cắt câu ──▶ Whisper STT (raw, pronunciation=None)
      ──▶ user sửa corrected_text (PATCH)
      ──▶ POST .../score  → chấm trên corrected_text + audio ĐẦU–CUỐI lượt nói
          ├─ nặng → 202 {queued} (task scoring chạy nền)
          └─ nhẹ → chấm sync, trả report ngay
      ──▶ POST .../feedback → LLM đọc ScoringReport đã lưu, không chấm lại
```

Prefix đầy đủ: `/api/v1/rooms/{room_id}/speech-logs/...`.

| Bước | API | Luật |
|---|---|---|
| Sửa câu | `PATCH .../speech-logs/{message_id}` `{corrected_text}` | Chỉ câu của mình (hoặc host/admin). Sửa sau khi đã chấm → `pronunciation` + `feedback` reset về `None`, bắt chấm lại (`app/ai/stt/speech_log.py::update_corrected_text`) |
| Chấm điểm | `POST .../speech-logs/{message_id}/score` | Dùng audio ĐẦU–CUỐI của attempt + toàn bộ `corrected_text` lượt nói. Audio nặng → enqueue `score_single_utterance` (queue `ai`) → `202 {queued:true}`; nhẹ → chấm sync (`app/tasks/scoring.py::score_room_utterance`) |
| Nhận xét | `POST .../speech-logs/{message_id}/feedback` | Chỉ chạy khi đã có `pronunciation.report`; chưa chấm → **409** `{"code": "NO_SCORE_REPORT"}` |

### Mã lỗi / trạng thái cần biết (UI xử lý)

| Mã | Nghĩa | UI làm gì |
|---|---|---|
| `202 {queued:true}` | Đang chấm nền | Hiện spinner, poll lại câu đó |
| `409 NO_SCORE_REPORT` | Xin feedback khi chưa chấm | Disable nút **Nhận xét AI** khi chưa có report |
| `no_audio` (reason) | Câu không có audio để chấm | Báo "không có audio", giữ nguyên |
| `scorer_failed` (reason) | Scorer crash | Báo lỗi, **giữ điểm cũ**, không ghi đè |
| `409` session feedback | `POST /sessions/{id}/feedback` khi chưa chấm câu nào | Báo "hãy chấm ít nhất 1 câu trước" |

### Scorer (deterministic, không phải LLM)

`app/ai/pronunciation/scorer.py::score_pronunciation` trả `ScoringReport`:

- `scores`: `sounds` (âm), `stress` (nhấn), `fluency` (trôi chảy), `completeness` (đủ chữ), `overall` (trung bình trọng số). `intonation` = `None` ở MVP (chỉ detect monotone).
- `word_details[]`: `{word, score, status, expected_ipa}` — `status` ∈ `ok` (≥70) · `pronunciation_error` · `no_evidence` (loại khỏi mẫu số, UI hiện "Không nghe rõ").
- `phonemes[]`: `{word, expected, observed, type, gop, score}` — vd `/θ/ → /s/` ở "think".
- `top_errors[]`: `{pattern, count, examples}` — tối đa 5.
- Thứ tự thử model: local wav2vec2 (forced-align + `score_sounds`/`score_stress`, fluency/completeness) → Pronun service (`PRONUN_BASE_URL`) → heuristic chữ (không có `word_details`).
- Mỗi từ yếu được gắn hướng dẫn sửa từ `articulation.py`: `how_to` (khẩu hình tiếng Việt) + `vi` (phiên âm Việt để đọc theo).

### Nhận xét AI (LLM — chỉ giải thích, không tính điểm)

`app/ai/pronunciation/feedback.py::generate_feedback` nhận **đúng 1 JSON `scoring_report`**, bị cấm đổi điểm / bịa lỗi (luật trong `app/ai/prompts/feedback_utterance.md` cho từng câu, `assessment.md` cho cả session).
Trả: `summary`, `pronunciation_feedback`, `stress_feedback`, `intonation_feedback`,
`fluency_feedback`, `priority_errors[]`, `practice_plan[]` (hoặc `feedback_raw` khi model trả text thô).
LLM chết → fallback rule-based `build_fallback_feedback` (vẫn có tip từ `how_to`/`vi`), không bao giờ làm rớt request.

## 2. Thiết kế UI (frontend)

Component: `frontend/src/features/profile/ReadingScoreCard.jsx`
(props: `utterance {text, corrected_text, pronunciation, feedback}`, `onScore`, `onFeedback`, `scoring`, `feedbackLoading`)

Dùng ở: Assessment (`/assessment/:sessionId` → `SessionScoringView`) và trang session (`/session/:id` → `SessionDetailPage`, mục *My pronunciation scores*, lọc theo `joined_at–left_at`).

### Trạng thái

| State | Hiển thị |
|---|---|
| Chưa chấm (`pronunciation == null`) | Hướng dẫn + nút **Chấm điểm AI** |
| Đang chấm nền (`202 queued`) | Spinner + poll lại, khóa các nút chấm khác (`scoreDisabled`) |
| Đã chấm | Câu chấm **hiển thị trơn** (không tô màu/badge từng chữ) + 4 thanh tiêu chí + điểm tổng + tip từ yếu (`how_to`/`vi`) + **2 nút độc lập** |
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

## 4. Gắn backend (đã gắn ở Assessment + Session)

`SessionScoringView` gọi thật (prefix `/api/v1`):

```js
await fetchJson(`/api/v1/rooms/${roomId}/speech-logs/${messageId}/score`, { method: 'POST' });
await fetchJson(`/api/v1/rooms/${roomId}/speech-logs/${messageId}/feedback`, { method: 'POST', body: {} });
```

`PATCH .../speech-logs/{message_id}` khi user sửa câu. `ReadingScoreCard` giữ nguyên — nó chỉ đọc `utterance.pronunciation` / `utterance.feedback` theo đúng schema `SpeechUtterance`. Lỗi client đọc qua `toApiError` (lấy `code`, fallback `detail`).

## 5. Session wiring + DB + chấm tuần tự

- **Máy host tự tính**: scorer local (wav2vec2 + XLSR phoneme) chạy trên backend máy host.
  `PRONUN_BASE_URL` để trống. TTS (`:8002`) và STT (`:8001`) chạy ở máy AI riêng.
- **Chấm tuần tự**: `SCORING_MAX_PARALLEL=1` — nhiều người bấm chấm cùng lúc thì xếp hàng (task Celery), không OOM.
  Frontend khóa các nút chấm khác khi đang có 1 lượt chạy (`scoreDisabled`).
- **Điểm vào DB**: bảng `pronunciation_scores` (`app/models/pronunciation_score.py`).
  POST `.../score` upsert (chấm lại cùng câu không đẻ dòng mới, reset feedback cũ);
  POST `.../feedback` điền `feedback_json`. JSONL giữ làm log chữ + trỏ audio;
  file `.wav` nằm trên MinIO (`speech/room_{id}/...`, ref `s3:...` trong JSONL/metadata,
  local chỉ là cache — MinIO chết thì tự rớt về local). Script migrate file cũ:
  `backend/scripts/migrate_speech_to_minio.py`.
  Lỗi ghi DB không làm rớt điểm vừa chấm (log warning).
- **Session**: `SessionDetailPage` đọc `GET /api/v1/rooms/{id}/speech-logs/me`, lọc theo
  `joined_at–left_at`, render `ReadingScoreCard` từng câu (mục *My pronunciation scores*).
- **AI feedbacks cả session**: `POST /api/v1/sessions/{id}/feedback` — gộp câu đã chấm trong session (đọc DB,
  fallback JSONL cho điểm cũ), gửi LLM với prompt `assessment.md` (gọn, chỉ nêu phần sai
  kèm quote + cách sửa + bước luyện). Chưa chấm câu nào → 409. Chỉ chính chủ / host / admin.
- **Nghe mẫu**: mỗi dòng *What was said* có nút loa (`POST /api/v1/tts/speak` của backend,
  backend gọi tiếp server `:8002`, cache theo giọng+câu) + `VoicePicker` 4 giọng
  (`af_heart`/`am_adam`/`bf_emma`/`bm_george`). Giọng chỉ ảnh hưởng phần nghe, **không đổi điểm**.
