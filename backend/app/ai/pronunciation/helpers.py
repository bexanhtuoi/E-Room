import math
import re
from typing import Dict, List, Optional


def tok_words(text: str) -> list[str]:
    return [w for w in re.findall(r"[A-Za-z']+", (text or "").lower())]


def gop_to_score(g: float) -> float:
    # 1. Chuẩn hoá GOP log-posterior về 0-100 đỡ gắt hơn exp thô
    if not math.isfinite(g):
        return 0.0

    s = 100.0 * (1.0 + g / 4.0)

    return round(max(0.0, min(100.0, s)), 1)


def is_gb_accent(accent: Optional[str]) -> bool:
    # 2. Nhận diện Anh-Anh để dùng chuẩn non-rhotic
    a = (accent or "").strip().lower()

    return a.startswith("en-gb") or a.startswith("en_uk") or a == "uk"


def build_stt_span_map(word_spans: Optional[List[Dict]]) -> Dict[str, List[List[float]]]:
    # 3. Gom span STT theo từ để neo biên khi CTC bóp quá ngắn
    out: Dict[str, List[List[float]]] = {}

    for item in word_spans or []:
        if not isinstance(item, dict):
            continue

        nested = item.get("words")

        if isinstance(nested, list):
            for w in nested:
                if isinstance(w, dict):
                    push_span(out, w)
        else:
            push_span(out, item)

    return out


def push_span(out: Dict[str, List[List[float]]], w: Dict) -> None:
    # 4. Đẩy một span STT vào map theo từ viết hoa
    key = str(w.get("word", "")).strip().strip(".,!?;:\"'()").upper()

    if not key:
        return

    try:
        s = float(w.get("start", w.get("start_s", 0.0)))

        e = float(w.get("end", w.get("end_s", 0.0)))
    except (TypeError, ValueError):
        return

    if e <= s:
        return

    out.setdefault(key, []).append([s, e])

