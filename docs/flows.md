# E-Room — Luồng kỹ thuật (Flows)

> Cập nhật: 09/2026 · Tài liệu này mô tả chính xác process nào làm gì, qua queue/key/DB nào.
> Ký hiệu: `api`, `ai-worker`, `ai-transcriber`, `ai-observer`, `ai-beat` là 5 container riêng,
> chỉ gặp nhau ở Redis (hàng đợi + trạng thái) và TiDB (kết quả). Không có HTTP nội bộ giữa chúng.

## 0. Bản đồ nhanh

```
Browser ──HTTP──▶ nginx:8080 ──┬── / ──▶ frontend:3000
                               ├── /api ──▶ api:8000 (routers → services → repositories → TiDB)
                               └── /rtc ──▶ livekit:7880
Browser ◀──WebRTC──▶ LiveKit (Cloud hoặc self-host) ◀── ai-transcriber / ai-observer

api ──RPUSH──▶ Redis lists: ai | ai_transcriber | ai_observer
ai-beat ──RPUSH (15s/60s/24h)──▶ cùng các list trên
ai-worker (x4) ◀──BRPOP── ai │ ai-transcriber (threads x50) ◀── ai_transcriber
ai-observer (x2) ◀── ai_observer
```

Giám sát realtime: đang chọn tool (xem mục đánh giá monitor) — tạm thời dùng `docker logs` + Redis trực tiếp.

## 1. Vào / rời phòng

```
POST /api/v1/rooms/{id}/join (idempotent)
 → Redis SADD room:{id}:participants {user_id} + SET room:{id}:last_activity=now
 → DB rooms.status idle→active (người đầu) + sessions mở ca mới
 → RPUSH ai_transcriber {transcribe_room_audio} + RPUSH ai_observer {observe_room_audio}

POST /api/v1/rooms/{id}/leave (hoặc webhook participant_left)
 → Redis SREM room:{id}:participants
 → hết người: DB rooms→idle + sessions đóng ca + RPUSH ai {score_room_utterances}
```

- `sadd`/`srem` nguyên tử — 2 người join cùng lúc không đếm sai.
- `claim_seat` chặn vượt 6 ghế (token endpoint check lại lần nữa).
- Webhook là đường dự phòng khi tab tắt đột ngột (bỏ qua prefix `ai_`).

## 2. Nói → chữ (transcript)

```
Mic → LiveKit room (WebRTC, không qua api)
 → ai-transcriber subscribe track (trừ ai_*, mỗi người 1 luồng + 1 VAD state)
 → Silero VAD cắt câu (im STT_VAD_SILENCE_SECONDS chốt; STT_VAD_THRESHOLD=0.5)
 → song song: RawAttemptRecorder ghi attempts/{id}/raw.wav
 → stt_executor (16 threads) POST whisper server :8001 (timeout STT_SERVER_TIMEOUT=30s)
    ├─ chết/rỗng → local nếu STT_LOCAL_ENABLED (docker: false → bỏ câu)
    └─ tắc ≥16 câu chờ → tràn cloud (tiếng Anh + có key)
 → TiDB messages (source=speech_to_text) + JSONL + broadcast LiveKit data
```

- Nói chỉ ra chữ, **không gọi AI** (trigger giọng nói đã gỡ — chỉ chat `@ai` mới gọi).
- Câu trùng trong 10s, câu rỗng, hallucination → bỏ.
- Utterance `.wav` upload MinIO ngay (`speech/room_{id}/audio/`, ref `s3:...` trong JSONL);
  MinIO chết → ghi đĩa local như cũ.

## 3. Hỏi `@ai` (chat)

```
POST /api/v1/messages/ {room_id, text="@ai ..."} → 201 (ghi DB messages trước)
 → RPUSH ai {stream_ai_response(room, "chat", query, source_message_id)}
 → ai-worker: trừ room:{id}:ai_pending, giữ room:{id}:ai_running (chống 2 thợ 1 câu)
 → đọc 20 câu gần nhất + documents (tag room:{id}) + tools [retrieval, web_search, transcript_*]
 → stream reasoning → LiveKit data → stream tokens → LiveKit data
 → ghi DB messages (role=ai) + xóa ai_running
 → browser poll 4s đón bản chính (phòng khi rớt stream)
```

- Hàng `ai` không giới hạn — đông thì xếp hàng, van duy nhất là `AI_TIMEOUT_SECONDS=900s`.
- Hết quota OpenRouter (20/phút, 50–1.000/ngày) → 429, log `ai-worker`.

