from __future__ import annotations

import json
import re
import time
from typing import Any, Dict, List

from app.ai.pronunciation.articulation import guide_for_word
from app.ai.pronunciation.g2p import get_pronunciation
from app.ai.pronunciation.metrics import INTON_MED_RANGE
from app.config import settings
from app.log import get_logger

log = get_logger("app.ai.pronunciation.feedback")


def request_pronun_feedback(
    scoring_report: Dict[str, Any],
    model: str = "",
    temperature: float = 0.2,
    max_tokens: int = 2000,
    system_prompt: str = "",
    user_label: str = "scoring_report",
) -> Dict[str, Any]:
    import asyncio

    try:
        out = asyncio.run(generate_feedback(
            scoring_report, model, temperature, max_tokens, system_prompt, user_label,
        ))
    except Exception as error:
        log.warning("feedback LLM lỗi (%s) — dùng gợi ý theo quy tắc", error)

        return build_fallback_feedback(scoring_report, user_label)

    if "error" in out:
        log.warning("feedback LLM lỗi (%s) — dùng gợi ý theo quy tắc", out["error"])

        return build_fallback_feedback(scoring_report, user_label)

    return out


def load_feedback_prompts() -> Dict[str, str]:
    from app.ai.llm.prompt import load_prompt

    out = {"utterance": "", "session": ""}

    utterance = load_prompt("feedback_utterance")

    session = load_prompt("assessment")

    if utterance:
        out["utterance"] = utterance

    if session:
        out["session"] = session

    if out["utterance"] and out["session"]:
        return out

    # Fallback: feedback.md cũ (1 file, 2 mục ## utterance / ## session).
    text = load_prompt("feedback")

    if not text:
        log.warning("prompt feedback thiếu/trống — feedback sẽ chạy prompt rỗng")

        return out

    current = None

    buf: list[str] = []

    for line in text.splitlines():
        head = line.strip().lower()

        if head == "## utterance":
            if current:
                out[current] = "\n".join(buf).strip()

            current, buf = "utterance", []
        elif head == "## session":
            if current:
                out[current] = "\n".join(buf).strip()

            current, buf = "session", []
        elif current:
            buf.append(line)

    if current:
        out[current] = "\n".join(buf).strip()

    if not out["utterance"] or not out["session"]:
        log.warning("thiếu prompt feedback_utterance/assessment")

    return out


_prompts: Dict[str, str] = {}


def prompts() -> Dict[str, str]:
    if not _prompts:
        _prompts.update(load_feedback_prompts())

    return _prompts


def __getattr__(name: str):
    if name == "PROMPTS":
        return prompts()

    if name == "SYSTEM_PROMPT":
        return prompts()["utterance"]

    if name == "SESSION_FEEDBACK_PROMPT":
        return prompts()["session"]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def strip_reasoning(content: str) -> str:
    return THINK_BLOCK_RE.sub("", content or "").strip()


def extract_json(content: str) -> Dict[str, Any] | None:
    text = strip_reasoning(content)

    if not text:
        return None

    try:
        parsed = json.loads(text)

        return parsed if isinstance(parsed, dict) else None
    except (TypeError, ValueError):
        pass

    start = text.find("{")

    end = text.rfind("}")

    if start >= 0 and end > start:
        try:
            parsed = json.loads(text[start : end + 1])

            return parsed if isinstance(parsed, dict) else None
        except (TypeError, ValueError):
            pass

    return _repair_json(text)


# Cứu JSON bị cắt cụt do max_tokens (vd dừng ở `"practice_plan": [`).
# Cắt lùi tới dấu phẩy an toàn gần nhất (ngoài string) rồi đóng ngoặc
# còn dở. Phần mất (thường là practice_plan) sẽ được bù từ fallback ở
# normalize_feedback. Thử tối đa vài lát cắt.
def _repair_json(text: str) -> Dict[str, Any] | None:
    start = text.find("{")

    if start < 0:
        return None

    s = text[start:].strip()

    if s.startswith("```"):
        lines = s.split("\n")

        s = "\n".join(lines[1:])

        if s.rstrip().endswith("```"):
            s = s.rstrip()[:-3].rstrip()

    for _ in range(8):
        depth_curly = depth_sq = 0

        in_str = False

        esc = False

        last_comma = -1

        for i, ch in enumerate(s):
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False

                continue

            if ch == '"':
                in_str = True
            elif ch == "{":
                depth_curly += 1
            elif ch == "}":
                depth_curly -= 1
            elif ch == "[":
                depth_sq += 1
            elif ch == "]":
                depth_sq -= 1
            elif ch == ",":
                last_comma = i

        trial = s + "]" * max(0, depth_sq) + "}" * max(0, depth_curly)

        try:
            parsed = json.loads(trial)

            if isinstance(parsed, dict):
                return parsed
        except (TypeError, ValueError):
            pass

        if last_comma < 0:
            return None

        s = s[:last_comma]

    return None


