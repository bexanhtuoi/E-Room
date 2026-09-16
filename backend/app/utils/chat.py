import json
import re
from typing import Optional

AI_MENTION_PATTERN = re.compile(r"(?:^|\s)@ai\b", re.IGNORECASE)


def strip_ai_mention(text: str) -> Optional[str]:
    stripped = (text or "").lstrip()
    match = AI_MENTION_PATTERN.search(stripped)

    if match is None:
        return None

    query = stripped[match.end():].strip()

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
