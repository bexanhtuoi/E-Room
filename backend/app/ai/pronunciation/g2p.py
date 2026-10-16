from __future__ import annotations

import functools
from typing import Dict, List, Optional, Tuple

IPA_MAP = {
    "TH": "θ", "DH": "ð", "SH": "ʃ", "ZH": "ʒ", "CH": "tʃ", "JH": "dʒ",
    "NG": "ŋ", "HH": "h", "R": "r", "ER": "ɜr", "AH": "ʌ", "IH": "ɪ",
    "IY": "i", "EH": "ɛ", "AE": "æ", "AA": "ɑ", "AO": "ɔ", "OW": "oʊ",
    "UW": "u", "UH": "ʊ", "AY": "aɪ", "EY": "eɪ", "OY": "ɔɪ", "AW": "aʊ",
    "S": "s", "Z": "z", "T": "t", "D": "d", "N": "n", "M": "m",
    "P": "p", "B": "b", "K": "k", "G": "g", "F": "f", "V": "v",
    "W": "w", "L": "l", "Y": "j",
}


def arpa_to_ipa(phone: str) -> str:
    base = phone.rstrip("012")

    return IPA_MAP.get(base, base.lower())


VOWEL_BASE = {
    "AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY",
    "IH", "IY", "OW", "OY", "UH", "UW",
}


def strip_stress(phone: str) -> str:
    return phone.rstrip("012")


def is_vowel(phone: str) -> bool:
    return strip_stress(phone) in VOWEL_BASE


@functools.lru_cache(maxsize=1)
def get_g2p():
    from g2p_en import G2p

    return G2p()


def g2p_to_phones(word_upper: str) -> Tuple[List[str], bool]:
    try:
        raw: List[str] = get_g2p()(word_upper.lower())
    except Exception:
        return ["AH1"], True

    # g2p-en có thể trả từ gốc xen kẽ phoneme khi không biết -> lọc token không phải phone
    phones = [t for t in raw if t.strip() and not any(c.islower() for c in t)]

    # chuẩn hoá: phone phải là chữ in hoa (+ số stress)
    phones = [t.upper() for t in phones if t.strip()]

    if not phones:
        return ["AH1"], True

    # đảm bảo có stress: nếu chưa có số nào, gán 1 cho nguyên âm đầu
    if not any(p[-1] in "012" for p in phones):
        for i, p in enumerate(phones):
            if strip_stress(p) in VOWEL_BASE:
                phones[i] = strip_stress(p) + "1"

                break

    return phones, True


def split_syllables(arpa: List[str]) -> Tuple[List[List[str]], Optional[int]]:
    syllables: List[List[str]] = []

    cur: List[str] = []

    for ph in arpa:
        cur.append(ph)

        if is_vowel(ph):
            syllables.append(cur)

            cur = []

    if cur:
        if syllables:
            syllables[-1].extend(cur)
        else:
            syllables.append(cur)

    for idx, syl in enumerate(syllables):
        if any(p.endswith("1") for p in syl):
            return syllables, idx

    return syllables, None


def apply_gb_non_rhotic(arpa: List[str]) -> List[str]:
    # 1. Bỏ R hậu nguyên âm cho Anh-Anh (non-rhotic)
    out: List[str] = []

    for idx, ph in enumerate(arpa):
        base = strip_stress(ph)

        if base == "ER":
            stress = ph[-1] if ph[-1] in "012" else ""

            out.append("AH" + stress)

            continue

        if base == "R":
            prev_base = strip_stress(out[-1]) if out else ""

            nxt = arpa[idx + 1] if idx + 1 < len(arpa) else ""

            nxt_base = strip_stress(nxt) if nxt else ""

            prev_is_vowel = prev_base in VOWEL_BASE

            nxt_is_end_or_cons = (not nxt_base) or (nxt_base not in VOWEL_BASE and nxt_base != "R")

            if prev_is_vowel and nxt_is_end_or_cons:
                continue

        out.append(ph)

    return out


def get_pronunciation(word: str, accent: str = "en-US") -> Dict:
    from app.ai.pronunciation.helpers import is_gb_accent

    w = (word or "").strip()

    if not w:
        return {"word": word, "arpa": [], "ipa": "", "syllables": [],
                "stress_index": None, "num_syllables": 0, "oov": True, "accent": accent}

    wu = w.upper()

    oov = False

    arpa: Optional[List[str]] = None

    try:
        import pronouncing

        cands = pronouncing.phones_for_word(wu.lower())

        if cands:
            arpa = cands[0].split()
    except Exception:
        arpa = None

    if arpa is None:
        arpa, oov = g2p_to_phones(wu)

    if is_gb_accent(accent):
        arpa = apply_gb_non_rhotic(arpa)

    syllables, stress_index = split_syllables(arpa)

    return {
        "word": wu,
        "arpa": arpa,
        "ipa": "/" + "".join(arpa_to_ipa(p) for p in arpa) + "/",
        "syllables": syllables,
        "stress_index": stress_index,
        "num_syllables": len(syllables),
        "oov": oov,
        "accent": accent,
    }

