from __future__ import annotations

import contextlib
import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import httpx
import numpy as np

from app.ai.pronunciation.align import align_transcripts
from app.ai.pronunciation.audio import check_audio_quality, extract_f0, load_wav_16k, vad_segments
from app.ai.pronunciation.metrics import calculate_overall, score_completeness, score_fluency
from app.ai.pronunciation.models import ensure_phone_ready
from app.ai.pronunciation.phonemes import score_phones, score_stress
from app.config import settings
from app.log import get_logger

log = get_logger("app.ai.pronunciation")

# 1. Cổng chấm trong process: serialize các thread cùng worker
# 2. Slot Redis (claim_scoring_slot): giới hạn xuyên process toàn cụm,
# vì threading.Semaphore mỗi process giữ riêng (api + mỗi worker Celery
# prefork đều có 1 cổng + 1 bản model) nên không chặn được OOM khi đông người.
scoring_gate = threading.Semaphore(max(1, settings.scoring_max_parallel))

SCORING_SLOT_NAME = "xlsr_scoring"

SCORING_SLOT_TTL = 900


@contextlib.contextmanager
def claim_scoring_slot(timeout_s: float = 300.0):
    # 1. Xếp hàng xuyên process: tối đa scoring_max_parallel inference toàn cụm
    try:
        from app.integration.redis import acquire_slot, release_slot
    except Exception as error:
        log.warning("không dùng được Redis slot, chỉ giới hạn trong process | err=%s", error)

        yield

        return

    limit = max(1, settings.scoring_max_parallel)

    start = time.monotonic()

    announced = False

    while True:
        try:
            taken = acquire_slot(SCORING_SLOT_NAME, limit, SCORING_SLOT_TTL)
        except Exception as error:
            log.warning("Redis slot lỗi, chỉ giới hạn trong process | err=%s", error)

            yield

            return

        if taken:
            break

        waited = time.monotonic() - start

        if waited >= timeout_s:
            raise RuntimeError("Hàng đợi chấm điểm đang bận — hãy thử lại sau.")

        if waited > 10.0 and not announced:
            log.info("chờ lượt chấm XLSR (giới hạn %s) | cho=%ss", limit, round(waited, 1))

            announced = True

        time.sleep(1.0)

    try:
        yield
    finally:
        try:
            release_slot(SCORING_SLOT_NAME)
        except Exception as error:
            log.warning("nhả Redis slot lỗi | err=%s", error)


def apply_xlsr_spans(aligned: List[Dict], word_details: List[Dict]) -> List[Dict]:
    # 1. Vá span: XLSR cho start_s/end_s từng từ, map ngược vào alignment
    queues: Dict[str, List[Dict]] = {}

    for detail in word_details or []:
        key = str(detail.get("word", "")).upper()

        queues.setdefault(key, []).append(detail)

    out: List[Dict] = []

    for item in aligned or []:
        key = str(item.get("word", "")).upper()

        queue = queues.get(key)

        if queue:
            detail = queue.pop(0)

            has_span = detail.get("status") in ("ok", "misaligned", "pronunciation_error")

            out.append({
                **item,
                "start_s": detail.get("start_s"),
                "end_s": detail.get("end_s"),
                "span_available": bool(has_span and detail.get("start_s") is not None),
            })
        else:
            out.append(item)

    return out


