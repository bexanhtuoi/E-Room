from __future__ import annotations

import functools

from app.log import get_logger

log = get_logger("app.ai.pronunciation.g2p")


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
    """ARPAbet -> IPA (subset MVP, đủ cho test think/sink/rice/lice/very)."""
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


def g2p_to_phones(word_upper: str) -> tuple[list[str], bool]:
    """Trả (arpa_phones, oov=True). g2p-en sinh cả stress số."""
    try:
        raw: list[str] = get_g2p()(word_upper.lower())
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


def get_pronunciation(word: str, accent: str = "en-US") -> dict:
    """Full CMUdict (qua package `pronouncing`, ~130k từ) + fallback `g2p-en`
    neural cho từ OOV. Theo tư vấn chuyên gia: không dùng mini-dict,
    không đoán stress thủ công."""
    w = (word or "").strip()
    if not w:
        return {"word": word, "arpa": [], "ipa": "", "syllables": [],
                "stress_index": None, "num_syllables": 0, "oov": True, "accent": accent}
    wu = w.upper()
    oov = False
    arpa: list[str] | None = None
    try:
        import pronouncing
        cands = pronouncing.phones_for_word(wu.lower())
        if cands:
            arpa = cands[0].split()
    except Exception:
        arpa = None
    if arpa is None:
        arpa, oov = g2p_to_phones(wu)
    syllables: list[list[str]] = []
    cur: list[str] = []
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
    stress_index = None
    for idx, syl in enumerate(syllables):
        if any(p.endswith("1") for p in syl):
            stress_index = idx
            break
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

