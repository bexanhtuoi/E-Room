# Báo cáo thay đổi wav2vec từ khi pull code về

Ngày lập: 11/10/2026 — Nhánh: `master` — HEAD: `b85b359 fix: loadtest quote comma args`

Phạm vi: toàn bộ thay đổi ở working-tree so với HEAD (chưa commit), trọng tâm là `backend/app/ai/pronunciation/` (wav2vec/XLSR).

## 1. Vấn đề hiện tại trước khi dọn

1. Còn 2 model song song: `wav2vec2-base-960h` (CTC chữ) + `xlsr-53-espeak` (phoneme GOP). Tốn RAM/VRAM, code rẽ nhánh `char_words/greedy` khó bảo trì.
2. `blank_ratio > 0.70` chấm 0 oan cho từ đọc rõ (posterior XLSR vốn peaky).
3. `feedback LLM` chết thì `raise RuntimeError` gây 502, mất trải nghiệm chấm.
4. Lỗi style vi phạm rules: `F841 flat` chưa dùng ở `align.py:39`, typing trộn `str | None` với `Optional`, `list` với `List`, import chưa gọn, tên `_FEEDBACK_NAMES`/`_embed_model` có `_` đầu, `except Exception: pass` nuốt lỗi ở `services/speech.py`.
5. EC2 còn preload cả `wav2vec-base` trong khi backend đã XLSR-only — không thống nhất.

## 2. Thông tin hữu ích thu thập được

- Nguồn chính: `git status`, `git diff --stat`, `git log --oneline -8`, đối chiếu `rules/python-coding-style.md`, `rules/backend-architecture.md`, `rules/api-design.md`.
- Công cụ đã dùng: `uv run ruff check`, `uv run pytest tests/unit/test_architecture.py`, script kiểm thử nhẹ `align/heuristic/fluency/score_pronunciation` không cần GPU.
- Kết quả đo trước khi sửa: `ruff` báo `1 F841 unused-variable (flat)`; test kiến trúc pass 7/7 ở nhóm Router/Layer nhưng còn nợ style typing.

## 3. Cách giải quyết và công cụ đã dùng

### 3.1. Thống nhất kiến trúc XLSR-only (kế thừa từ diff đã có + bổ sung)

| File | Thay đổi |
|---|---|
| `backend/app/ai/pronunciation/models.py` | Xóa `acoustic_lock/ctc_processor/acoustic_model`, `acoustic_model_id()`, `get_acoustic_model()`. Chỉ giữ `phone_fe/phone_model/phone_vocab` + thêm `is_phone_ready()`, `ensure_phone_ready()` fail-fast tiếng Việt. |
| `backend/app/ai/pronunciation/scorer.py` | Xóa `split_words_with_spans`, CTC chữ, `normalize_reference/score_utterance`. Thêm `apply_xlsr_spans()`, `score_local()` + gate `threading.Semaphore`, `score_via_pronun_service()`, giữ `score_with_wav2vec2()` làm wrapper tương thích test/mocks. |
| `backend/app/ai/pronunciation/phonemes.py` | `score_phones()` validate audio (rỗng/<0.2s/>10 phút), resample về 16k, `try` quanh `fe()` và `model()` kèm dọn CUDA OOM, tính `blank_ratio`, giữ `misaligned` để chấm GOP thay vì 0. Tổng hợp `sounds` theo trọng số `n_phones`, thêm `pronunciation_error`. |
| `backend/app/ai/pronunciation/__init__.py` | Đổi export `get_acoustic_model/normalize_reference/score_utterance` thành `ensure_phone_ready/is_phone_ready/apply_xlsr_spans`. Đổi `_FEEDBACK_NAMES` thành `FEEDBACK_NAMES` cho đúng luật không `_` đầu. |
| `backend/app/config.py`, `backend/.env.example` | Xóa `WAV2VEC_MODEL_ID`, sửa comment thành `XLSR phoneme GOP only, wav2vec-base đã xóa`. |
| `backend/app/main.py` | `lifespan` preload `ensure_phone_ready()`, log `Model XLSR đã sẵn sàng`, lỗi thì warning để lần chấm đầu tải. |
| `backend/ec2/config.py`, `backend/ec2/.env.example` | Xóa `wav2vec_model_id`/`WAV2VEC_MODEL_ID` chết (không còn ai đọc). |
| `backend/ec2/Dockerfile` | Chỉ bake `wav2vec2-xlsr-53-espeak-cv-ft` + `AutoFeatureExtractor`, bỏ `wav2vec2-base-960h`/`Wav2Vec2Processor`. Sửa comment thành `XLSR-only + Qwen3`. |
| `backend/ec2/models.py` | `warm_all()` chỉ gọi `get_phone_model()`. Đổi `_embed_model` thành `embed_model_cache` cho đúng luật tên. |
| `backend/app/services/speech.py` | `utterance_needs_heavy_scoring()` thay `except: pass` bằng `log.warning` có `room/msg/err`. |

### 3.2. Làm sạch code dư thừa (đợt này)