# 2. Deterministic pipeline — LLM feedback KHÔNG được gọi ở đây.
def score_attempt_v2(
    wav: np.ndarray,
    sr: int,
    whisper_raw: str,
    user_corrected: str,
    mode: str = "free_speaking",
    original_text: Optional[str] = None,
    accent: str = "en-US",
    whisper_segments: Optional[List[Dict]] = None,
    char_words: Optional[List[Dict]] = None,
    greedy_text: str = "",
) -> Dict[str, Any]:
    t0 = time.time()

    warnings: List[str] = []

    if not (user_corrected or "").strip():
        return {"error": "user_corrected rỗng — hãy sửa transcript trước khi chấm."}

    aligned = align_transcripts(whisper_raw, user_corrected, whisper_segments)

    # 2. Tham số cũ giữ để tương thích, XLSR không dùng tới
    if char_words:
        warnings.append("char_words bị bỏ qua — đã chuyển sang span phoneme XLSR")

    snd = None

    gop_model = None

    try:
        ph = score_phones(wav, sr, user_corrected, accent)
    except Exception as error:
        return {"error": f"XLSR lỗi khi chấm: {error}", "warnings": warnings}

    if "error" in ph:
        # 3. Không bịa điểm 0: trả lỗi thật để router giữ điểm cũ
        return {"error": ph.get("error", "XLSR thất bại"), "warnings": warnings}

    snd = {
        "sounds": ph["sounds"],
        "word_details": ph["word_details"],
        "phonemes": ph["phonemes"],
        "top_errors": ph["top_errors"],
    }

    gop_model = ph.get("model")

    # 4. Vá span XLSR vào alignment để UI/seek dùng được
    aligned = apply_xlsr_spans(aligned, snd["word_details"])

    if aligned and not any(w.get("span_available") for w in aligned):
        warnings.append("Không lấy được timestamp từng chữ — kiểm tra audio và câu chấm")

    st = score_stress(snd.get("word_details") or [], wav, sr, accent)

    segs, pauses = vad_segments(wav, sr)

    fl = score_fluency(len(wav) / sr, len([w for w in aligned if w["alignment"] != "deletion"]), pauses, whisper_raw)

    details = snd["word_details"]

    no_evidence_count = sum(1 for d in details if d.get("status") == "no_evidence")

    cp = score_completeness(original_text, user_corrected, mode, details)

    if mode != "read_aloud" and cp.get("missing_words"):
        names = ", ".join(cp["missing_words"][:6])

        warnings.append(f"{len(cp['missing_words'])} từ chưa hoàn thiện, 0 điểm hoặc không tìm thấy ({names}).")

    f0 = extract_f0(wav, sr)

    monotone = f0["std_f0"] < 15 and f0["voiced_ratio"] > 0.1

    overall = calculate_overall(snd["sounds"], st["stress"], fl["score"], cp["score"])

    return {
        "scores": {
            "sounds": snd["sounds"],
            "stress": st["stress"],
            "fluency": fl["score"],
            "completeness": cp["score"],
            "intonation": None,
            "overall": overall,
        },
        "texts": {
            "original": original_text,
            "whisper_raw": whisper_raw,
            "user_corrected": user_corrected,
        },
        "reference": {
            "accent": accent,
            "voice_id": "af_heart",
        },
        "word_details": snd["word_details"],
        "phonemes": snd["phonemes"],
        "stress_detail": st["details"],
        "intonation": {
            "median_f0": f0["median_f0"],
            "std_f0": f0["std_f0"],
            "range_f0": f0["range_f0"],
            "final_slope": f0["final_slope"],
            "monotone": monotone,
            "note": "MVP: monotone detection only, DTW vs Kokoro deferred to v1.1",
        },
        "fluency": {**fl},
        "completeness": cp,
        "top_errors": snd["top_errors"],
        "alignment": aligned,
        "speech_segments": segs,
        "scorer_version": "scorer-v2-mvp-xlsr-only",
        "gop_model": gop_model,
        "n_scored": len(details) - no_evidence_count,
        "n_no_evidence": no_evidence_count,
        "warnings": warnings,
        "compute_s": round(time.time() - t0, 2),
    }


def heuristic_score(
    confidence: float = 1.0,
    avg_logprob: float = 0.0,
    duration: float = 0.0,
    words_count: int = 0,
) -> Dict[str, Any]:
    conf_part = max(0.0, min(1.0, confidence)) * 60.0
    # avg_logprob thường nằm [-2, 0]; map về 0-25 điểm
    logprob_norm = max(0.0, min(1.0, (avg_logprob + 2.0) / 2.0))

    fluency = 0.0

    if duration > 0 and words_count > 0:
        wpm = (words_count / duration) * 60.0
        # 90-170 wpm là vùng tự nhiên cho speaking practice
        if 90 <= wpm <= 170:
            fluency = 15.0
        elif 60 <= wpm < 90 or 170 < wpm <= 210:
            fluency = 10.0
        else:
            fluency = 5.0
    score = round(conf_part + logprob_norm * 25.0 + fluency, 1)

    return {
        "score": min(100.0, score),
        "method": "heuristic-v1",
        "wav2vec_ready": False,
        "details": {
            "confidence": confidence,
            "avg_logprob": avg_logprob,
            "duration": duration,
            "words_count": words_count,
        },
    }


def report_to_hook(report: Dict[str, Any], method: str) -> Dict[str, Any]:
    scores = report.get("scores", {})

    return {
        "score": float(scores.get("overall", 0.0)),
        "method": method,
        "wav2vec_ready": True,
        "scorer_version": report.get("scorer_version", ""),
        "gop_model": report.get("gop_model", ""),
        "details": {
            "sounds": scores.get("sounds"),
            "stress": scores.get("stress"),
            "fluency": scores.get("fluency"),
            "completeness": scores.get("completeness"),
            "n_scored": report.get("n_scored"),
            "n_no_evidence": report.get("n_no_evidence"),
            "duration_s": report.get("duration_s"),
            "top_errors": report.get("top_errors", []),
            "warnings": report.get("warnings", []),
        },
        "report": report,
    }


