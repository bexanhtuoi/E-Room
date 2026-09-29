"""Hướng dẫn khẩu hình + phiên âm tiếng Việt cho lỗi phát âm.

Thuần dữ liệu, không phụ thuộc model/DB — dùng chung cho fallback
rule-based và gợi ý trong prompt LLM.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

MOUTH: Dict[str, str] = {
    "TH": "đặt đầu lưỡi thò ra giữa hai hàm răng rồi thổi hơi nhẹ, không rung dây thanh",
    "DH": "đặt đầu lưỡi giữa hai hàm răng như /θ/ nhưng rung dây thanh (sờ cổ thấy rung)",
    "S": "đầu lưỡi gần lợi răng trên, xì hơi mạnh qua khe hẹp, không rung",
    "Z": "khẩu hình như /s/ nhưng rung dây thanh",
    "SH": "tròn môi chúm về trước, cong lưỡi lên, xì hơi dài",
    "ZH": "khẩu hình như /ʃ/ nhưng rung dây thanh",
    "CH": "bật /t/ rồi nối ngay hơi xì /ʃ/, môi tròn",
    "JH": "bật /d/ rồi nối ngay /ʒ/, rung dây thanh",
    "T": "đầu lưỡi chạm lợi răng trên rồi bật hơi dứt khoát",
    "D": "khẩu hình như /t/ nhưng rung dây thanh, bật nhẹ hơn",
    "N": "đầu lưỡi chạm lợi, hơi đi qua mũi, rung dây thanh",
    "L": "đầu lưỡi chạm lợi răng trên, hơi thoát ra hai bên lưỡi",
    "R": "cong đầu lưỡi lên nhưng không chạm đâu, môi hơi tròn",
    "P": "mím chặt môi rồi bật hơi mạnh",
    "B": "khẩu hình như /p/ nhưng rung dây thanh, bật nhẹ hơn",
    "M": "mím môi, hơi đi qua mũi, rung dây thanh",
    "K": "nâng gốc lưỡi chạm vòm mềm rồi bật hơi (âm cổ họng)",
    "G": "khẩu hình như /k/ nhưng rung dây thanh",
    "NG": "giữ gốc lưỡi chạm vòm mềm, hơi đi qua mũi, không bật (như cuối chữ 'đang')",
    "F": "răng trên chạm môi dưới rồi thổi hơi ra, không rung",
    "V": "khẩu hình như /f/ nhưng rung dây thanh",
    "H": "thở hắt ra như tiếng thở dài, không cản hơi",
    "W": "tròn môi chúm như thổi sáo rồi mở ra ngay",
    "Y": "nâng lưỡi cao sát vòm cứng, hơi thoát qua khe hẹp",
    "IY": "cười banh miệng theo chiều ngang, lưỡi nâng cao, âm kéo dài",
    "IH": "miệng hơi mở, âm ngắn dứt khoát, đừng kéo dài thành /i:/",
    "EY": "đọc /e/ rồi trượt lên /ɪ/, miệng khép dần",
    "EH": "mở miệng vừa như 'e' tiếng Việt, lưỡi thấp",
    "AE": "há miệng rộng, hàm hạ thấp — âm nằm giữa 'a' và 'e'",
    "AA": "há to như lúc khám họng, lưỡi thấp",
    "AO": "tròn môi vừa, lưỡi lùi vào trong",
    "OW": "đọc /o/ tròn môi rồi trượt sang /ʊ/, môi khép lại",
    "UH": "môi hơi tròn, thả lỏng, âm ngắn",
    "UW": "tròn môi chặt chúm về trước, âm kéo dài",
    "AH": "miệng mở tự nhiên, thả lỏng, âm ngắn",
    "AY": "há rộng đọc /a/ rồi trượt lên /ɪ/",
    "OY": "tròn môi đọc /ɔ/ rồi trượt lên /ɪ/",
    "AW": "há rộng đọc /a/ rồi trượt sang /ʊ/, môi khép lại",
    "ER": "cong lưỡi lên, thả lỏng môi, âm kéo dài",
    "AX": "âm ơ lười — thả lỏng hoàn toàn, đọc lướt nhẹ",
}

VI_SOUND: Dict[str, str] = {
    "TH": "th", "DH": "đ", "S": "x", "Z": "gi", "SH": "s", "ZH": "gi",
    "CH": "ch", "JH": "gi", "T": "t", "D": "d", "N": "n", "L": "l",
    "R": "r", "P": "p", "B": "b", "M": "m", "K": "k", "G": "g",
    "NG": "ng", "F": "ph", "V": "v", "H": "h", "W": "u", "Y": "d",
    "IY": "ii", "IH": "i", "EY": "ây", "EH": "e", "AE": "ae", "AA": "a",
    "AO": "o", "OW": "âu", "UH": "u", "UW": "uu", "AH": "ơ", "AY": "ai",
    "OY": "oi", "AW": "ao", "ER": "ơ", "AX": "ơ",
}

PATTERN_TIPS: Dict[str, str] = {
    "θ→s": "Đừng xì thành /s/. Đặt đầu lưỡi THÒ RA GIỮA hai hàm răng rồi thổi hơi — lưỡi phải chạm răng.",
    "ð→z": "Đừng đọc thành /z/. Đặt đầu lưỡi giữa hai hàm răng và RUNG dây thanh (sờ cổ thấy rung).",
    "ð→d": "Đừng bật thành /d/. Đặt đầu lưỡi giữa hai hàm răng, rung nhẹ, hơi thoát liên tục.",
    "ɪ→i": "Âm ngắn dứt khoát, miệng hơi mở — đừng kéo dài thành /i:/.",
    "æ→a": "Đừng đọc tròn thành 'a'. Há rộng, hàm hạ thấp — âm nằm giữa 'a' và 'e'.",
    "ʃ→s": "Đừng xì dẹt như /s/. Tròn môi chúm về trước, cong lưỡi lên rồi xì dài.",
    "tʃ→t": "Đừng đọc cụt thành /t/. Bật /t/ rồi nối ngay hơi xì /ʃ/ trong một hơi.",
    "ŋ→n": "Đừng đọc thành /n/ đầu lưỡi. Nâng GỐC lưỡi chạm vòm mềm, hơi đi qua mũi, không bật.",
    "ʌ→a": "Thả lỏng, miệng mở tự nhiên — ngắn và nhẹ hơn 'a' tiếng Việt.",
    "ɒ→o": "Tròn môi vừa, lưỡi lùi sâu — trầm và ngắn hơn 'o' tiếng Việt.",
    "w→u": "Tròn môi chúm như thổi sáo rồi mở bung ra ngay, đừng đọc rời thành 2 âm.",
    "θ→t": "Đừng bật thành /t/. Thò lưỡi giữa răng, thổi hơi liên tục thay vì bật.",
}

_CONFUSION_RE = re.compile(r"/([^/]+)/\s*→\s*/([^/]+)/")


def normalize_base(phone: str) -> str:
    base = (phone or "").rstrip("012")
    return "H" if base == "HH" else base


def parse_confusion(issue: str) -> Optional[tuple[str, str]]:
    found = _CONFUSION_RE.findall(issue or "")
    if not found:
        return None
    exp, obs = found[0][0].strip().lower(), found[0][1].strip().lower()
    if not exp or not obs:
        return None
    return exp, obs


def phone_bases(arpa: List[str]) -> List[str]:
    return [base for p in (arpa or []) if p for base in [normalize_base(p)] if base in MOUTH]


def vi_reading(arpa: List[str]) -> str:
    parts = [VI_SOUND.get(normalize_base(p), normalize_base(p).lower()) for p in (arpa or [])]
    return " ".join(part for part in parts if part)


def mouth_guide(arpa: List[str], limit: int = 3) -> str:
    seen: List[str] = []
    for base in phone_bases(arpa):
        tip = MOUTH[base]
        if tip not in seen:
            seen.append(tip)
        if len(seen) >= limit:
            break
    return "; ".join(seen)


def guide_for_word(word: str, arpa: List[str], issue: str = "") -> Dict[str, str]:
    pair = parse_confusion(issue or "")
    how_to = ""
    if pair is not None:
        how_to = PATTERN_TIPS.get(f"{pair[0]}→{pair[1]}", "")
    if not how_to:
        how_to = mouth_guide(arpa)
    if not how_to:
        how_to = f"Đọc chậm '{word}' từng âm, ghi âm lại rồi so với mẫu."
    return {"how_to": how_to, "vi": vi_reading(arpa)}
