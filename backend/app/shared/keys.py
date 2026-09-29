"""Redis key builders dùng chung (presence, jobs, locks, RAG tags)."""


def room_presence_key(room_id: int) -> str:
    return f"room:{room_id}:participants"


def room_pending_key(room_id: int) -> str:
    return f"room:{room_id}:ai_pending"


def room_running_key(room_id: int) -> str:
    return f"room:{room_id}:ai_running"


def room_activity_key(room_id: int) -> str:
    return f"room:{room_id}:last_activity"


def room_heartbeat_key(room_id: int) -> str:
    return f"room:{room_id}:heartbeat_pending"


def room_observer_lock_key(room_id: int) -> str:
    return f"room:{room_id}:observer_running"


def room_transcriber_lock_key(room_id: int) -> str:
    return f"room:{room_id}:transcriber_running"


def room_tag(room_id: int) -> str:
    return f"room:{room_id}"