## 4. Beat: heartbeat + điểm danh + dọn dẹp

```
ai-beat (không nhặt việc, chỉ đẻ giấy):
 15s  check_room_heartbeats → ai-worker: phòng active + ≥2 người + im >45s
       + chưa hỏi (room:{id}:heartbeat_pending) → RPUSH ai {stream_ai_response(..., "heartbeat")}
       + phòng trống quá ROOM_EMPTY_END_SECONDS → DB rooms→ended
       + phòng hẹn quá 24h → xóa hẳn
  60s  ensure_room_workers → ai-worker: phòng active còn người mà mất khóa
       transcriber/observer_running → phát lại giấy nghe/coi (tự hồi sau restart)
```

## 5. Chấm điểm phát âm

```
PATCH .../speech-logs/{mid} {corrected_text} → reset pronunciation+feedback (JSONL + DB)

POST .../speech-logs/{mid}/score
 ├─ nhẹ (không audio) → chấm sync tại api (heuristic), trả report ngay
 └─ nặng (có wav) → RPUSH ai {score_single_utterance} → 202 {queued}
     → ai-worker (tuần tự): tải wav (local hoặc MinIO→temp, xóa sau)
     → wav2vec2-base + xlsr forced-align + GOP → sounds/stress/fluency/completeness/overall
     → articulation.py gắn how_to/vi → upsert pronunciation_scores + attach JSONL
     → browser poll 3s
     → no_audio / scorer_failed: giữ điểm cũ, không ghi đè

POST .../feedback → cần pronunciation.report (chưa chấm → 409 NO_SCORE_REPORT)
 → LLM giải thích report (cấm đổi điểm/bịa lỗi) → attach JSONL + DB
 → LLM chết → fallback rule-based từ how_to/vi

POST /sessions/{sid}/feedback → gom câu đã chấm trong ca (DB, fallback JSONL)
 → prompt assessment.md → gọn, chỉ nêu phần sai (chưa chấm câu nào → 409)
```

- Tan phòng (người cuối out) → RPUSH ai {score_room_utterances} → chấm vét.
- Model chấm (~1.6GB) nạp lười trong worker, recycle mỗi 100 tasks.

## 6. Session chat (hỏi đáp transcript)

```
POST /sessions/{sid}/chat (sync) | /chat/stream (SSE thinking|token|error)
 → agent chỉ có tools transcript_* + prompt session.md (Recap/Analyze/Q&A, sạch tiếng Anh)
 → transcript ca đó + 20 turns chat cũ làm context
```

## 7. Upload tài liệu RAG

```
POST /rooms/{id}/documents (host, pdf/md/txt ≤10MB)
 → MinIO documents/room_{id}/{uuid}_{tên} → chunk + embed + Qdrant tag room:{id}
 → agent chỉ search đúng tag phòng đó + rerank Qwen3
```

## 8. MinIO buckets/keys

```
eroom/
 ├── avatars/{user_id}                        1 user 1 file, ghi đè
 ├── documents/room_{id}|general/{uuid}_{tên}  theo phòng (DB documents.file_path)
 └── speech/room_{id}/audio|attempts/...       theo phòng (JSONL/metadata giữ ref s3:)
```

Test dùng bucket riêng `eroom-test` (conftest tự flush), không lẫn production.

## 9. Ghi chú vận hành (case thật đã gặp)

| Hiện tượng | Nguyên nhân / xử lý |
|---|---|
| Test đỏ `Connection closed by server` hàng loạt | Đường host→container gãy sau reboot WSL → `docker restart redis` (tương tự tidb/nginx) |
| api CPU cao lúc rảnh | Do uvicorn `--reload` nạp lại sau mỗi lần sửa file qua bind-mount (đo thật ~0.4% lúc yên). Prod public nên cân nhắc `APP_ENV=production` để tắt reload |
| Score treo `queued` | Worker `ai` chết hoặc Redis chết → `docker ps`, restart đúng container đó |
| Chữ ra chậm theo số phòng live | Hết thợ nghe → tăng `ai-transcriber` concurrency (threads, rẻ RAM) |
| Spinner chấm lâu + RAM vọt | Chấm tuần tự 1/lần là thiết kế; vượt tải thì trỏ `PRONUN_BASE_URL` sang server chấm riêng |
| `@ai` 429 | Hết quota OpenRouter → nạp $10 (50→1.000/ngày) + làm fallback chain model |
| Phòng kẹt `active` không ai | Tên ma trên bảng ghi danh → vào lại rồi Leave cho sạch |
