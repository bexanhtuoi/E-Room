from __future__ import annotations

import json
import math
import re
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import numpy as np

from app.ai.pronunciation.align import align_transcripts, apply_forced_spans
from app.ai.pronunciation.audio import check_audio_quality, extract_f0, load_wav_16k, vad_segments
from app.ai.pronunciation.metrics import calculate_overall, score_completeness, score_fluency
from app.ai.pronunciation.models import (
    BLANK_RATIO_MISALIGNED,
    FRAME_STRIDE_S,
    acoustic_model_id,
    ctc_forced_align,
    get_acoustic_model,
    load_torch,
)
from app.ai.pronunciation.phonemes import score_phones, score_sounds, score_stress
from app.config import settings
from app.log import get_logger

log = get_logger("app.ai.pronunciation")

# Cổng chấm local: serialize inference wav2vec2/XLSR để máy host web không
# quá tải khi 3-4 người bấm chấm cùng lúc (model đã cache, chỉ inference
# là nặng). Rescore endpoint là sync def (chạy trong worker thread) nên
# threading.Semaphore là đủ, không cần Celery cho tới khi tải cao hơn
# (lúc đó offload qua PRONUN_BASE_URL).
scoring_gate = threading.Semaphore(max(1, settings.scoring_max_parallel))


def split_words_with_spans(ref_ctc: str) -> tuple[list[str], list[list[int]]]:
    chars = list(ref_ctc)
    word_list: list[str] = []
    per_word_spans: list[list[int]] = []
    word, idxs = "", []

    for ci, ch in enumerate(chars):
        if ch == "|":
            if word:
                word_list.append(word)
                per_word_spans.append(idxs)
                word, idxs = "", []
        else:
            word += ch
            idxs.append(ci)

    if word:
        word_list.append(word)
        per_word_spans.append(idxs)

    return word_list, per_word_spans


def greedy_decode(processor, pred_ids: list[int], blank_id: int) -> str:
    vocab_list = [None] * len(processor.tokenizer)

    for tok, i in processor.tokenizer.get_vocab().items():
        if 0 <= i < len(vocab_list):
            vocab_list[i] = tok

    collapsed, prev = [], None

    for pid in pred_ids:
        if pid != prev:
            if pid != blank_id:
                collapsed.append(vocab_list[pid] if vocab_list[pid] else "")
        prev = pid

    return "".join(collapsed).replace("|", " ").strip()


def normalize_reference(text: str, vocab: set[str]) -> str:
    t = (text or "").upper().strip()
    t = re.sub(r"\s+", " ", t)
    t = t.replace("-", " ")
    kept = "".join(ch for ch in t if ch in vocab or ch == " ")
    kept = re.sub(r"\s+", " ", kept).strip()
    return kept


