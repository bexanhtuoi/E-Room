from __future__ import annotations

from typing import Dict, List, Optional

from app.ai.pronunciation.helpers import is_gb_accent

# Từ chức năng hay rút gọn khi nói liền, đọc nhanh
FUNCTION_WORDS = frozenset({
    "a", "an", "the", "of", "to", "and", "are", "was", "were",
    "have", "has", "had", "will", "would", "can", "could",
    "should", "do", "does", "did", "in", "on", "at", "for",
    "from", "as", "that", "than", "then", "them", "us", "or",
    "but", "so", "if", "it", "its", "is", "am",
})

# Họ nguyên âm yếu qua lại với nhau khi không trọng âm
SCHWA_FAMILY = frozenset({"ʌ", "ə", "ɐ", "ɑ", "ɑː", "ʌ̈"})

# Cặp dài-ngắn cùng chất khi đọc nhanh
LENGTH_PAIRS = frozenset({
    ("i", "iː"), ("u", "uː"), ("o", "oː"), ("ə", "əː"),
    ("ɑ", "ɑː"), ("ɔ", "oː"),
})

# Rhotic chỉ miễn khi Anh-Anh non-rhotic
RHOTIC_SET = frozenset({"ɹ", "ɚ", "ɜ", "r"})

# Đồng hoá voicing khi nói liền
VOICE_PAIRS = frozenset({
    ("s", "z"), ("t", "d"), ("k", "g"), ("f", "v"),
})


def norm_token(token: Optional[str]) -> str:
    return (token or "").strip()


def is_function_word(word: str) -> bool:
    return word.strip().lower() in FUNCTION_WORDS


def next_starts_with_vowel(next_word: str, accent: str = "en-US") -> bool:
    # 2. Âm đầu từ tiếp theo (theo ARPA để đúng cả hour/one/year)
    from app.ai.pronunciation.g2p import get_pronunciation, is_vowel

    arpa = get_pronunciation(next_word, accent).get("arpa", [])

    if not arpa:
        return False

    return is_vowel(arpa[0])


def classify_phone_pair(
    expected: str,
    observed: Optional[str],
    word: str = "",
    accent: str = "en-US",
    next_word: str = "",
) -> Optional[Dict[str, str]]:
    # 1. Miễn trừ rút gọn tự nhiên, trả None khi vẫn tính lỗi thật
    exp = norm_token(expected)

    ob = norm_token(observed or "")

    if not exp or not ob or ob == "-":
        return None

    low_word = word.strip().lower()

    func = is_function_word(low_word)

    gb = is_gb_accent(accent)

    if exp in SCHWA_FAMILY and ob in SCHWA_FAMILY:
        return {"kind": "weak-vowel", "label": "rút gọn tự nhiên"}

    if func and exp in {"u", "uː"} and ob in SCHWA_FAMILY:
        return {"kind": "weak-vowel", "label": "rút gọn tự nhiên"}

    if low_word == "the" and exp in SCHWA_FAMILY and ob in {"i", "iː", "ɪ"}:
        if next_starts_with_vowel(next_word, accent):
            return {"kind": "article", "label": "the trước nguyên âm đọc /ðiː/"}

        return None

    if low_word == "a" and exp in SCHWA_FAMILY and ob in {"eɪ", "æ"}:
        return {"kind": "article", "label": "a nhấn mạnh đọc /eɪ/"}

    if (exp, ob) in LENGTH_PAIRS or (ob, exp) in LENGTH_PAIRS:
        return {"kind": "length", "label": "dài-ngắn tự nhiên"}

    if gb and exp in RHOTIC_SET:
        return {"kind": "non-rhotic", "label": "Anh-Anh bỏ /r/"}

    if exp in RHOTIC_SET and ob in SCHWA_FAMILY:
        if func or gb:
            return {"kind": "rhotic-reduce", "label": "rút gọn /r/"}

    if (exp, ob) in VOICE_PAIRS:
        return {"kind": "voicing", "label": "đồng hoá voicing khi nói liền"}

    if exp == "t" and ob in {"d", "ɾ", "ɾʲ"}:
        return {"kind": "flap", "label": "flap /t/ kiểu Mỹ"}

    if func and exp in {"h", "ð", "θ"} and len(ob) > 0:
        return {"kind": "weak-func", "label": "lướt từ chức năng"}

    return None


def reduction_floor(kind: str) -> float:
    # 2. Sàn điểm cho rút gọn để không kéo từ tốt xuống 0 oan
    if kind in ("weak-vowel", "non-rhotic", "length", "article"):
        return 70.0

    return 65.0


def summarize_reductions(items: List[Dict]) -> List[Dict]:
    # 3. Gom top rút gọn cho UI hiện vàng thay vì đỏ
    counter: Dict[str, Dict] = {}

    for item in items:
        key = str(item.get("pattern", ""))

        if not key:
            continue

        e = counter.setdefault(key, {"pattern": key, "count": 0, "examples": []})

        e["count"] += 1

        for ex in item.get("examples", []):
            if ex not in e["examples"]:
                e["examples"].append(ex)

    out = sorted(counter.values(), key=lambda x: -x["count"])

    return out[:5]
