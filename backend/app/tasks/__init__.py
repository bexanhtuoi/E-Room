# Tên task Celery ("app.ai.tasks.*") giữ nguyên để tương thích beat schedule
# và job đang xếp hàng — chỉ đổi module chứa code sang app.tasks.*.
from app.tasks.helpers import (
    WORKER_LOCK_TTL,
    claim_worker_lock,
    clear_stale_worker_locks,
    format_room_message,
    get_activity_key,
    get_pending_key,
    get_running_key,
    mark_room_activity,
    publish_task,
    recent_room_context,
    refresh_worker_lock,
    release_worker_lock,
)
from app.tasks.maintenance import (
    check_room_heartbeats,
    delete_expired_scheduled_rooms,
    end_stale_empty_rooms,
    ensure_room_workers,
)
from app.tasks.room_jobs import (
    enqueue_ai_job,
    enqueue_room_observer,
    enqueue_room_transcriber,
    observe_room_audio,
    stream_ai_response,
    transcribe_room_audio,
)
from app.tasks.scoring import score_room_utterance, score_room_utterances, score_single_utterance

__all__ = [
    "WORKER_LOCK_TTL",
    "check_room_heartbeats",
    "claim_worker_lock",
    "clear_stale_worker_locks",
    "delete_expired_scheduled_rooms",
    "end_stale_empty_rooms",
    "enqueue_ai_job",
    "enqueue_room_observer",
    "enqueue_room_transcriber",
    "format_room_message",
    "get_activity_key",
    "get_pending_key",
    "get_running_key",
    "mark_room_activity",
    "observe_room_audio",
    "publish_task",
    "recent_room_context",
    "refresh_worker_lock",
    "release_worker_lock",
    "score_room_utterance",
    "score_room_utterances",
    "score_single_utterance",
    "stream_ai_response",
    "transcribe_room_audio",
]