# Các script ngoài tiếng Việt + IPA Latin: lẫn vào là model lạc ngôn ngữ
# (từng thấy Nga/Trung/Thái/Ý) -> bỏ cả bản, dùng fallback rule-based.
FOREIGN_SCRIPT_RE = re.compile(
    "[\u0400-\u04ff\u4e00-\u9fff\u3040-\u30ff\U00020000-\U0002a6df"
    "\uac00-\ud7af\u0e00-\u0e7f\u0600-\u06ff\u0900-\u097f]"
)


def has_foreign_script(parsed: Dict[str, Any]) -> bool:
    try:
        return bool(FOREIGN_SCRIPT_RE.search(json.dumps(parsed, ensure_ascii=False)))
    except (TypeError, ValueError):
        return False


# Rò rỉ chữ Latin ngoài tiếng Việt/Anh-mục-tiêu (model free hay lẫn
# Tây Ban Nha/Ý/Pháp/Ba Lan: "uno", "evidente", "voix", "doprowad"...).
# FOREIGN_SCRIPT_RE không bắt được vì vẫn là chữ Latin.
LEAK_WORDS = (
    r"uno|una|evidente|evidenti|voix|abbastanza|doprowad|ecco|molto|"
    r"tr[eè]s|schon|sehr|cosa|hola|grazie|merci"
)

LATIN_LEAK_RE = re.compile(r"\b(%s)\b" % LEAK_WORDS, re.IGNORECASE)

# Dính chữ: từ lạ dính liền sau ký tự tiếng Việt ("từuno" thiếu khoảng
# trắng). Chỉ soi đúng các từ lạ đã biết để không chạm từ Việt
# bình thường ("quãng", "những" cũng có dạng dấu+phụ âm).
VI_CHAR = (
    "àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡ"
    "ùúụủũưừứựửữỳýỵỷỹđ"
)

GLUED_LEAK_RE = re.compile("[%s](%s)\\b" % (VI_CHAR, LEAK_WORDS), re.IGNORECASE)

NULL_PAREN_RE = re.compile(r"\s*\([^()]*\bnull\b[^()]*\)", re.IGNORECASE)

NULL_WORD_RE = re.compile(r"\bnull\b", re.IGNORECASE)

SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([,.;:!?])")

MULTI_SPACE_RE = re.compile(r"\s{2,}")

NUMBERED_STEP_RE = re.compile(r"\(?\b[123][).]\s*")

SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

# Thuật ngữ Anh hay lọt vào câu tiếng Việt -> dịch cố định.
VI_TERM_FIXES = (
    (re.compile(r"\bpauses\b", re.IGNORECASE), "quãng nghỉ"),
    (re.compile(r"\bpause\b", re.IGNORECASE), "quãng nghỉ"),
    (re.compile(r"\bintonation\b", re.IGNORECASE), "ngữ điệu"),
)


# Chuẩn hóa câu chữ LLM: dịch thuật ngữ Anh, xóa "(null)".
# Giữ nguyên ký hiệu IPA trong /.../ và từ ví dụ tiếng Anh
# (chúng không khớp whole-word với thuật ngữ cần dịch).
def sanitize_feedback_text(text: str) -> str:
    if not isinstance(text, str) or not text:
        return text

    # Chuẩn hóa gạch nối/khoảng trắng lạ mà model hay nhả ra.
    out = text.replace("\u2011", "-").replace("\u202f", " ")

    for pattern, replacement in VI_TERM_FIXES:
        out = pattern.sub(replacement, out)

    out = NULL_PAREN_RE.sub("", out)

    out = NULL_WORD_RE.sub("", out)

    out = SPACE_BEFORE_PUNCT_RE.sub(r"\1", out)

    out = MULTI_SPACE_RE.sub(" ", out)

    return out.strip()


