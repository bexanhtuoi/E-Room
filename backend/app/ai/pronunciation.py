"""Chấm điểm phát âm cho E-Room — TẤT CẢ trong 1 file (gọn, không thư mục con).

Nội dung (giữ nguyên logic từng hàm, chỉ gộp + chia mục):
  Part 1  Audio: load wav 16k + VAD + F0 (cuốn từ speech_audio).
  Part 2  Từ điển phát âm: CMUdict full + g2p-en fallback + ARPAbet->IPA.
  Part 3  Alignment: whisper_raw <-> user_corrected (text + forced spans).
  Part 4  CTC acoustic: wav2vec2 forced align char-level (word spans thật).
  Part 5  Metrics: fluency + completeness + overall.
  Part 6  Sounds: phoneme-level từ char evidence (fallback khi chưa có GOP thật).
  Part 7  Stress: nhấn âm theo syllable spans thật.
  Part 8  Phoneme GOP thật: XLSR-espeak (1 pass, Witt & Young).
  Part 9  Pipeline: audio + texts -> ScoringReport (deterministic).
  Part 10 Hook: entry-point cho router (local -> pronun service -> heuristic)
          + xin nhận xét AI (LLM local, chỉ đọc report).

Thứ tự thử: local pipeline (máy chạy backend gánh compute) -> Pronun service
qua PRONUN_BASE_URL (máy AI) -> heuristic. Interface `score_pronunciation`
không đổi nên caller (speech.py) không phải sửa gì.
"""

from __future__ import annotations

import difflib
import functools
import glob
import io
import json
import math
import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import numpy as np

from app.config import settings
from app.log import get_logger

log = get_logger("app.ai.pronunciation")

# Cổng chấm local: serialize inference wav2vec2/XLSR để máy host web không
# quá tải khi 3-4 người bấm chấm cùng lúc (model đã cache, chỉ inference
# là nặng). Rescore endpoint là sync def (chạy trong worker thread) nên
# threading.Semaphore là đủ, không cần Celery cho tới khi tải cao hơn
# (lúc đó offload qua PRONUN_BASE_URL).
_scoring_gate = threading.Semaphore(max(1, settings.scoring_max_parallel))


# ═══════════════════════════════════════════════════════════════════
# Part 1 — Audio: load 16k mono + VAD + RMS + pYIN
# ═══════════════════════════════════════════════════════════════════

def load_wav_16k(raw: bytes) -> tuple[np.ndarray, int]:
    import soundfile as sf
    wav, sr = sf.read(io.BytesIO(raw), dtype="float32", always_2d=False)
    wav = np.asarray(wav, dtype=np.float32).reshape(-1)
    if getattr(wav, "ndim", 1) > 1:
        wav = np.mean(wav, axis=-1)
    if sr != 16000:
        try:
            import librosa
            wav = librosa.resample(wav, orig_sr=sr, target_sr=16000).astype(np.float32)
        except Exception:
            ratio = 16000 / float(sr)
            idx = (np.arange(int(len(wav) * ratio)) / ratio).astype(int)
            idx = np.clip(idx, 0, len(wav) - 1)
            wav = wav[idx]
        sr = 16000
    return wav, sr


