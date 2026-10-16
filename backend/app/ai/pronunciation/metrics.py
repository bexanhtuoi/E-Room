import difflib
from typing import Dict, List, Optional, Tuple

from app.ai.pronunciation.helpers import tok_words


def score_fluency(
    duration_s: float,
    words_count: int,
    pauses: List[Tuple[float, float]],
    whisper_text: str = "",
    long_pause_s: float = 0.4,
) -> Dict:
    wpm = (words_count / max(0.1, duration_s)) * 60.0 if duration_s > 0 else 0.0

    pause_dur = sum(e - s for s, e in pauses)

    pause_ratio = pause_dur / max(0.1, duration_s)

    long_pauses = sum(1 for s, e in pauses if e - s >= long_pause_s)

    low = (whisper_text or "").lower()

    hes = sum(low.count(x) for x in [" uh ", " um ", " er ", " ah "])

    # repetition: từ lặp liền nhau
    toks = tok_words(whisper_text)

    rep = sum(1 for i in range(1, len(toks)) if toks[i] == toks[i-1])

    phones = sum(len(w) for w in toks)

    art = phones / max(0.1, duration_s - pause_dur)

    # rubric 0-100, band rộng: chấm thật (<50) hoặc bản quá nhanh mới trừ nặng
    s = 100.0

    if 90 <= wpm <= 200:
        s -= 0
    elif 50 <= wpm < 90 or 200 < wpm <= 250:
        s -= 10
    else:
        s -= 25

    if pause_ratio > 0.35:
        s -= 20
    elif pause_ratio > 0.25:
        s -= 10

    s -= min(20, long_pauses * 5 + hes * 4 + rep * 5)

    return {"wpm": round(wpm,1), "articulation_rate": round(art,2), "pause_ratio": round(pause_ratio,3),
            "long_pause_count": long_pauses, "hesitation_count": hes, "repetition_count": rep,
            "score": round(max(0.0, min(100.0, s)),1)}


def score_completeness(
    original: Optional[str],
    corrected: str,
    mode: str,
    word_details: Optional[List[Dict]] = None,
) -> Dict:
    if mode == "read_aloud" and original:
        return score_completeness_read_aloud(original, corrected, mode)

    details = word_details or []

    total = len(details)

    if not total:
        return {"mode": mode, "missing_words": [], "extra_words": [], "wer_vs_original": None, "score": 0.0}

    missing = [
        str(d.get("word", ""))
        for d in details
        if d.get("status") == "no_evidence" or float(d.get("score") or 0.0) <= 0.0
    ]

    score = round(100.0 * (total - len(missing)) / total, 1)

    return {"mode": mode, "missing_words": missing[:20], "extra_words": [], "wer_vs_original": None, "score": score}


def score_completeness_read_aloud(original: Optional[str], corrected: str, mode: str) -> Dict:
    if not original:
        return {"mode": mode, "missing_words": [], "extra_words": [], "wer_vs_original": None, "score": 100.0}

    a, b = tok_words(original), tok_words(corrected)

    sa, sb = set(a), set(b)

    missing = [w for w in a if w not in sb]

    extra = [w for w in b if w not in sa]

    # WER đơn giản
    sm = difflib.SequenceMatcher(None, a, b)

    wer = round(1.0 - sm.ratio(), 3)

    score = round(max(0.0, 100.0 * (1.0 - (len(missing) + len(extra)) / max(1, len(a)))), 1)

    return {"mode": mode, "missing_words": missing[:20], "extra_words": extra[:20],
            "wer_vs_original": wer, "score": score}


def calculate_overall(sounds: float, stress: float, fluency: float, completeness: float) -> float:
    return round(0.5*sounds + 0.25*stress + 0.15*fluency + 0.10*completeness, 1)


# Ngưỡng chấm ngữ điệu rule-based (đơn vị Hz, trừ điểm theo thang 0-100).
INTON_MIN_VOICED = 0.1