# Gom các trường câu chữ (bỏ word/vi/model) để soi rò rỉ ngôn ngữ.
def feedback_prose_text(parsed: Dict[str, Any]) -> str:
    if not isinstance(parsed, dict):
        return ""

    parts: List[str] = []

    for key in ("summary", "pronunciation_feedback", "stress_feedback",
                "intonation_feedback", "fluency_feedback", "feedback_raw"):
        value = parsed.get(key)

        if isinstance(value, str) and value:
            parts.append(value)

    for key in ("priority_errors", "error_words"):
        entries = parsed.get(key)

        if not isinstance(entries, list):
            continue

        for entry in entries:
            if not isinstance(entry, dict):
                continue

            for field in ("issue", "advice", "tip", "how_to"):
                value = entry.get(field)

                if isinstance(value, str) and value:
                    parts.append(value)

    plans = parsed.get("practice_plan")

    if isinstance(plans, list):
        parts.extend([p for p in plans if isinstance(p, str)])

    return "\n".join(parts)


def has_latin_leak(parsed: Dict[str, Any]) -> bool:
    try:
        prose = feedback_prose_text(parsed)
    except (TypeError, ValueError):
        return False

    return bool(LATIN_LEAK_RE.search(prose) or GLUED_LEAK_RE.search(prose))