- Xóa biến `flat` không dùng ở `align.py:39` — hết lỗi `F841`, `ruff check` chuyển sang `All checks passed!`.
- Thống nhất typing theo luật `Optional/List/Dict/Tuple` thay vì `str | None`, `list`, `dict`, `tuple`: `align.py`, `metrics.py`, `audio.py`, `g2p.py`, `models.py`, `phonemes.py`, `scorer.py` (giữ `Union[Path, str]` để không gãy caller truyền `str`).
- Chuẩn hóa chữ ký nhiều dòng (`score_fluency`, `vad_segments`, `score_sounds`, `score_stress`, `score_attempt_v2`) và comment đánh số tiếng Việt (`1. Vá span`, `1. Validate audio`, `2. OOM`, `3. Canonical`, `4. GOP`, `5. Observed`, `6. Evidence`, `7. Tổng hợp`).
- Sửa import: thêm `typing` đúng nhóm stdlib → third-party → local; sửa comment `FRAME_STRIDE_S` sang tiếng Việt.
- Giữ lại có chủ đích (không xóa để tránh gãy): `score_sounds/score_word_sounds/observe_phones_fallback` (đường char cũ, hiện không ai gọi nhưng còn export), `score_with_wav2vec2` (wrapper giữ tên cũ cho test/mocks).

## 4. Kết quả sau khi làm

### 4.1. Kiểm thử đã chạy

- `uv run ruff check app/ai/pronunciation/ app/services/speech.py ec2/` → **All checks passed!**
- `uv run pytest tests/unit/test_architecture.py -k "RouterLayer or LayerDirections"` → **7 passed** (không `HTTPException`/DB/ai-import trong routers, đúng chiều tầng, `shared` là lá).
- Smoke-test nhẹ không cần model:
  - `tok_words`, `align_transcripts` (2 match), `heuristic_score` (87.8), `score_fluency` (90.0), `calculate_overall` (84.2), `score_pronunciation(audio_path=None)` fallback `reason=no_audio` → **ALL LIGHT TESTS OK**.
  - `import app.ai.pronunciation` (46 exports), `speech_service`, `ec2.config` (đã hết `wav2vec_model_id`), `PHONE_MODEL_ID` đọc đúng.
- `ruff format --check` vẫn báo reformat 11 file — **cố ý không chạy** vì project dùng luật riêng (dòng trống sau mỗi câu lệnh), `ruff format` sẽ phá style này.

### 4.2. Thống kê diff so với HEAD (`git diff --stat`)

```
 backend/.env.example                     |   1 -
 backend/app/ai/pronunciation/__init__.py |  17 +-
 backend/app/ai/pronunciation/align.py    |  18 +-
 backend/app/ai/pronunciation/audio.py    |  17 +-
 backend/app/ai/pronunciation/g2p.py      |  15 +-
 backend/app/ai/pronunciation/metrics.py  |  19 +-
 backend/app/ai/pronunciation/models.py   |  93 +++-----
 backend/app/ai/pronunciation/phonemes.py | 165 +++++++++----
 backend/app/ai/pronunciation/scorer.py   | 393 +++++++------------------------
 backend/app/config.py                    |   5 +-
 backend/app/main.py                      |   9 +
 backend/app/services/speech.py           |   9 +-
 backend/ec2/.env.example                 |   1 -
 backend/ec2/Dockerfile                   |   9 +-
 backend/ec2/config.py                    |   1 -
 backend/ec2/models.py                    |  13 +-
 16 files changed, 327 insertions(+), 458 deletions(-)
```

Chưa commit thêm: `backend/scripts/benchmark_scoring_regression.py`, `backend/scripts/profile_scoring.py` (file mới untracked).

### 4.3. Đối chiếu rules

- **Python style:** đạt giãn cách, logging placeholder, tiếng Việt, type-hint thống nhất. Ngoại lệ còn lại: cache model toàn cục (`torch_lib/phone_fe/phone_model/phone_vocab`) vẫn là biến global mutable — giữ vì là singleton model có `phone_lock`, refactor thành class sẽ đụng nhiều caller nên để đợt sau.
- **Backend architecture:** đạt routers mỏng, services `SpeechService(ServiceBase)` + singleton + lỗi domain, `ai` chia package + `helpers`, `__init__` re-export. Nợ nhẹ: `scorer.py` ~400 dòng, nên chẻ `heuristic/report` ra file riêng đợt sau.
- **API design:** đạt response trực tiếp + `response_model`, fallback `reason=no_audio/quiet_audio/scorer_failed` thay vì 500, không `HTTPException` trong service.

## 5. Việc còn đề xuất đợt sau

1. Bọc cache model thành `PhoneModelHolder` singleton để hết hẳn global mutable.
2. Chẻ `scorer.py` (<300 dòng): tách `heuristic/report_to_hook` sang `helpers.py`.
3. Xóa hẳn đường char cũ (`score_sounds/score_word_sounds`) sau khi xác nhận không còn client ngoài dùng.
4. Chạy full `pytest` (hiện timeout do tải torch/librosa) trên máy có GPU/cache đầy đủ trước khi merge.
