import json
from typing import Optional


def strip_ai_mention(text: str) -> Optional[str]:
    lowered = (text or "").lstrip().lower()
    if "@ai" not in lowered:
        return None

    query = (text or "").lstrip()[lowered.find("@ai") + 3 :].strip()
    return query or None


def scrub_meta(raw) -> Optional[str]:
    if not raw:
        return raw

    try:
        meta = json.loads(raw) if isinstance(raw, str) else dict(raw)
    except (TypeError, ValueError):
        return None

    meta.pop("session_chat", None)
    meta.pop("session_id", None)
    return json.dumps(meta) if meta else None