def score_utterance(waveform_16k, sample_rate: int, reference_text: str) -> dict[str, Any]:
    torch = load_torch()

    processor, model = get_acoustic_model()

    device = next(model.parameters()).device

    wav = np.asarray(waveform_16k, dtype=np.float32).reshape(-1)

    if sample_rate != 16000:
        try:
            import librosa

            wav = librosa.resample(wav, orig_sr=sample_rate, target_sr=16000).astype(np.float32)
        except Exception:
            ratio = 16000 / float(sample_rate)

            idx = (np.arange(int(len(wav) * ratio)) / ratio).astype(int)

            idx = np.clip(idx, 0, len(wav) - 1)

            wav = wav[idx]

        sample_rate = 16000

    duration_s = len(wav) / 16000.0

    if duration_s > 600:
        return {"error": "Audio dài quá 10 phút — hãy chia thành nhiều lần chấm.", "transcript_norm": ""}

    inputs = processor(wav, sampling_rate=16000, return_tensors="pt", padding=True)

    input_values = inputs.input_values.to(device)

    with torch.no_grad():
        logits = model(input_values).logits[0].cpu()

    log_probs = torch.log_softmax(logits, dim=-1)

    total_frames, num_classes = log_probs.shape

    vocab = set(processor.tokenizer.get_vocab().keys())
    vocab.discard(processor.tokenizer.pad_token or "<pad>")
    vocab.discard(processor.tokenizer.unk_token or "<unk>")

    ref_norm = normalize_reference(reference_text, vocab | {"|", "'", " "})

    if not ref_norm:
        return {"error": "Câu rỗng hoặc không có ký tự hợp lệ (A-Z).", "transcript_norm": ""}

    ref_ctc = ref_norm.replace(" ", "|")

    target_ids = processor.tokenizer(ref_ctc).input_ids

    blank_id = model.config.pad_token_id if model.config.pad_token_id is not None else 0

    align, path_score = ctc_forced_align(log_probs, list(target_ids), int(blank_id))

    pred_ids: list[int] = torch.argmax(logits, dim=-1).tolist()

    num_targets = len(target_ids)
    char_lp: list[float] = []
    char_span: list[tuple[int, int]] = []
    char_ok: list[bool] = []

    for i, tid in enumerate(target_ids):
        s = 2 * i + 1

        frames = [t for t in range(total_frames) if align[t] == s]

        if frames:
            vals = [float(log_probs[t, int(tid)]) for t in frames]
            char_lp.append(sum(vals) / len(vals))
            char_span.append((frames[0], frames[-1]))
            char_ok.append(True)
        else:
            char_lp.append(-10.0)
            char_span.append((-1, -1))
            char_ok.append(False)

    words_out: list[dict[str, Any]] = []

    word_list, per_word_spans = split_words_with_spans(ref_ctc)

    for wstr, idxs in zip(word_list, per_word_spans):
        lps = [char_lp[i] for i in idxs if 0 <= i < len(char_lp)]

        oks = [char_ok[i] for i in idxs if 0 <= i < len(char_ok)]

        starts = [char_span[i][0] for i in idxs if 0 <= i < len(char_span) and char_span[i][0] >= 0]

        ends = [char_span[i][1] for i in idxs if 0 <= i < len(char_span) and char_span[i][1] >= 0]

        if starts and ends:
            f0, f1 = min(starts), max(ends)

            span_frames = list(range(f0, f1 + 1))

            n_blank = sum(1 for t in span_frames if pred_ids[t] == blank_id)

            blank_ratio = n_blank / max(1, len(span_frames))

            start_s = round(f0 * FRAME_STRIDE_S, 2)

            end_s = round((f1 + 1) * FRAME_STRIDE_S, 2)
        else:
            blank_ratio, start_s, end_s = 1.0, 0.0, 0.0

        if not any(oks):
            status = "no_evidence"
        elif blank_ratio > BLANK_RATIO_MISALIGNED:
            status = "misaligned"
        else:
            status = "scored"

        if status == "scored":
            avg = sum(lps) / len(lps) if lps else -10.0

            prob = math.exp(max(avg, -10.0))

            score = round(max(0.0, min(100.0, prob * 100.0)), 1)
        else:
            avg = sum(lps) / len(lps) if lps else -10.0

            score = 0.0

        words_out.append(
            {
                "word": wstr,
                "avg_log_prob": round(avg, 4),
                "score_0_100": score,
                "status": status,
                "blank_ratio": round(blank_ratio, 3),
                "start_s": start_s,
                "end_s": end_s,
            }
        )

    scored = [x for x in words_out if x["status"] == "scored"]

    no_ev = [x for x in words_out if x["status"] != "scored"]

    if scored:
        overall = sum(x["score_0_100"] for x in scored) / len(scored)

        avg_lp_all = sum(x["avg_log_prob"] for x in scored) / len(scored)
    else:
        overall, avg_lp_all = 0.0, -10.0

    try:
        ctc = torch.nn.CTCLoss(blank=int(blank_id), zero_infinity=True)

        input_lengths = torch.tensor([total_frames])

        target_lengths = torch.tensor([num_targets])

        loss = float(ctc(log_probs.unsqueeze(1), torch.tensor([target_ids]), input_lengths, target_lengths))
    except Exception:
        loss = float("nan")

    try:
        greedy = greedy_decode(processor, pred_ids, blank_id)
    except Exception:
        greedy = ""

    if overall >= 85:
        level = "Xuất sắc"
    elif overall >= 70:
        level = "Tốt"
    elif overall >= 50:
        level = "Trung bình"
    else:
        level = "Cần luyện thêm"

    return {
        "transcript_norm": ref_norm,
        "greedy_decoded": greedy,
        "overall_0_100": round(overall, 1),
        "overall_0_10": round(overall / 10.0, 2),
        "level": level,
        "avg_log_prob": round(float(avg_lp_all), 4),
        "ctc_loss": loss,
        "num_frames": total_frames,
        "duration_s": round(duration_s, 2),
        "model": acoustic_model_id(),
        "n_scored": len(scored),
        "n_no_evidence": len(no_ev),
        "words": words_out,
    }


