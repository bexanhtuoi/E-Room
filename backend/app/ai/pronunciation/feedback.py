from __future__ import annotations

import json
import re
from typing import Any, Dict

from app.ai.pronunciation.articulation import guide_for_word
from app.ai.pronunciation.g2p import get_pronunciation
from app.config import settings
from app.log import get_logger

log = get_logger("app.ai.pronunciation.feedback")


def request_pronun_feedback(
    scoring_report: Dict[str, Any],
    model: str = "",
    temperature: float = 0.6,
    max_tokens: int = 1200,
    system_prompt: str = "",
    user_label: str = "scoring_report",
) -> Dict[str, Any]:
    """Xin nhận xét AI: LLM local qua get_llm (llama.cpp).
    Chỉ gửi ScoringReport (không audio, không tự tính điểm — đúng luật đã khóa).
    system_prompt != "" cho phép caller (vd session feedback) dùng prompt gọn
    chuyên biệt thay vì prompt mặc định. LLM chết -> gợi ý theo quy tắc
    (không raise, API vẫn 200)."""
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
    """Đọc 2 prompt md riêng. Fallback feedback.md cũ nếu file mới thiếu."""
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
        log.warning("prompt feedback thieu/trong — feedback se chay prompt rong")
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
        log.warning("thieu prompt feedback_utterance/assessment")
    return out


PROMPTS = load_feedback_prompts()


SYSTEM_PROMPT = PROMPTS["utterance"]


SESSION_FEEDBACK_PROMPT = PROMPTS["session"]


THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def strip_reasoning(content: str) -> str:
    """Bỏ khối reasoning (<think>...</think>) model đôi khi kèm theo."""
    return THINK_BLOCK_RE.sub("", content or "").strip()


def extract_json(content: str) -> Dict[str, Any] | None:
    """LLM local tra JSON (co the kem text). Boc tach object JSON dau tien."""
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
            return None
    return None


async def generate_feedback(scoring_report: dict, model: str = "",
                            temperature: float = 0.6, max_tokens: int = 2000,
                            system_prompt: str = "", user_label: str = "scoring_report") -> dict:
    from app.ai import get_llm

    user_msg = f"{user_label}:\n" + json.dumps(scoring_report, ensure_ascii=False)[:12000]
    try:
        llm = get_llm(model=model, temperature=temperature, max_tokens=max_tokens,
                        reasoning="exclude")
        msg = await llm.ainvoke([
            {"role": "system", "content": system_prompt or SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ])
    except Exception as error:
        log.warning("LLM feedback không reachable (%s) — dùng gợi ý theo quy tắc", error)
        return build_fallback_feedback(scoring_report, user_label)
    content = getattr(msg, "content", "") or ""
    parsed = extract_json(content if isinstance(content, str) else str(content))
    if parsed:
        parsed.setdefault("model", (model or "").strip() or settings.llm_model)
        return parsed
    return {"feedback_raw": content, "model": (model or "").strip() or settings.llm_model, "usage": {}}


def build_fallback_feedback(scoring_report: dict, user_label: str = "scoring_report") -> dict:
    """Gợi ý theo quy tắc từ điểm đã chấm (không cần LLM).
    Dùng khi LLM local chết — API vẫn 200, không 502. Bao đủ keys cho cả
    2 frontend (utterance: pronunciation_feedback/priority_errors/...;
    session: error_words)."""
    def word_guide(word: str, issue: str) -> Dict[str, str]:
        try:
            arpa = get_pronunciation(word.split(",")[0].strip(), "en-US").get("arpa", [])
        except Exception:
            arpa = []
        return guide_for_word(word, arpa, issue)

    report = scoring_report or {}
    utts = report.get("utterances")
    if isinstance(utts, list):
        # Dạng session_scores: [{text, overall, bad_words, top_errors}]
        entries = []
        for u in utts:
            bad = u.get("bad_words") or []
            for b in bad[:5]:
                w = b.get("word") or "?"
                issue = f"{b.get('status', '')} {b.get('expected_ipa', '')}".strip()
                entries.append({"word": w, "issue": issue, "score": b.get("score"),
                                **word_guide(w, issue)})
            for t in (u.get("top_errors") or [])[:3]:
                w = ", ".join(t.get("examples", [])[:2]) or "?"
                issue = str(t.get("pattern", ""))
                entries.append({"word": w, "issue": issue, "score": None,
                                **word_guide(w, issue)})
        scored = [u for u in utts if isinstance(u.get("overall"), (int, float))]
        avg = round(sum(u["overall"] for u in scored) / len(scored), 1) if scored else 0.0
        n = len(utts)
    else:
        # Dạng scoring_report 1 câu: {scores, word_details, top_errors}
        entries = []
        for w in report.get("word_details") or []:
            if (w.get("status") or "ok") != "ok":
                word = w.get("word") or "?"
                issue = f"{w.get('status', '')} {w.get('expected_ipa', '')}".strip()
                entries.append({"word": word, "issue": issue, "score": w.get("score"),
                                **word_guide(word, issue)})
        for t in (report.get("top_errors") or [])[:3]:
            w = ", ".join(t.get("examples", [])[:2]) or "?"
            issue = str(t.get("pattern", ""))
            entries.append({"word": w, "issue": issue, "score": None,
                            **word_guide(w, issue)})
        overall = ((report.get("scores") or {}).get("overall"))
        avg = round(float(overall), 1) if isinstance(overall, (int, float)) else 0.0
        n = 1
    # Gom trùng từ, giữ tối đa 3 lỗi chính.
    seen, top = set(), []
    for e in entries:
        if e["word"] not in seen:
            seen.add(e["word"])
            top.append(e)
        if len(top) >= 3:
            break
    if top:
        listed = "; ".join(f"'{e['word']}' ({e['issue']})" for e in top)
        summary = f"Chấm {n} câu, điểm trung bình {avg}. Cần sửa nhất: {listed}."
    else:
        summary = f"Chấm {n} câu, điểm trung bình {avg}. Không phát hiện lỗi âm rõ rệt — giữ phong độ."
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
        "pronunciation_feedback": summary,
        "stress_feedback": "",
        "intonation_feedback": "",
        "fluency_feedback": "",
        "priority_errors": [{"word": e["word"], "issue": e["issue"],
                             "advice": e["how_to"], "vi": e["vi"]} for e in top],
        "error_words": error_words,
        "practice_plan": practice_plan,
        "model": "rule-based-fallback",
        "fallback": True,
        "usage": {},
    }