def frame_rms(wav: np.ndarray, frame_len: int = 320) -> np.ndarray:
    n = max(1, len(wav) // frame_len)
    out = np.zeros(n, dtype=np.float32)
    for i in range(n):
        seg = wav[i * frame_len:(i + 1) * frame_len]
        out[i] = float(np.sqrt(np.mean(seg ** 2) + 1e-12))
    return out


def vad_segments(wav: np.ndarray, sr: int = 16000, energy_thr: float = 0.003,
                 silence_s: float = 0.5, min_speech_s: float = 0.3) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """Trả (speech_segments, pauses). Không cắt audio, chỉ đánh dấu.
    Dùng cho file dài free_speaking: chunk theo speech_segments nếu segment > 20s thì cắt tiếp ở pause."""
    hop = 320  # 20ms
    rms = frame_rms(wav, hop)
    voiced = rms >= energy_thr
    segs: list[tuple[float, float]] = []
    start = None
    for i, v in enumerate(voiced):
        t = i * hop / sr
        if v and start is None:
            start = t
        elif not v and start is not None:
            # đòi im lặng liên tục silence_s mới đóng segment
            gap_frames = int(silence_s * sr / hop)
            if i + gap_frames >= len(voiced) or not voiced[i:i + gap_frames].any():
                end = t
                if end - start >= min_speech_s:
                    segs.append((round(start, 2), round(end, 2)))
                start = None
    if start is not None:
        end = len(wav) / sr
        if end - start >= min_speech_s:
            segs.append((round(start, 2), round(end, 2)))
    pauses: list[tuple[float, float]] = []
    prev_end = 0.0
    for s, e in segs:
        if s - prev_end >= 0.05:
            pauses.append((round(prev_end, 2), round(s, 2)))
        prev_end = e
    total = len(wav) / sr
    if total - prev_end >= 0.05:
        pauses.append((round(prev_end, 2), round(total, 2)))
    return segs, pauses


def chunk_long_audio(wav: np.ndarray, sr: int = 16000, max_chunk_s: float = 20.0) -> list[tuple[float, float]]:
    """Chia file dài thành chunk <= max_chunk_s, ưu tiên cắt ở pause."""
    segs, _ = vad_segments(wav, sr)
    if not segs:
        total = len(wav) / sr
        return [(0.0, round(total, 2))]
    chunks: list[tuple[float, float]] = []
    for s, e in segs:
        while e - s > max_chunk_s:
            chunks.append((round(s, 2), round(s + max_chunk_s, 2)))
            s += max_chunk_s
        chunks.append((round(s, 2), round(e, 2)))
    return chunks


def extract_f0(wav: np.ndarray, sr: int = 16000) -> dict[str, Any]:
    """pYIN F0. Trả median/std/p10/p90 + curve thưa để vẽ."""
    try:
        import librosa
        f0, voiced_flag, _ = librosa.pyin(wav, fmin=librosa.note_to_hz("C2"),
                                          fmax=librosa.note_to_hz("C7"), sr=sr)
        import numpy as _np
        valid = f0[~_np.isnan(f0)] if f0 is not None else _np.array([])
        if len(valid) == 0:
            return {"median_f0": 0.0, "std_f0": 0.0, "p10": 0.0, "p90": 0.0,
                    "range_f0": 0.0, "final_slope": 0.0, "curve_t": [], "curve_f0": [], "voiced_ratio": 0.0}
        p10, p90 = float(_np.percentile(valid, 10)), float(_np.percentile(valid, 90))
        # slope 0.5s cuối
        tail = valid[-25:] if len(valid) >= 25 else valid
        slope = float(tail[-1] - tail[0]) if len(tail) >= 2 else 0.0
        # curve thưa 100 điểm để frontend vẽ
        idx = _np.linspace(0, len(f0) - 1, min(100, len(f0))).astype(int)
        curve_t = [round(float(i) * 512 / sr, 2) for i in idx]  # pyin hop mặc định 512
        curve_f0 = [round(float(f0[i]) if not _np.isnan(f0[i]) else 0.0, 1) for i in idx]
        return {"median_f0": round(float(_np.median(valid)), 1), "std_f0": round(float(_np.std(valid)), 1),
                "p10": round(p10, 1), "p90": round(p90, 1), "range_f0": round(p90 - p10, 1),
                "final_slope": round(slope, 1), "curve_t": curve_t, "curve_f0": curve_f0,
                "voiced_ratio": round(float(len(valid)) / max(1, len(f0)), 3)}
    except Exception as e:
        return {"median_f0": 0.0, "std_f0": 0.0, "p10": 0.0, "p90": 0.0, "range_f0": 0.0,
                "final_slope": 0.0, "curve_t": [], "curve_f0": [], "voiced_ratio": 0.0, "error": str(e)[:200]}


# ═══════════════════════════════════════════════════════════════════
# Part 2 — Từ điển phát âm: CMUdict full + g2p-en + ARPAbet->IPA
# ═══════════════════════════════════════════════════════════════════

_IPA_MAP = {
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
    return _IPA_MAP.get(base, base.lower())


_VOWEL_BASE = {
    "AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY",
    "IH", "IY", "OW", "OY", "UH", "UW",
}


def _strip_stress(phone: str) -> str:
    return phone.rstrip("012")


def _is_vowel(phone: str) -> bool:
    return _strip_stress(phone) in _VOWEL_BASE


@functools.lru_cache(maxsize=1)
def _g2p():
    from g2p_en import G2p
    return G2p()


def _from_g2p(word_upper: str) -> tuple[list[str], bool]:
    """Trả (arpa_phones, oov=True). g2p-en sinh cả stress số."""
    try:
        raw: list[str] = _g2p()(word_upper.lower())
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
            if _strip_stress(p) in _VOWEL_BASE:
                phones[i] = _strip_stress(p) + "1"
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
        arpa, oov = _from_g2p(wu)
    syllables: list[list[str]] = []
    cur: list[str] = []
    for ph in arpa:
        cur.append(ph)
        if _is_vowel(ph):
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


# ═══════════════════════════════════════════════════════════════════
# Part 3 — Alignment whisper_raw <-> user_corrected
# Bước 1 (text): Needleman-Wunsch trên từ -> match/substitution/insertion/deletion.
# Bước 2 (time): span cuối BẮT BUỘC từ forced aligner trên user_corrected,
# không tin Whisper timestamp (chỉ gợi ý ban đầu + UI).
# ═══════════════════════════════════════════════════════════════════

def _tok_words(text: str) -> list[str]:
    return [w for w in re.findall(r"[A-Za-z']+", (text or "").lower())]


def align_transcripts(whisper_raw: str, user_corrected: str, whisper_segments: list[dict] | None = None) -> list[dict]:
    a, b = _tok_words(whisper_raw), _tok_words(user_corrected)
    n, m = len(a), len(b)
    # DP edit distance
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)
    # traceback
    i, j = n, m
    ops: list[dict] = []
    # map whisper word index -> timestamp gợi ý
    seg_words: list[dict] = []
    if whisper_segments:
        for seg in whisper_segments:
            for w in seg.get("words", []) or []:
                seg_words.append(w)
    def whisper_hint(idx: int) -> dict:
        # idx: index trong a
        if 0 <= idx < len(seg_words):
            w = seg_words[idx]
            return {"start_s": w.get("start"), "end_s": w.get("end"), "confidence": w.get("confidence")}
        # fallback: whisper_segments dạng {start,end,text} -> chia đều từ (chỉ gợi ý, scorer không tin)
        flat = " ".join(s.get("text", "") for s in (whisper_segments or [])).lower()
        return {"start_s": None, "end_s": None, "confidence": None}
    while i > 0 or j > 0:
        if i > 0 and j > 0 and a[i - 1] == b[j - 1]:
            h = whisper_hint(i - 1)
            ops.append({"word": b[j - 1], "source_word": a[i - 1], "alignment": "match",
                        "start_s": h["start_s"], "end_s": h["end_s"],
                        "span_available": h["start_s"] is not None, "ignored_for_pronunciation": False})
            i -= 1; j -= 1
        elif i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + 1:
            h = whisper_hint(i - 1)
            ops.append({"word": b[j - 1], "source_word": a[i - 1], "alignment": "substitution",
                        "start_s": h["start_s"], "end_s": h["end_s"],
                        "span_available": h["start_s"] is not None, "ignored_for_pronunciation": False})
            i -= 1; j -= 1
        elif j > 0 and dp[i][j] == dp[i][j - 1] + 1:
            ops.append({"word": b[j - 1], "source_word": None, "alignment": "insertion",
                        "start_s": None, "end_s": None,
                        "span_available": False, "ignored_for_pronunciation": False})
            j -= 1
        else:
            # deletion: từ whisper bị user xóa -> không chấm phát âm từ này
            i -= 1
    ops.reverse()
    return ops


def apply_forced_spans(aligned: list[dict], forced_words: list[dict]) -> list[dict]:
    """Ghi đè start/end bằng forced aligner (nguồn sự thật). forced_words: [{word,start_s,end_s}]."""
    fw = {w["word"].upper(): w for w in forced_words}
    out = []
    for w in aligned:
        key = w["word"].upper()
        if key in fw:
            w = {**w, "start_s": fw[key]["start_s"], "end_s": fw[key]["end_s"], "span_available": True}
        elif w["alignment"] == "insertion":
            # forced aligner trên user_corrected LUÔN gán được span -> không còn insertion mù
            w = {**w, "span_available": True}
        out.append(w)
    return out


# ═══════════════════════════════════════════════════════════════════
# Part 4 — CTC acoustic: wav2vec2 forced align char-level (word spans thật).
# Dùng cho stress/fluency + fallback acoustic khi phoneme model chưa tải.
# KHÔNG gọi output này là GOP. Full-audio 1 pass, không chunk.
# ═══════════════════════════════════════════════════════════════════

FRAME_STRIDE_S = 0.02  # wav2vec2 downsample 320x @16kHz ~= 20ms/frame
BLANK_RATIO_MISALIGNED = 0.70  # blank >70% word span -> misalignment, không phải lỗi phát âm

_acoustic_lock = threading.Lock()
_ctc_processor = None
_acoustic_model = None
_torch = None


def _load_torch():
    global _torch
    if _torch is None:
        import torch  # noqa: WPS433

        _torch = torch
    return _torch


def _acoustic_model_id() -> str:
    try:
        return settings.wav2vec_model_id or "facebook/wav2vec2-base-960h"
    except Exception:
        return "facebook/wav2vec2-base-960h"


def get_acoustic_model():
    """Lazy-load wav2vec2 processor + model (thread-safe, load 1 lần)."""
    global _ctc_processor, _acoustic_model
    if _acoustic_model is not None:
        return _ctc_processor, _acoustic_model
    with _acoustic_lock:
        if _acoustic_model is not None:
            return _ctc_processor, _acoustic_model
        torch = _load_torch()
        from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

        mid = _acoustic_model_id()
        _ctc_processor = Wav2Vec2Processor.from_pretrained(mid)
        _acoustic_model = Wav2Vec2ForCTC.from_pretrained(mid)
        _acoustic_model.eval()
        if torch.cuda.is_available():
            _acoustic_model.to("cuda")
    return _ctc_processor, _acoustic_model


def normalize_reference(text: str, vocab: set[str]) -> str:
    t = (text or "").upper().strip()
    t = re.sub(r"\s+", " ", t)
    t = t.replace("-", " ")
    kept = "".join(ch for ch in t if ch in vocab or ch == " ")
    kept = re.sub(r"\s+", " ", kept).strip()
    return kept


def ctc_forced_align(log_probs, target_ids: list[int], blank_id: int):
    """Viterbi forced alignment CTC (vector hoá theo S).
    Extended: [b, t1, b, t2, b, ..., tL, b]. Ưu tiên stay > +1 > +2 khi hoà."""
    torch = _load_torch()
    T = log_probs.shape[0]
    L = len(target_ids)
    if L == 0 or T == 0:
        return [0] * T, float("-inf")
    ext = [blank_id]
    for tid in target_ids:
        ext.append(int(tid))
        ext.append(blank_id)
    S = len(ext)
    NEG = -1e9
    ext_t = torch.tensor(ext, dtype=torch.long)
    lp = log_probs[:, ext_t]  # [T, S]
    trellis = torch.full((T, S), NEG)
    choice = torch.zeros((T, S), dtype=torch.long)  # 0=stay, 1=+1, 2=+2
    trellis[0, 0] = lp[0, 0]
    if S > 1:
        trellis[0, 1] = lp[0, 1]
    skip_ok = torch.zeros(S, dtype=torch.bool)
    for s in range(2, S):
        if ext[s] != blank_id and ext[s] != ext[s - 2]:
            skip_ok[s] = True
    neg_col = torch.full((S,), NEG)
    for t in range(1, T):
        prev = trellis[t - 1]
        stay = prev
        plus1 = torch.cat([neg_col[:1], prev[:-1]])
        if skip_ok.any():
            plus2 = torch.cat([neg_col[:2], prev[:-2]])
            plus2 = torch.where(skip_ok, plus2, neg_col)
            cand = torch.stack([stay, plus1, plus2], dim=0)
        else:
            cand = torch.stack([stay, plus1], dim=0)
        best, idx = cand.max(dim=0)
        trellis[t] = best + lp[t]
        choice[t] = idx
    last = S - 1
    if S > 1 and trellis[T - 1, S - 2] > trellis[T - 1, S - 1]:
        last = S - 2
    align = [0] * T
    s = last
    for t in range(T - 1, -1, -1):
        align[t] = s
        if t > 0:
            c = int(choice[t, s])
            s = s if c == 0 else (s - 1 if c == 1 else s - 2)
    return align, float(trellis[T - 1, last])


def score_utterance(waveform_16k, sample_rate: int, reference_text: str) -> dict[str, Any]:
    """Char-level acoustic likelihood + word spans + alignment_status.
    KHÔNG cắt audio (chỉ chặn >10 phút). Từ no_evidence/misaligned loại khỏi overall."""
    torch = _load_torch()
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
        logits = model(input_values).logits[0].cpu()  # [T, V]
    log_probs = torch.log_softmax(logits, dim=-1)
    T, V = log_probs.shape

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

    L = len(target_ids)
    char_lp: list[float] = []
    char_span: list[tuple[int, int]] = []
    char_ok: list[bool] = []
    for i, tid in enumerate(target_ids):
        s = 2 * i + 1
        frames = [t for t in range(T) if align[t] == s]
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
    chars = list(ref_ctc)
    w, wi = "", []
    per_word_spans: list[list[int]] = []
    word_list: list[str] = []
    for ci, ch in enumerate(chars):
        if ch == "|":
            if w:
                word_list.append(w)
                per_word_spans.append(wi)
                w, wi = "", []
        else:
            w += ch
            wi.append(ci)
    if w:
        word_list.append(w)
        per_word_spans.append(wi)

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
        input_lengths = torch.tensor([T])
        target_lengths = torch.tensor([L])
        loss = float(ctc(log_probs.unsqueeze(1), torch.tensor([target_ids]), input_lengths, target_lengths))
    except Exception:
        loss = float("nan")

    try:
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
        greedy = "".join(collapsed).replace("|", " ").strip()
    except Exception:
        greedy = ""

    level = "Xuat sac" if overall >= 85 else ("Tot" if overall >= 70 else ("Trung binh" if overall >= 50 else "Can luyen them"))

    return {
        "transcript_norm": ref_norm,
        "greedy_decoded": greedy,
        "overall_0_100": round(overall, 1),
        "overall_0_10": round(overall / 10.0, 2),
        "level": level,
        "avg_log_prob": round(float(avg_lp_all), 4),
        "ctc_loss": loss,
        "num_frames": T,
        "duration_s": round(duration_s, 2),
        "model": _acoustic_model_id(),
        "n_scored": len(scored),
        "n_no_evidence": len(no_ev),
        "words": words_out,
    }


# ═══════════════════════════════════════════════════════════════════
# Part 5 — Metrics: fluency + completeness + overall (deterministic)
# ═══════════════════════════════════════════════════════════════════

def score_fluency(duration_s: float, words_count: int, pauses: list[tuple[float, float]],
                  whisper_text: str = "") -> dict:
    wpm = (words_count / max(0.1, duration_s)) * 60.0 if duration_s > 0 else 0.0
    pause_dur = sum(e - s for s, e in pauses)
    pause_ratio = pause_dur / max(0.1, duration_s)
    long_pauses = sum(1 for s, e in pauses if e - s >= 0.4)
    low = (whisper_text or "").lower()
    hes = sum(low.count(x) for x in [" uh ", " um ", " er ", " ah "])
    # repetition: từ lặp liền nhau
    toks = _tok_words(whisper_text)
    rep = sum(1 for i in range(1, len(toks)) if toks[i] == toks[i-1])
    phones = sum(len(w) for w in toks)
    art = phones / max(0.1, duration_s - pause_dur)
    # rubric 0-100
    s = 100.0
    if 130 <= wpm <= 170: s -= 0
    elif 90 <= wpm < 130 or 170 < wpm <= 210: s -= 10
    else: s -= 25
    if pause_ratio > 0.35: s -= 20
    elif pause_ratio > 0.25: s -= 10
    s -= min(20, long_pauses * 5 + hes * 4 + rep * 5)
    return {"wpm": round(wpm,1), "articulation_rate": round(art,2), "pause_ratio": round(pause_ratio,3),
            "long_pause_count": long_pauses, "hesitation_count": hes, "repetition_count": rep,
            "score": round(max(0.0, min(100.0, s)),1)}


def score_completeness(original: str | None, corrected: str, mode: str) -> dict:
    if mode != "read_aloud" or not original:
        return {"mode": mode, "missing_words": [], "extra_words": [], "wer_vs_original": None, "score": 100.0}
    a, b = _tok_words(original), _tok_words(corrected)
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
    """MVP v2: 0.5*Sounds + 0.25*Stress + 0.15*Fluency + 0.10*Completeness. Intonation v1.1."""
    return round(0.5*sounds + 0.25*stress + 0.15*fluency + 0.10*completeness, 1)


# ═══════════════════════════════════════════════════════════════════
# Part 6 — Sounds: phoneme-level từ char evidence + CMU.
# Case bắt buộc: đọc /sɪŋk/ nhưng corrected là think -> phải ra /θ/→/s/.
# Khi có xlsr-espeak: thay observe_phones_fallback bằng decode IPA trực tiếp
# từ audio (API giữ nguyên, chỉ đổi hàm observe).
# ═══════════════════════════════════════════════════════════════════

def _needleman(a: list[str], b: list[str]) -> list[tuple[str, str, str]]:
    """Align canonical (a) vs observed (b) -> [(exp, obs, type)]. Dùng chung
    cho char-phoneme fallback (Part 6) và GOP thật (Part 8)."""
    n, m = len(a), len(b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1): dp[i][0] = i
    for j in range(m + 1): dp[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            c = 0 if a[i-1] == b[j-1] else 1
            dp[i][j] = min(dp[i-1][j]+1, dp[i][j-1]+1, dp[i-1][j-1]+c)
    i, j, out = n, m, []
    while i > 0 or j > 0:
        if i > 0 and j > 0 and a[i-1] == b[j-1]:
            out.append((a[i-1], b[j-1], "match")); i -= 1; j -= 1
        elif i > 0 and j > 0 and dp[i][j] == dp[i-1][j-1]+1:
            out.append((a[i-1], b[j-1], "substitution")); i -= 1; j -= 1
        elif j > 0 and dp[i][j] == dp[i][j-1]+1:
            out.append(("-", b[j-1], "insertion")); j -= 1
        else:
            out.append((a[i-1], "-", "deletion")); i -= 1
    return out[::-1]


def observe_phones_fallback(greedy_text: str, canonical_arpa: list[str]) -> list[str]:
    """Tạm: suy observed từ greedy char decode. VD greedy SINK vs canonical THINK -> S thay TH."""
    g = (greedy_text or "").upper()
    # map chữ cái đầu từ greedy sang ARPAbet tương ứng để so với canonical
    m = {"S": "S", "F": "F", "TH": "TH", "T": "T", "D": "D", "R": "R", "L": "L", "V": "V", "W": "W"}
    if not g:
        return []
    first = g.split()[0] if g.split() else g
    if first.startswith("S"):
        return ["S"]
    if first.startswith("F"):
        return ["F"]
    if first.startswith("TH"):
        return ["TH"]
    return [canonical_arpa[0] if canonical_arpa else "AH0"]


def score_sounds(words_forced: list[dict], greedy_text: str = "", accent: str = "en-US") -> dict[str, Any]:
    """words_forced: [{word, avg_log_prob/score_0_100, start_s, end_s}] từ char forced aligner.
    Trả sounds 0-100 + phonemes + top_errors + vowel/consonant split."""
    phonemes: list[dict] = []
    err_counter: dict[str, dict] = {}
    wdetails: list[dict] = []
    v_scores, c_scores = [], []
    VOWELS = {"AA","AE","AH","AO","AW","AY","EH","ER","EY","IH","IY","OW","OY","UH","UW"}
    for w in words_forced:
        word = w.get("word", "")
        status_in = w.get("status", "scored")
        if status_in != "scored":
            # Không evidence (misaligned/no_evidence): loại khỏi mẫu số, UI hiện "Không nghe rõ"
            wdetails.append({"word": word, "score": 0.0, "status": "no_evidence",
                             "start_s": w.get("start_s"), "end_s": w.get("end_s"),
                             "acoustic_confidence": w.get("avg_log_prob"),
                             "expected_ipa": get_pronunciation(word, accent)["ipa"]})
            continue
        pron = get_pronunciation(word, accent)
        arpa = pron["arpa"]
        char_score = float(w.get("score_0_100", 0.0))
        # GOP phoneme tạm = char acoustic_confidence (MVP), ghi rõ warnings ở pipeline
        obs = observe_phones_fallback(greedy_text if word.upper() in (greedy_text or "").upper() else word, arpa)
        # align full: nếu greedy không có info thì coi như match để không false-positive
        if word.upper() in (greedy_text or "").upper() or not greedy_text:
            pairs = [(p, p, "match") for p in arpa]
        else:
            # từ bị đọc khác hẳn -> align canonical vs observed suy từ greedy
            obs_full = obs * max(1, len(arpa) // max(1, len(obs)))
            pairs = _needleman(arpa, (obs_full + arpa)[ :len(arpa)])
        for exp, ob, typ in pairs:
            base = exp.rstrip("012")
            is_v = base in VOWELS
            # phoneme sai -> phạt 25đ so với word score (MVP heuristic, thay bằng GOP thật ở v1.1)
            pscore = char_score if typ == "match" else max(0.0, char_score - 25.0)
            gop = math.log(max(1e-6, pscore / 100.0))
            phonemes.append({"word": word, "expected": "/" + arpa_to_ipa(exp) + "/",
                             "observed": "/" + arpa_to_ipa(ob) + "/" if ob != "-" else None,
                             "type": typ, "gop": round(gop, 3), "score": round(pscore, 1)})
            (v_scores if is_v else c_scores).append(pscore)
            if typ == "substitution":
                pat = f"/{arpa_to_ipa(exp)}/ → /{arpa_to_ipa(ob)}/"
                e = err_counter.setdefault(pat, {"pattern": pat, "count": 0, "examples": []})
                e["count"] += 1
                if word not in e["examples"]:
                    e["examples"].append(word)
        status = "ok" if char_score >= 70 else "pronunciation_error"
        wdetails.append({"word": word, "score": round(char_score, 1), "status": status,
                         "start_s": w.get("start_s"), "end_s": w.get("end_s"),
                         "acoustic_confidence": w.get("avg_log_prob"), "expected_ipa": pron["ipa"]})
    sounds = round(sum(d["score"] for d in wdetails if d["status"] != "no_evidence") / max(1, sum(1 for d in wdetails if d["status"] != "no_evidence")), 1) if wdetails else 0.0
    top_errors = sorted(err_counter.values(), key=lambda x: -x["count"])[:5]
    return {"sounds": sounds,
            "vowel_score": round(sum(v_scores)/max(1,len(v_scores)),1) if v_scores else sounds,
            "consonant_score": round(sum(c_scores)/max(1,len(c_scores)),1) if c_scores else sounds,
            "word_details": wdetails, "phonemes": phonemes, "top_errors": top_errors}


# ═══════════════════════════════════════════════════════════════════
# Part 7 — Stress: syllable boundary THẬT từ phoneme timestamps
# (forced aligner), không chia đều. MVP: word span -> N syllable spans theo
# tỉ lệ duration phoneme; v1.1 MFA cho boundary chuẩn 100%.
# ═══════════════════════════════════════════════════════════════════

def score_stress(words_forced: list[dict], wav: np.ndarray, sr: int = 16000, accent: str = "en-US") -> dict:
    details: list[dict] = []
    correct, total = 0, 0
    for w in words_forced:
        if w.get("status", "scored") == "no_evidence":
            details.append({"word": w.get("word",""), "expected_stress": None,
                            "detected_stress": None, "correct": None, "reason": "no_evidence"})
            continue
        pron = get_pronunciation(w.get("word",""), accent)
        n = pron["num_syllables"]
        if n <= 1 or w.get("start_s") is None:
            details.append({"word": w.get("word",""), "expected_stress": pron["stress_index"],
                            "detected_stress": pron["stress_index"], "correct": True if n<=1 else None,
                            "reason": "mono-syllable" if n<=1 else "missing_span"})
            continue
        s, e = float(w["start_s"]), float(w["end_s"])
        s_i, e_i = max(0, int(s*sr)), min(len(wav), int(e*sr))
        seg = wav[s_i:e_i]
        if len(seg) < 160:
            details.append({"word": w.get("word",""), "expected_stress": pron["stress_index"],
                            "detected_stress": None, "correct": False, "reason": "too_short"})
            total += 1
            continue
        # chia theo tỉ lệ phoneme trong syllable (MVP: đều theo số phone mỗi syllable — tốt hơn chia đều time)
        syls = pron["syllables"]
        lens = [max(1, len(x)) for x in syls]
        tot = sum(lens)
        bounds = []
        cur = 0
        for L in lens:
            nxt = cur + int(len(seg) * L / tot)
            bounds.append((cur, nxt)); cur = nxt
        bounds[-1] = (bounds[-1][0], len(seg))
        feats = []
        try:
            import librosa
            f0, _, _ = librosa.pyin(seg, fmin=librosa.note_to_hz("C2"), fmax=librosa.note_to_hz("C7"), sr=sr)
            import numpy as _np
            f0m = []
            hop = 512
            for a, b in bounds:
                fa, fb = a // hop, max(a // hop + 1, b // hop)
                vals = f0[fa:fb] if f0 is not None else []
                vals = [float(x) for x in vals if x == x]
                f0m.append(sum(vals)/len(vals) if vals else 0.0)
        except Exception:
            f0m = [0.0]*len(bounds)
        proms = []
        for (a, b), f in zip(bounds, f0m):
            part = seg[a:b]
            dur = (b-a)/sr
            energy = float(np.sqrt(np.mean(part**2)+1e-12))
            proms.append((dur, energy, f))
        # z-norm trong word
        def znorm(xs):
            m = sum(xs)/len(xs); v = sum((x-m)**2 for x in xs)/len(xs); s = math.sqrt(v+1e-9)
            return [(x-m)/(s+1e-9) for x in xs]
        dz = znorm([p[0] for p in proms]); ez = znorm([p[1] for p in proms]); fz = znorm([p[2] for p in proms])
        scores = [0.4*d+0.4*e+0.2*f for d,e,f in zip(dz,ez,fz)]
        det = max(range(len(scores)), key=lambda i: scores[i])
        exp = pron["stress_index"]
        ok = (det == exp)
        details.append({"word": w.get("word",""), "expected_stress": exp, "detected_stress": det,
                        "correct": ok, "reason": ""})
        total += 1; correct += 1 if ok else 0
    score = round(100.0*correct/max(1,total),1) if total else 85.0
    return {"stress": score, "correct": correct, "total": total, "details": details}


# ═══════════════════════════════════════════════════════════════════
# Part 8 — Phoneme GOP thật (theo tư vấn chuyên gia).
# Model: facebook/wav2vec2-xlsr-53-espeak-cv-ft (Wav2Vec2ForCTC trên phone espeak).
# - KHÔNG dùng tokenizer của transformers (nó đòi binary espeak) — đọc thẳng
#   vocab.json trong HF cache, tokenize thủ công.
# - user_corrected -> CMUdict (full) -> ARPAbet -> espeak phones.
# - 1 pass forced alignment (Viterbi, tái dùng ctc_forced_align) trên full audio.
# - GOP(phone) = mean log-posterior trên các frame align vào phone đó (Witt & Young).
# - Observed phones = greedy decode phone model (free phone recognition, không LM)
#   -> align Needleman canonical vs observed -> substitution thật (/th/->/s/).
# - Char-level (Part 4+6) KHÔNG được gọi là GOP nữa — chỉ fallback khi
#   model phoneme chưa tải được (ghi rõ trong warnings).
# ═══════════════════════════════════════════════════════════════════

def _phone_model_id() -> str:
    try:
        return settings.phoneme_model_id or "facebook/wav2vec2-xlsr-53-espeak-cv-ft"
    except Exception:
        return os.getenv("PHONEME_MODEL_ID", "facebook/wav2vec2-xlsr-53-espeak-cv-ft")


_PHONE_MODEL_ID = _phone_model_id()

# ARPAbet (đã strip số stress) -> espeak phone token. Mọi token đều có trong vocab.
ARPA_TO_ESPEAK: dict[str, tuple[str, ...]] = {
    "AA": ("ɑ",), "AE": ("æ",), "AH": ("ʌ",), "AO": ("ɔ",),
    "AW": ("aʊ",), "AY": ("aɪ",),
    "EH": ("ɛ",), "ER": ("ɜ", "ɹ"), "EY": ("eɪ",),
    "IH": ("ɪ",), "IY": ("i",),
    "OW": ("oʊ",), "OY": ("ɔɪ",), "UH": ("ʊ",), "UW": ("u",),
    "P": ("p",), "B": ("b",), "T": ("t",), "D": ("d",),
    "K": ("k",), "G": ("ɡ",),
    "F": ("f",), "V": ("v",), "TH": ("θ",), "DH": ("ð",),
    "S": ("s",), "Z": ("z",), "SH": ("ʃ",), "ZH": ("ʒ",),
    "HH": ("h",), "M": ("m",), "N": ("n",), "NG": ("ŋ",),
    "L": ("l",), "R": ("ɹ",), "W": ("w",), "Y": ("j",),
    "CH": ("tʃ",), "JH": ("dʒ",),
}

_phone_lock = threading.Lock()
_phone_fe = None
_phone_model = None
_phone_vocab: dict[str, int] | None = None


def _load_vocab() -> dict[str, int]:
    global _phone_vocab
    if _phone_vocab is not None:
        return _phone_vocab
    pats = [
        str(Path.home() / ".cache" / "huggingface" / "hub" /
            ("models--" + _PHONE_MODEL_ID.replace("/", "--")) / "snapshots" / "*" / "vocab.json"),
    ]
    found = []
    for p in pats:
        found.extend(glob.glob(p))
    if not found:
        # ép download vocab (nhẹ, vài KB)
        from huggingface_hub import hf_hub_download
        fp = hf_hub_download(_PHONE_MODEL_ID, "vocab.json")
        found = [fp]
    with open(found[0], encoding="utf-8") as f:
        _phone_vocab = json.load(f)
    return _phone_vocab


def get_phone_model():
    """Lazy-load feature extractor + phone CTC model (1 lần). Nặng ~1.2GB lần đầu."""
    global _phone_fe, _phone_model
    if _phone_model is not None:
        return _phone_fe, _phone_model
    with _phone_lock:
        if _phone_model is not None:
            return _phone_fe, _phone_model
        torch = _load_torch()
        from transformers import AutoFeatureExtractor, Wav2Vec2ForCTC
        _phone_fe = AutoFeatureExtractor.from_pretrained(_PHONE_MODEL_ID)
        _phone_model = Wav2Vec2ForCTC.from_pretrained(_PHONE_MODEL_ID)
        _phone_model.eval()
        if torch.cuda.is_available():
            _phone_model.to("cuda")
        _load_vocab()
    return _phone_fe, _phone_model


def arpa_to_espeak(arpa: list[str]) -> tuple[list[str], list[int]]:
    """ARPAbet (kèm số stress) -> (espeak tokens, phone->arpa index). Bỏ token lạ."""
    vocab = _load_vocab()
    toks: list[str] = []
    back: list[int] = []
    for i, ph in enumerate(arpa):
        base = ph.rstrip("012")
        for t in ARPA_TO_ESPEAK.get(base, ()):
            if t in vocab:
                toks.append(t)
                back.append(i)
    return toks, back


def score_phones(wav, sr: int, text: str, accent: str = "en-US") -> dict[str, Any]:
    """Full pipeline phoneme GOP. Trả word_details/phonemes/top_errors/sounds cùng schema score_sounds."""
    torch = _load_torch()
    fe, model = get_phone_model()
    vocab = _load_vocab()
    device = next(model.parameters()).device
    blank_id = 0  # <pad>

    words = [w for w in re.findall(r"[A-Za-z']+", text)]
    if not words:
        return {"error": "Text rỗng."}

    # canonical phone sequence + word ranges
    seq: list[str] = []
    wranges: list[tuple[int, int, str, list[str]]] = []  # (p_start, p_end, word, arpa)
    skipped_words: list[str] = []
    for w in words:
        pron = get_pronunciation(w, accent)
        toks, _ = arpa_to_espeak(pron["arpa"])
        if not toks:
            skipped_words.append(w)
            continue
        s0 = len(seq)
        seq.extend(toks)
        wranges.append((s0, len(seq), w, pron["arpa"]))
    if not seq:
        return {"error": "Không map được phoneme nào."}
    target_ids = [vocab[t] for t in seq]

    warr = np.asarray(wav, dtype=np.float32).reshape(-1)
    inputs = fe(warr, sampling_rate=16000, return_tensors="pt", padding=True)
    with torch.no_grad():
        logits = model(inputs.input_values.to(device)).logits[0].cpu()
    log_probs = torch.log_softmax(logits, dim=-1)
    T = log_probs.shape[0]
    pred_ids: list[int] = torch.argmax(logits, dim=-1).tolist()

    align, _ = ctc_forced_align(log_probs, target_ids, blank_id)

    # per-phone GOP
    L = len(target_ids)
    phone_lp: list[float] = []
    phone_span: list[tuple[int, int]] = []
    phone_ok: list[bool] = []
    for i, tid in enumerate(target_ids):
        s = 2 * i + 1
        frames = [t for t in range(T) if align[t] == s]
        if frames:
            vals = [float(log_probs[t, tid]) for t in frames]
            phone_lp.append(sum(vals) / len(vals))
            phone_span.append((frames[0], frames[-1]))
            phone_ok.append(True)
        else:
            phone_lp.append(float("-inf"))
            phone_span.append((-1, -1))
            phone_ok.append(False)

    # observed phones: free recognition (greedy collapse, không LM)
    id2tok = {i: t for t, i in vocab.items()}
    collapsed, prev = [], None
    for pid in pred_ids:
        if pid != prev:
            if pid != blank_id:
                collapsed.append(id2tok.get(pid, ""))
        prev = pid
    observed = [t for t in collapsed if t]

    phonemes: list[dict] = []
    wdetails: list[dict] = []
    err_counter: dict[str, dict] = {}
    for (p0, p1, w, arpa) in wranges:
        canon = seq[p0:p1]
        # observed evidence: align needleman toàn câu quá nặng -> so trong vùng từ:
        # xấp xỉ bằng greedy phones gần span thời gian của từ (MVP trung thực)
        f0 = phone_span[p0][0] if phone_ok[p0] else -1
        f1 = phone_span[p1 - 1][1] if phone_ok[p1 - 1] else -1
        if f0 >= 0:
            span_pred = [id2tok.get(p, "") for p in pred_ids[f0:f1 + 1] if p != blank_id]
            # collapse
            obs_w, pv = [], None
            for t in span_pred:
                if t != pv:
                    obs_w.append(t)
                pv = t
        else:
            obs_w = []
        pairs = _needleman(canon, obs_w)
        # blank density trên word span
        if f0 >= 0:
            tot = f1 - f0 + 1
            n_blank = sum(1 for t in range(f0, f1 + 1) if pred_ids[t] == blank_id)
            blank_ratio = n_blank / max(1, tot)
        else:
            blank_ratio = 1.0
        has_frames = any(phone_ok[p0:p1])
        if not has_frames:
            status = "no_evidence"
        elif blank_ratio > BLANK_RATIO_MISALIGNED:
            status = "misaligned"
        else:
            status = "scored"
        pscores: list[float] = []
        for (exp, ob, typ), pi in zip(pairs, range(p0, p1)):
            # GOP: mean log-posterior; no_evidence -> -inf
            g = phone_lp[pi] if phone_ok[pi] else float("-inf")
            s100 = round(max(0.0, min(100.0, math.exp(max(g, -10.0)) * 100.0)), 1) if math.isfinite(g) else 0.0
            if status == "scored":
                pscores.append(s100)
            disp_ob = ob if ob != "-" else None
            phonemes.append({"word": w, "expected": exp, "observed": disp_ob,
                             "type": typ, "gop": round(g, 3) if math.isfinite(g) else None,
                             "score": s100 if status == "scored" else 0.0})
            if typ == "substitution" and status == "scored":
                pat = f"/{exp}/ -> /{ob}/"
                e = err_counter.setdefault(pat, {"pattern": pat, "count": 0, "examples": []})
                e["count"] += 1
                if w not in e["examples"]:
                    e["examples"].append(w)
        wscore = round(sum(pscores) / len(pscores), 1) if pscores else 0.0
        pron = get_pronunciation(w, accent)
        wdetails.append({"word": w, "score": wscore,
                         "status": "ok" if status == "scored" else "no_evidence",
                         "start_s": round(f0 * FRAME_STRIDE_S, 2) if f0 >= 0 else 0.0,
                         "end_s": round((f1 + 1) * FRAME_STRIDE_S, 2) if f1 >= 0 else 0.0,
                         "acoustic_confidence": None, "expected_ipa": pron["ipa"],
                         "blank_ratio": round(blank_ratio, 3)})
    for w in skipped_words:
        wdetails.append({"word": w, "score": 0.0, "status": "no_evidence",
                         "start_s": 0.0, "end_s": 0.0, "acoustic_confidence": None,
                         "expected_ipa": "", "blank_ratio": 1.0})
    ok_w = [d for d in wdetails if d["status"] == "ok"]
    sounds = round(sum(d["score"] for d in ok_w) / len(ok_w), 1) if ok_w else 0.0
    # vowel/consonant split theo ARPAbet gốc
    return {"sounds": sounds, "word_details": wdetails, "phonemes": phonemes,
            "top_errors": sorted(err_counter.values(), key=lambda x: -x["count"])[:5],
            "model": _PHONE_MODEL_ID, "n_scored": len(ok_w),
            "n_no_evidence": len(wdetails) - len(ok_w)}


# ═══════════════════════════════════════════════════════════════════
# Part 9 — Pipeline: audio + whisper_raw + user_corrected + accent
# -> ScoringReport. Trái tim scorer. Deterministic.
# LLM feedback KHÔNG được gọi ở đây.
# ═══════════════════════════════════════════════════════════════════

def score_attempt_v2(wav: np.ndarray, sr: int, whisper_raw: str, user_corrected: str,
                     mode: str = "free_speaking", original_text: str | None = None,
                     accent: str = "en-US", whisper_segments: list[dict] | None = None,
                     char_words: list[dict] | None = None, greedy_text: str = "") -> dict:
    """char_words: output words từ score_utterance (forced aligner char-level,
    nguồn span thật). Caller truyền vào để tái dùng model đã load."""
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
            snd = {"sounds": ph["sounds"], "word_details": ph["word_details"],
                   "phonemes": ph["phonemes"], "top_errors": ph["top_errors"]}
            gop_model = ph.get("model")
    except Exception as e:
        warnings.append(f"phoneme GOP failed ({str(e)[:120]}), fallback char-level acoustic")
    if snd is None:
        # Fallback char-level: KHÔNG gọi là GOP, chỉ là acoustic likelihood.
        snd = score_sounds(char_words or [], greedy_text=greedy_text or whisper_raw, accent=accent)
        warnings.append("diem Sounds hien tai la char-level acoustic likelihood, KHONG phai GOP chuan")
    st = score_stress(snd.get("word_details") or char_words or [], wav, sr, accent)
    segs, pauses = vad_segments(wav, sr)
    fl = score_fluency(len(wav)/sr, len([w for w in aligned if w["alignment"] != "deletion"]),
                       pauses, whisper_raw)
    cp = score_completeness(original_text, user_corrected, mode)
    f0 = extract_f0(wav, sr)
    monotone = f0["std_f0"] < 15 and f0["voiced_ratio"] > 0.1
    overall = calculate_overall(snd["sounds"], st["stress"], fl["score"], cp["score"])
    _details = snd["word_details"]
    _no_ev = sum(1 for d in _details if d.get("status") == "no_evidence")
    return {
        "scores": {"sounds": snd["sounds"], "stress": st["stress"], "fluency": fl["score"],
                   "completeness": cp["score"], "intonation": None, "overall": overall},
        "texts": {"original": original_text, "whisper_raw": whisper_raw, "user_corrected": user_corrected},
        "reference": {"accent": accent, "voice_id": "af_heart"},
        "word_details": snd["word_details"], "phonemes": snd["phonemes"],
        "stress_detail": st["details"],
        "intonation": {"median_f0": f0["median_f0"], "std_f0": f0["std_f0"], "range_f0": f0["range_f0"],
                       "final_slope": f0["final_slope"], "monotone": monotone,
                       "note": "MVP: monotone detection only, DTW vs Kokoro deferred to v1.1"},
        "fluency": {**fl}, "completeness": cp, "top_errors": snd["top_errors"],
        "alignment": aligned, "speech_segments": segs,
        "scorer_version": "scorer-v2-mvp",
        "gop_model": gop_model,
        "n_scored": len(_details) - _no_ev,
        "n_no_evidence": _no_ev,
        "warnings": warnings,
        "compute_s": round(time.time() - t0, 2),
    }


# ═══════════════════════════════════════════════════════════════════
# Part 10 — Hook: entry-point cho router + xin nhận xét AI
# ═══════════════════════════════════════════════════════════════════

def heuristic_score(
    confidence: float = 1.0,
    avg_logprob: float = 0.0,
    duration: float = 0.0,
    words_count: int = 0,
) -> Dict[str, Any]:
    """Chấm tạm 0-100 từ tín hiệu STT sẵn có."""
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


def _report_to_hook(report: Dict[str, Any], method: str) -> Dict[str, Any]:
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
    """Chấm bằng ruột scorer trong file này: full-audio 1 pass,
    phoneme GOP + 4 tiêu chí. Raise khi model/audio lỗi.

    Xếp hàng qua _scoring_gate: lượt chấm sau đợi lượt trước xong (tuần tự
    theo SCORING_MAX_PARALLEL) thay vì forward song song gây OOM."""
    raw = Path(audio_path).read_bytes()
    if len(raw) > 100 * 1024 * 1024:
        raise ValueError("Audio > 100MB.")
    queued_at = time.monotonic()
    with _scoring_gate:
        waited = time.monotonic() - queued_at
        if waited > 1.0:
            log.info("scoring queued %.1fs (nhieu nguoi cham cung luc)", waited)
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
    return _report_to_hook(report, "local-v2")


def score_via_pronun_service(
    audio_path: Path | str,
    reference_text: str,
    language: str = "en",
) -> Dict[str, Any]:
    """Gọi Pronun scorer qua HTTP: POST {PRONUN_BASE_URL}/api/speaking/score.
    Raise khi chưa cấu hình hoặc scorer lỗi."""
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
    return _report_to_hook(report, "pronun-v2")


def score_with_wav2vec2(
    audio_path: Path | str,
    reference_text: str,
    language: str = "en",
) -> Dict[str, Any]:
    """Local trước, remote sau. Raise để caller fallback heuristic."""
    try:
        return score_local(audio_path, reference_text, language)
    except Exception as error:
        log.warning("local scoring failed (%s), thử pronun service", error)
    return score_via_pronun_service(audio_path, reference_text, language)


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
    chuyên biệt thay vì prompt mặc định. Raise khi LLM lỗi."""
    import asyncio

    try:
        out = asyncio.run(generate_feedback(
            scoring_report, model, temperature, max_tokens, system_prompt, user_label,
        ))
    except Exception as error:
        raise RuntimeError(f"feedback LLM lỗi: {error}")
    if "error" in out:
        raise RuntimeError(out["error"])
    return out


# ═══════════════════════════════════════════════════════════════════
# Part 11 — Nhận xét AI: gọi LLM local (get_llm), prompt ở prompts/feedback.md
# (1 file, 2 mục ## utterance / ## session). Trả dict JSON nếu parse được,
# không thì {"feedback_raw": ...} — frontend render được cả hai.
# ═══════════════════════════════════════════════════════════════════

def _load_feedback_prompts() -> Dict[str, str]:
    """Cắt feedback.md theo dòng ## utterance / ## session."""
    from app.ai.prompt import load_prompt

    out = {"utterance": "", "session": ""}
    text = load_prompt("feedback")
    if not text:
        log.warning("prompt feedback.md thieu/trong — feedback se chay prompt rong")
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
        log.warning("feedback.md thieu muc ## utterance/## session")
    return out


_PROMPTS = _load_feedback_prompts()
SYSTEM_PROMPT = _PROMPTS["utterance"]
SESSION_FEEDBACK_PROMPT = _PROMPTS["session"]


def _extract_json(content: str) -> Dict[str, Any] | None:
    """LLM local tra JSON (co the kem text). Boc tach object JSON dau tien."""
    text = (content or "").strip()
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
                            temperature: float = 0.6, max_tokens: int = 1200,
                            system_prompt: str = "", user_label: str = "scoring_report") -> dict:
    from app.ai import get_llm

    user_msg = f"{user_label}:\n" + json.dumps(scoring_report, ensure_ascii=False)[:12000]
    try:
        llm = get_llm(model=model, temperature=temperature, max_tokens=max_tokens)
        msg = await llm.ainvoke([
            {"role": "system", "content": system_prompt or SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ])
    except Exception as error:
        return {"error": f"LLM local lỗi ({settings.llm_base_url}): {error}"}
    content = getattr(msg, "content", "") or ""
    parsed = _extract_json(content if isinstance(content, str) else str(content))
    if parsed:
        parsed.setdefault("model", (model or "").strip() or settings.llm_model)
        return parsed
    return {"feedback_raw": content, "model": (model or "").strip() or settings.llm_model, "usage": {}}


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
    """Entry-point duy nhất caller cần gọi.

    Thử local scorer -> pronun service (nếu có audio + text), fallback heuristic.
    Không bao giờ raise — luôn trả dict score.
    """
    words = words or []
    if prefer_wav2vec and audio_path and reference_text.strip():
        try:
            path = Path(audio_path)
            if path.exists():
                return score_with_wav2vec2(path, reference_text, language)
        except NotImplementedError:
            pass
        except Exception as error:
            log.warning("wav2vec2 scoring failed, fallback heuristic | err=%s", error)
    return heuristic_score(
        confidence=confidence,
        avg_logprob=avg_logprob,
        duration=duration,
        words_count=len(words),
    )
