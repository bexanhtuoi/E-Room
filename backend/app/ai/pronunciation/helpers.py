import math
import re
from typing import Dict, List, Optional, Tuple


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


def flat_stt_words(word_spans: Optional[List[Dict]]) -> List[Dict]:
    # 5. Trải span STT (phẳng hoặc theo segment) về list từ theo thứ tự
    flat: List[Dict] = []

    for item in word_spans or []:
        if not isinstance(item, dict):
            continue

        nested = item.get("words")

        if isinstance(nested, list):
            for w in nested:
                if isinstance(w, dict) and w.get("word"):
                    flat.append(w)
        elif item.get("word"):
            flat.append(item)

    return flat


def word_time(word: Dict) -> Tuple[float, float]:
    # 6. Lấy biên thời gian một từ STT, chịu được nhiều key
    try:
        s = float(word.get("start", word.get("start_s", 0.0)))

        e = float(word.get("end", word.get("end_s", 0.0)))
    except (TypeError, ValueError):
        return (0.0, 0.0)

    return (s, e)


def trim_edge_pauses(
    pauses: List[Tuple[float, float]],
    duration_s: float,
) -> Tuple[List[Tuple[float, float]], int]:
    # 7. Bỏ silence đầu/cuối file thu, không phải ngập ngừng
    kept: List[Tuple[float, float]] = []

    dropped = 0

    for s, e in pauses or []:
        if s <= 0.05 or e >= max(0.0, duration_s - 0.05):
            dropped += 1

            continue

        kept.append((s, e))

    return kept, dropped


def speech_span(
    word_spans: Optional[List[Dict]] = None,
    segs: Optional[List[Tuple[float, float]]] = None,
    duration_s: float = 0.0,
) -> Tuple[float, float]:
    # 9. Khung nói thật: từ chữ đầu tới chữ cuối, silence đầu/cuối không bao giờ tính
    flat = flat_stt_words(word_spans)

    bounds: List[Tuple[float, float]] = []

    for w in flat:
        s, e = word_time(w)

        if e > s:
            bounds.append((s, e))

    if bounds:
        return (min(s for s, _ in bounds), max(e for _, e in bounds))

    if segs:
        return (float(segs[0][0]), float(segs[-1][1]))

    return (0.0, max(0.0, duration_s))


def filter_speech_pauses(
    pauses: List[Tuple[float, float]],
    duration_s: float,
    span_start: Optional[float] = None,
    span_end: Optional[float] = None,
) -> Dict[str, object]:
    # 10. Bỏ pause đầu/cuối câu, pause giữa nguyên vẹn để rubric gốc chấm
    lo = span_start if span_start is not None else 0.0

    hi = span_end if span_end is not None else max(0.0, duration_s)

    out: List[Tuple[float, float]] = []

    n_edge = 0

    for s, e in pauses or []:
        if e <= lo or s >= hi:
            n_edge += 1

            continue

        a, b = max(s, lo), min(e, hi)

        if a <= lo + 0.05 or b >= hi - 0.05:
            n_edge += 1

            continue

        out.append((a, b))

    return {"pauses": out, "n_edge": n_edge}


def punct_gaps(
    word_spans: Optional[List[Dict]] = None,
    text: str = "",
) -> List[Tuple[float, float, str]]:
    # 11. Khe nghỉ ở từng dấu câu kèm dấu, lấy theo timestamp STT
    flat = flat_stt_words(word_spans)

    pairs = [(m.group(1).lower(), m.group(2) or "") for m in re.finditer(r"([A-Za-z']+)([.,;:?!]+)?", text or "")]

    lows = [str(w.get("word", "")).strip().strip(".,!?;:\"'()").lower() for w in flat]

    if len(lows) != len(pairs):
        return []

    if any(a != b for a, b in zip(lows, [p[0] for p in pairs])):
        return []

    gaps: List[Tuple[float, float, str]] = []

    for idx in range(len(flat) - 1):
        if not pairs[idx][1]:
            continue

        _, e0 = word_time(flat[idx])

        s1, _ = word_time(flat[idx + 1])

        if s1 > e0:
            gaps.append((e0, s1, pairs[idx][1]))

    return gaps


def check_punct_pause_order(
    word_spans: Optional[List[Dict]] = None,
    text: str = "",
) -> Dict[str, object]:
    # 12. Nghỉ ở dấu câu không sai, nhưng phẩy nghỉ dài hơn chấm là sai nhịp
    periods: List[Tuple[str, float]] = []

    commas: List[Tuple[str, float]] = []

    flat = flat_stt_words(word_spans)

    ends = {round(word_time(w)[1], 2): str(w.get("word", "")) for w in flat}

    for g0, g1, mark in punct_gaps(word_spans, text):
        name = ends.get(round(g0, 2), "")

        if any(c in mark for c in ".!?;"):
            periods.append((name, round(g1 - g0, 2)))
        elif any(c in mark for c in ",:"):
            commas.append((name, round(g1 - g0, 2)))

    if not periods or not commas:
        return {"ok": True, "offenders": []}

    top_period = max(d for _, d in periods)

    bad = [{"word": w, "gap": d, "top_period": top_period} for w, d in commas if d > top_period]

    return {"ok": not bad, "offenders": bad}


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