# Deterministic pipeline — LLM feedback KHÔNG được gọi ở đây.
def score_attempt_v2(wav: np.ndarray, sr: int, whisper_raw: str, user_corrected: str,
                     mode: str = "free_speaking", original_text: str | None = None,
                     accent: str = "en-US", whisper_segments: list[dict] | None = None,
                     char_words: list[dict] | None = None, greedy_text: str = "") -> dict:
    t0 = time.time()
    warnings: list[str] = []
    if not (user_corrected or "").strip():
        return {"error": "user_corrected rỗng — hãy sửa transcript trước khi chấm."}

    aligned = align_transcripts(whisper_raw, user_corrected, whisper_segments)

    if char_words:
        aligned = apply_forced_spans(aligned, char_words)
    else:
        warnings.append("missing forced aligner spans — stress/sounds dùng whisper hint, độ tin cậy thấp")

    snd = None

    gop_model = None

    try:
        ph = score_phones(wav, sr, user_corrected, accent)

        if "error" not in ph:
            snd = {
                "sounds": ph["sounds"],
                "word_details": ph["word_details"],
                "phonemes": ph["phonemes"],
                "top_errors": ph["top_errors"],
            }

            gop_model = ph.get("model")

    except Exception as e:
        warnings.append(f"phoneme GOP failed ({str(e)[:120]}), fallback char-level acoustic")

    if snd is None:
        # Fallback char-level: KHÔNG gọi là GOP, chỉ là acoustic likelihood.
        snd = score_sounds(char_words or [], greedy_text=greedy_text or whisper_raw, accent=accent)

        warnings.append("Điểm Sounds hiện tại là char-level acoustic likelihood, KHÔNG phải GOP chuẩn")

    st = score_stress(snd.get("word_details") or char_words or [], wav, sr, accent)

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
        "scorer_version": "scorer-v2-mvp",
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
    audio_path: Path | str,
    reference_text: str,
    language: str = "en",
) -> Dict[str, Any]:
    raw = Path(audio_path).read_bytes()

    if len(raw) > 100 * 1024 * 1024:
        raise ValueError("Audio > 100MB.")

    queued_at = time.monotonic()

    with scoring_gate:
        waited = time.monotonic() - queued_at

        if waited > 1.0:
            log.info("scoring queued %.1fs (nhiều người chấm cùng lúc)", waited)

        wav, sr = load_wav_16k(raw)

        r = score_utterance(wav, int(sr), reference_text)

        if "error" in r and "words" not in r:
            raise RuntimeError(f"local scorer: {r.get('error')}")

        report = score_attempt_v2(
            wav, sr, "", reference_text, "free_speaking", None, "en-US",
            None, r.get("words", []), r.get("greedy_decoded", ""),
        )

    if "error" in report and "scores" not in report:
        raise RuntimeError(f"local scorer: {report.get('error')}")

    return report_to_hook(report, "local-v2")


def score_via_pronun_service(
    audio_path: Path | str,
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
    audio_path: Path | str,
    reference_text: str,
    language: str = "en",
) -> Dict[str, Any]:
    try:
        return score_local(audio_path, reference_text, language)
    except Exception as error:
        log.warning("local scoring failed (%s), thử pronun service", error)
    return score_via_pronun_service(audio_path, reference_text, language)


def score_pronunciation(
    audio_path: Optional[Path | str] = None,
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
            log.warning("wav2vec2 scoring failed, fallback heuristic | err=%s", error)
            return heuristic("scorer_failed")
    if prefer_wav2vec and reference_text.strip():
        log.warning("scoring thiếu audio (audio_path=%r) — fallback heuristic", audio_path)
        return heuristic("no_audio")
    return heuristic("heuristic")