def score_local(
    audio_path: Union[Path, str],
    reference_text: str,
    language: str = "en",
) -> Dict[str, Any]:
    raw = Path(audio_path).read_bytes()

    if len(raw) > 100 * 1024 * 1024:
        raise ValueError("Audio > 100MB.")

    # 5. Fail-fast trước khi giữ gate: model lỗi thì báo ngay, không treo hàng đợi
    try:
        ensure_phone_ready()
    except Exception as error:
        raise RuntimeError(f"local scorer: {error}") from error

    queued_at = time.monotonic()

    # 6. Giữ slot cụm trước, cổng process sau: đúng 1 inference tại mọi thời điểm
    with claim_scoring_slot(timeout_s=settings.pronun_timeout):
        with scoring_gate:
            waited = time.monotonic() - queued_at

            if waited > 1.0:
                log.info("scoring queued %.1fs (nhiều người chấm cùng lúc)", waited)

            wav, sr = load_wav_16k(raw)

            # 3. Chặn audio quá dài thay cho check cũ trong score_utterance
            duration_s = len(wav) / 16000.0

            if duration_s > 600:
                raise RuntimeError("local scorer: Audio dài quá 10 phút — hãy chia thành nhiều lần chấm.")

            # 4. XLSR-only: không còn char_words/greedy từ wav2vec-base
            report = score_attempt_v2(
                wav,
                sr,
                "",
                reference_text,
                "free_speaking",
                None,
                "en-US",
                None,
                None,
                "",
            )

    if "error" in report and "scores" not in report:
        raise RuntimeError(f"local scorer: {report.get('error')}")

    return report_to_hook(report, "local-v2")


def score_via_pronun_service(
    audio_path: Union[Path, str],
    reference_text: str,
    language: str = "en",
) -> Dict[str, Any]:
    base = (settings.pronun_base_url or "").strip().rstrip("/")

    if not base:
        raise NotImplementedError(
            "PRONUN_BASE_URL chưa cấu hình — chấm local hoặc heuristic."
        )
    audio_bytes = Path(audio_path).read_bytes()

    if len(audio_bytes) > 100 * 1024 * 1024:
        raise ValueError("Audio > 100MB.")
    payload = {
        "whisper_raw": "",
        "user_corrected": reference_text,
        "mode": "free_speaking",
        "accent": "en-US" if (language or "en").lower().startswith("en") else "en-US",
    }

    with httpx.Client(timeout=settings.pronun_timeout) as client:
        resp = client.post(
            f"{base}/api/speaking/score",
            files={"audio": ("rec.wav", audio_bytes, "audio/wav")},
            data={"payload": json.dumps(payload)},
        )

        resp.raise_for_status()

        report = resp.json()
    if "error" in report and "scores" not in report:
        raise RuntimeError(f"pronun scorer: {report.get('error')}")
    return report_to_hook(report, "pronun-v2")


def score_with_wav2vec2(
    audio_path: Union[Path, str],
    reference_text: str,
    language: str = "en",
) -> Dict[str, Any]:
    # 5. Tên cũ giữ để tương thích test/mocks, ruột giờ là XLSR-only
    try:
        return score_local(audio_path, reference_text, language)
    except Exception as error:
        log.warning("local scoring failed (%s), thử pronun service", error)
    return score_via_pronun_service(audio_path, reference_text, language)


def score_pronunciation(
    audio_path: Optional[Union[Path, str]] = None,
    reference_text: str = "",
    language: str = "en",
    confidence: float = 1.0,
    avg_logprob: float = 0.0,
    duration: float = 0.0,
    words: Optional[List[Dict[str, Any]]] = None,
    prefer_wav2vec: bool = True,
) -> Dict[str, Any]:
    words = words or []

    def heuristic(reason: str) -> Dict[str, Any]:
        result = heuristic_score(
            confidence=confidence,
            avg_logprob=avg_logprob,
            duration=duration,
            words_count=len(words),
        )

        result["reason"] = reason

        return result

    if prefer_wav2vec and audio_path and reference_text.strip():
        try:
            path = Path(audio_path)

            if path.exists():
                try:
                    probe_wav, probe_sr = load_wav_16k(path.read_bytes())

                    quality = check_audio_quality(probe_wav, probe_sr)
                except Exception:
                    quality = {"ok": True, "peak": 0.0, "rms": 0.0, "duration_s": 0.0, "hint": ""}
                if not quality["ok"]:
                    log.info(
                        "scoring skipped, audio too quiet | peak=%s rms=%s path=%s",
                        quality["peak"], quality["rms"], path,
                    )

                    result = heuristic("quiet_audio")

                    result["audio_quality"] = quality

                    return result
                return score_with_wav2vec2(path, reference_text, language)
            log.warning("scoring thiếu audio (file không tồn tại: %s) — fallback heuristic", audio_path)

            return heuristic("no_audio")
        except NotImplementedError as error:
            log.warning("local scoring failed và chưa cấu hình pronun service — fallback heuristic | err=%s", error)

            return heuristic("scorer_failed")
        except Exception as error:
            log.warning("local scoring failed, fallback heuristic | err=%s", error)

            return heuristic("scorer_failed")
    if prefer_wav2vec and reference_text.strip():
        log.warning("scoring thiếu audio (audio_path=%r) — fallback heuristic", audio_path)

        return heuristic("no_audio")
    return heuristic("heuristic")