INTON_MONOTONE_STD = 15.0

INTON_FLAT_STD = 25.0

INTON_NARROW_RANGE = 20.0

INTON_MED_RANGE = 40.0

INTON_RISE_SLOPE = 5.0

INTON_STMT_MAX_SLOPE = 15.0

INTON_PEN_MONOTONE = 30.0

INTON_PEN_NARROW = 20.0

INTON_PEN_MED = 10.0

INTON_PEN_SLOPE = 15.0


# Chấm ngữ điệu rule-based, KHÔNG so giọng mẫu (giọng AI không chuẩn
# bằng giọng thật) nên chỉ dùng số liệu F0 có sẵn + dấu câu.
# Rubric 0-100: trừ khi đều-đều (monotone), dải cao độ hẹp, hoặc
# hướng cuối câu sai loại câu (hỏi phải lên, kể không vọt).
# Điểm này chỉ đưa vào report cho LLM đọc, KHÔNG hiện UI,
# KHÔNG cộng vào overall (giữ nguyên trọng số cũ).
def score_intonation(f0: Dict, text: str = "") -> Dict:
    voiced = float(f0.get("voiced_ratio") or 0.0)

    median = float(f0.get("median_f0") or 0.0)

    if voiced < INTON_MIN_VOICED or median <= 0.0:
        return {"score": None, "monotone": False, "pitch_range": 0.0,
                "final_slope": 0.0, "sentence_type": "unknown",
                "slope_ok": None,
                "note": "không đủ tín hiệu giọng để chấm ngữ điệu"}

    std = float(f0.get("std_f0") or 0.0)

    prange = float(f0.get("range_f0") or 0.0)

    slope = float(f0.get("final_slope") or 0.0)

    monotone = std < INTON_MONOTONE_STD and voiced > INTON_MIN_VOICED

    tail = (text or "").strip()

    if tail.endswith("?"):
        sentence_type = "question"

        slope_ok = slope > INTON_RISE_SLOPE
    elif tail.endswith("!"):
        sentence_type = "exclaim"

        slope_ok = abs(slope) > INTON_RISE_SLOPE
    else:
        sentence_type = "statement"

        slope_ok = slope < INTON_STMT_MAX_SLOPE

    s = 100.0

    if monotone:
        s -= INTON_PEN_MONOTONE
    elif std < INTON_FLAT_STD:
        s -= INTON_PEN_MED

    if prange < INTON_NARROW_RANGE:
        s -= INTON_PEN_NARROW
    elif prange < INTON_MED_RANGE:
        s -= INTON_PEN_MED

    if not slope_ok:
        s -= INTON_PEN_SLOPE

    return {"score": round(max(0.0, min(100.0, s)), 1),
            "monotone": monotone,
            "pitch_range": round(prange, 1),
            "final_slope": round(slope, 1),
            "sentence_type": sentence_type,
            "slope_ok": bool(slope_ok),
            "note": "rule-based-v1: dải cao độ + hướng cuối câu theo loại câu"}


def needleman(a: List[str], b: List[str]) -> List[Tuple[str, str, str]]:
    n, m = len(a), len(b)

    dp = [[0] * (m + 1) for _ in range(n + 1)]

    for i in range(n + 1):
        dp[i][0] = i

    for j in range(m + 1):
        dp[0][j] = j

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1

            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)

    i, j, out = n, m, []

    while i > 0 or j > 0:
        if i > 0 and j > 0 and a[i - 1] == b[j - 1]:
            out.append((a[i - 1], b[j - 1], "match"))

            i -= 1

            j -= 1
        elif i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + 1:
            out.append((a[i - 1], b[j - 1], "substitution"))

            i -= 1

            j -= 1
        elif j > 0 and dp[i][j] == dp[i][j - 1] + 1:
            out.append(("-", b[j - 1], "insertion"))

            j -= 1
        else:
            out.append((a[i - 1], "-", "deletion"))

            i -= 1

    return out[::-1]