# Dịch thuật ngữ + xóa null trên mọi trường chữ (trừ word/model/usage).
def sanitize_feedback_json(parsed: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(parsed, dict):
        return parsed

    for key in ("summary", "pronunciation_feedback", "stress_feedback",
                "intonation_feedback", "fluency_feedback", "feedback_raw"):
        if isinstance(parsed.get(key), str):
            parsed[key] = sanitize_feedback_text(parsed[key])

    for key in ("priority_errors", "error_words"):
        entries = parsed.get(key)

        if not isinstance(entries, list):
            continue

        for entry in entries:
            if not isinstance(entry, dict):
                continue

            for field in ("issue", "advice", "tip", "how_to", "vi"):
                if isinstance(entry.get(field), str):
                    entry[field] = sanitize_feedback_text(entry[field])

    plans = parsed.get("practice_plan")

    if isinstance(plans, list):
        parsed["practice_plan"] = [
            sanitize_feedback_text(p) if isinstance(p, str) else p for p in plans
        ]

    return parsed


LLM_MAX_ATTEMPTS = 3

LLM_FAST_FAIL_SECONDS = 20.0

LLM_RETRY_PAUSE_SECONDS = 3.0


async def generate_feedback(scoring_report: dict, model: str = "",
                            temperature: float = 0.2, max_tokens: int = 2000,
                            system_prompt: str = "", user_label: str = "scoring_report") -> dict:
    import asyncio

    from app.ai.llm.client import get_llm

    user_msg = f"{user_label}:\n" + json.dumps(scoring_report, ensure_ascii=False)[:12000]

    for attempt in range(1, LLM_MAX_ATTEMPTS + 1):
        started = time.monotonic()

        try:
            llm = get_llm(model=model, temperature=temperature, max_tokens=max_tokens,
                            reasoning="exclude")

            msg = await llm.ainvoke([
                {"role": "system", "content": system_prompt or prompts()["utterance"]},
                {"role": "user", "content": user_msg},
            ])
        except Exception as error:
            elapsed = time.monotonic() - started

            if attempt < LLM_MAX_ATTEMPTS and elapsed < LLM_FAST_FAIL_SECONDS:
                log.warning("LLM feedback lần %s lỗi sau %.1fs (%s) — thử lại", attempt, elapsed, error)

                await asyncio.sleep(LLM_RETRY_PAUSE_SECONDS)

                continue

            log.warning("LLM feedback không reachable (%s) — dùng gợi ý theo quy tắc", error)

            return build_fallback_feedback(scoring_report, user_label)

    content = getattr(msg, "content", "") or ""

    text = content if isinstance(content, str) else str(content)

    if not text.strip():
        log.warning("feedback LLM trả về rỗng — dùng gợi ý theo quy tắc")

        return build_fallback_feedback(scoring_report, user_label)

    parsed = extract_json(text)

    if parsed:
        parsed = sanitize_feedback_json(parsed)

        if has_foreign_script(parsed) or has_latin_leak(parsed):
            log.warning("feedback LLM lẫn ngoại ngữ — dùng gợi ý theo quy tắc")

            return build_fallback_feedback(scoring_report, user_label)

        parsed.setdefault("model", (model or "").strip() or settings.llm_model)

        return normalize_feedback(parsed, scoring_report)

    return {"feedback_raw": sanitize_feedback_text(text),
            "model": (model or "").strip() or settings.llm_model, "usage": {}}


# Tách 1 bước gộp thành nhiều bước theo đánh số hoặc theo câu.
# Model hay dồn cả kế hoạch vào 1 chuỗi ("(1) ... (2) ... (3) ..." hoặc 1 đoạn văn).
# UI và quy ước cần mảng bước tách rời nên thử tách: ưu tiên mốc đánh số, rồi đến
# ranh giới câu. Chỉ nhận khi được 2-4 bước đủ dài, còn không giữ nguyên.
def split_plan_steps(plans: Any) -> Any:
    if not isinstance(plans, list) or len(plans) != 1:
        return plans

    sole = plans[0]

    if not isinstance(sole, str) or not sole.strip():
        return plans

    numbered = [p.strip(" .;") for p in NUMBERED_STEP_RE.split(sole)]

    numbered = [p for p in numbered if len(p) >= 10]

    if 2 <= len(numbered) <= 4:
        return numbered

    sents = [p.strip() for p in SENTENCE_SPLIT_RE.split(sole.strip())]

    sents = [p for p in sents if len(p) >= 10]

    if 2 <= len(sents) <= 4:
        return sents

    return plans


# Chuẩn hóa JSON LLM về schema UI mới: prompt cũ bắt `how_to` nhưng schema
# `PriorityError`/UI đọc `advice` nên bản LLM cũ làm mất dòng Cách sửa.
# Hàm này map `how_to`/`tip` về `advice` (và ngược lại cho `error_words`
# của session), bù `vi` từ `guide_for_word` khi thiếu, và bù mục chữ +
# `practice_plan` còn trống (kể cả sau khi _repair_json cứu JSON cụt) từ
# fallback rule-based để UI không mất section.
def normalize_feedback(parsed: Dict[str, Any], scoring_report: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(parsed, dict):
        return parsed

    # Model đôi khi trả practice_plan là chuỗi thay vì mảng (UI đọc .map)
    # -> bọc lại để không vỡ render.
    if isinstance(parsed.get("practice_plan"), str):
        text = parsed["practice_plan"].strip()

        parsed["practice_plan"] = [text] if text else []

    parsed["practice_plan"] = split_plan_steps(parsed.get("practice_plan"))

    errs = parsed.get("priority_errors")

    if isinstance(errs, list):
        norm = []

        for entry in errs:
            if not isinstance(entry, dict):
                continue

            word = str(entry.get("word") or "?")

            advice = entry.get("advice") or entry.get("how_to") or entry.get("tip") or ""

            vi = entry.get("vi") or ""

            if (not advice or not vi) and word != "?":
                try:
                    guide = word_guide(word, str(entry.get("issue") or ""))

                    advice = advice or guide.get("how_to", "")

                    vi = vi or guide.get("vi", "")
                except Exception:
                    pass

            norm.append({
                "word": word,
                "issue": entry.get("issue") or "cần luyện thêm",
                "advice": advice,
                "vi": vi,
            })

        parsed["priority_errors"] = norm

    session_errs = parsed.get("error_words")

    if isinstance(session_errs, list):
        for entry in session_errs:
            if not isinstance(entry, dict):
                continue

            if not entry.get("how_to") and entry.get("advice"):
                entry["how_to"] = entry["advice"]

            if not entry.get("tip") and (entry.get("how_to") or entry.get("advice")):
                entry["tip"] = entry.get("how_to") or entry.get("advice")

    needs_fill = (
        not parsed.get("practice_plan")
        or not parsed.get("summary")
        or not parsed.get("pronunciation_feedback")
        or not parsed.get("priority_errors")
        or not parsed.get("stress_feedback")
        or not parsed.get("intonation_feedback")
        or not parsed.get("fluency_feedback")
    )

    if needs_fill:
        try:
            fallback = build_fallback_feedback(scoring_report or {}, "scoring_report")
        except Exception:
            fallback = {}

        for key in ("summary", "pronunciation_feedback", "stress_feedback",
                    "intonation_feedback", "fluency_feedback"):
            if not parsed.get(key) and fallback.get(key):
                parsed[key] = fallback[key]

        if not parsed.get("priority_errors") and fallback.get("priority_errors"):
            parsed["priority_errors"] = fallback["priority_errors"]

        if not parsed.get("practice_plan") and fallback.get("practice_plan"):
            parsed["practice_plan"] = fallback["practice_plan"]

    return parsed


def word_guide(word: str, issue: str) -> Dict[str, str]:
    try:
        arpa = get_pronunciation(word.split(",")[0].strip(), "en-US").get("arpa", [])
    except Exception:
        arpa = []

    return guide_for_word(word, arpa, issue)


def bad_word_entry(word: str, issue: str, score) -> dict:
    return {"word": word, "issue": issue, "score": score, **word_guide(word, issue)}


def top_error_entry(examples, pattern: str) -> dict:
    word = ", ".join((examples or [])[:2]) or "?"

    issue = str(pattern)

    return {"word": word, "issue": issue, "score": None, **word_guide(word, issue)}


def build_fallback_feedback(scoring_report: dict, user_label: str = "scoring_report") -> dict:
    report = scoring_report or {}

    utts = report.get("utterances")

    if isinstance(utts, list):
        # Dạng session_scores: [{text, overall, bad_words, top_errors}]
        entries = []

        for u in utts:
            for b in (u.get("bad_words") or [])[:5]:
                issue = f"{b.get('status', '')} {b.get('expected_ipa', '')}".strip()

                entries.append(bad_word_entry(b.get("word") or "?", issue, b.get("score")))

            for t in (u.get("top_errors") or [])[:3]:
                entries.append(top_error_entry(t.get("examples"), t.get("pattern", "")))

        scored = [u for u in utts if isinstance(u.get("overall"), (int, float))]

        avg = round(sum(u["overall"] for u in scored) / len(scored), 1) if scored else 0.0

        n = len(utts)
    else:
        # Dạng scoring_report 1 câu: {scores, word_details, top_errors}
        entries = []

        for w in report.get("word_details") or []:
            if (w.get("status") or "ok") != "ok":
                issue = f"{w.get('status', '')} {w.get('expected_ipa', '')}".strip()

                entries.append(bad_word_entry(w.get("word") or "?", issue, w.get("score")))

        for t in (report.get("top_errors") or [])[:3]:
            entries.append(top_error_entry(t.get("examples"), t.get("pattern", "")))

        overall = ((report.get("scores") or {}).get("overall"))

        avg = round(float(overall), 1) if isinstance(overall, (int, float)) else 0.0

        n = 1

    stress_details = report.get("stress_detail") or []
    stress_wrong = [
        str(d.get("word") or "").strip() for d in stress_details
        if d.get("correct") is False and str(d.get("word") or "").strip()
    ]
    if stress_wrong:
        stress_names = ", ".join(f"'{w}'" for w in stress_wrong[:3])
        stress_feedback = (
            f"Trọng âm sai: {stress_names}. "
            f"Nghe kỹ âm tiết nhấn của từ đa âm tiết, đọc mạnh-nhẹ rõ ràng."
        )
    elif stress_details:
        stress_feedback = "Trọng âm ổn — các từ đa âm tiết đều nhấn đúng."
    else:
        stress_feedback = ""

    into = report.get("intonation") or {}
    if into.get("score") is None:
        intonation_feedback = ""
    else:
        into_parts = []
        if into.get("monotone"):
            into_parts.append("giọng ngang, đều từ đầu đến cuối")
        elif float(into.get("pitch_range") or 0.0) < INTON_MED_RANGE:
            into_parts.append("dải cao độ hẹp, ít nhấn nhá")
        else:
            into_parts.append("giọng có lên xuống tự nhiên")
        stype = {"question": "câu hỏi", "statement": "câu kể", "exclaim": "câu cảm thán"}.get(str(into.get("sentence_type") or ""))
        if stype and into.get("slope_ok") is False:
            if str(into.get("sentence_type")) == "question":
                into_parts.append("nhưng cuối câu hỏi chưa lên giọng")
            else:
                into_parts.append(f"nhưng cuối {stype} chưa xuống giọng tự nhiên")
        elif stype:
            into_parts.append(f"cuối {stype} hợp ngữ điệu")
        intonation_feedback = "Ngữ điệu: " + ", ".join(into_parts) + "."

    flu = report.get("fluency") or {}
    wpm = float(flu.get("wpm") or 0.0)
    if not flu or wpm <= 0:
        fluency_feedback = ""
    else:
        flu_bits = []
        if 90 <= wpm <= 200:
            flu_bits.append(f"nhịp vừa phải ({round(wpm)} từ/phút)")
        elif wpm < 90:
            flu_bits.append(f"nói chậm ({round(wpm)} từ/phút)")
        else:
            flu_bits.append(f"nói nhanh ({round(wpm)} từ/phút)")
        longs = int(flu.get("long_pause_count") or 0)
        if longs > 0:
            flu_bits.append(f"nghỉ dài {longs} lần")
        elif float(flu.get("pause_ratio") or 0.0) > 0.25:
            flu_bits.append("nhiều quãng nghỉ")
        stumbles = int(flu.get("hesitation_count") or 0) + int(flu.get("repetition_count") or 0)
        if stumbles > 0:
            flu_bits.append("có vấp/lặp từ")
        fluency_feedback = "Trôi chảy: " + ", ".join(flu_bits) + "."

    # Gom trùng từ, giữ tối đa 3 lỗi chính.
    seen, top = set(), []

    for e in entries:
        if e["word"] not in seen:
            seen.add(e["word"])

            top.append(e)

        if len(top) >= 3:
            break

    dimension_labels = (
        ("sounds", "Phát âm"),
        ("stress", "Trọng âm"),
        ("fluency", "Lưu loát"),
        ("completeness", "Hoàn thiện"),
    )

    dim_scores = report.get("scores") or {}

    dim_values = []

    for key, label in dimension_labels:
        value = dim_scores.get(key)

        if isinstance(value, (int, float)):
            dim_values.append((label, round(float(value), 1)))

    if avg >= 85:
        verdict = "Tốt — giữ phong độ"
    elif avg >= 70:
        verdict = "Khá — sửa vài âm là lên điểm"
    elif avg >= 50:
        verdict = "Trung bình — cần luyện trọng tâm"
    else:
        verdict = "Còn yếu — quay lại luyện từng âm cơ bản"

    if dim_values:
        best = max(dim_values, key=lambda item: item[1])

        worst = min(dim_values, key=lambda item: item[1])

        dimension_part = f" Mạnh nhất: {best[0]} ({best[1]}). Yếu nhất: {worst[0]} ({worst[1]})."
    else:
        dimension_part = ""

    if top:
        listed = "; ".join(f"'{e['word']}' ({e['issue']})" for e in top)

        error_part = f" Cần sửa: {listed}."

        if n == 1:
            next_action = f" Luyện '{top[0]['word']}' trước rồi chấm lại."
        else:
            next_action = f" Luyện {len(top)} từ trên trước rồi chấm lại."
    else:
        error_part = " Không phát hiện lỗi âm rõ rệt."

        next_action = " Giữ nhịp nói đều và chấm câu mới."

    summary = f"Tổng quan ({n} câu, trung bình {avg}): {verdict}.{dimension_part}{error_part}{next_action}"

    if top:
        sound_part = "; ".join(f"'{e['word']}' ({e['issue']})" for e in top)

        pronunciation_feedback = (
            f"Âm cần sửa: {sound_part}. "
            f"Đọc chậm từng từ theo phiên âm IPA, ghi âm rồi so với mẫu 3 lần."
        )
    else:
        pronunciation_feedback = "Không phát hiện lỗi âm rõ rệt — giữ nguyên cách phát âm hiện tại."

    error_words = [{"word": e["word"], "issue": e["issue"] or "cần luyện thêm",
                    "tip": e["how_to"], "how_to": e["how_to"], "vi": e["vi"]} for e in top]

    if top:
        first = top[0]

        practice_plan = [
            f"Luyện từ khó nhất '{first['word']}' (đọc là “{first['vi']}”): {first['how_to']}",
            "Đọc chậm từng từ sai, ghi âm và so với mẫu 3 lần.",
            "Nói lại cả đoạn ở tốc độ tự nhiên rồi chấm lại để kiểm tra.",
        ]
    else:
        practice_plan = [
            "Đọc chậm từng từ sai, ghi âm và so với mẫu 3 lần.",
            "Luyện câu đầy đủ với nhịp đều, không nuốt âm cuối.",
            "Nói lại cả đoạn ở tốc độ tự nhiên rồi chấm lại để kiểm tra.",
        ]

    return {
        "summary": summary,
        "pronunciation_feedback": pronunciation_feedback,
        "stress_feedback": stress_feedback,
        "intonation_feedback": intonation_feedback,
        "fluency_feedback": fluency_feedback,
        "priority_errors": [{"word": e["word"], "issue": e["issue"],
                             "advice": e["how_to"], "vi": e["vi"]} for e in top],
        "error_words": error_words,
        "practice_plan": practice_plan,
        "model": "rule-based-fallback",
        "fallback": True,
        "usage": {},
    }

