from __future__ import annotations

import io
from typing import Any, Dict

import numpy as np

from app.log import get_logger

log = get_logger("app.ai.pronunciation.audio")


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


QUIET_PEAK_THRESHOLD = 0.08


QUIET_RMS_THRESHOLD = 0.015


def check_audio_quality(wav: np.ndarray, sr: int = 16000) -> Dict[str, Any]:
    flat = np.asarray(wav, dtype=np.float64).reshape(-1)
    peak = float(np.max(np.abs(flat))) if flat.size else 0.0
    rms = float(np.sqrt(np.mean(flat ** 2))) if flat.size else 0.0
    duration = float(len(flat)) / float(sr or 16000)
    ok = not (peak < QUIET_PEAK_THRESHOLD and rms < QUIET_RMS_THRESHOLD)
    return {
        "ok": ok,
        "peak": round(peak, 4),
        "rms": round(rms, 4),
        "duration_s": round(duration, 2),
        "hint": "" if ok else "Âm thanh quá nhỏ — hãy nói to hơn, gần mic hơn rồi chấm lại.",
    }


def frame_rms(wav: np.ndarray, frame_len: int = 320) -> np.ndarray:
    n = max(1, len(wav) // frame_len)
    out = np.zeros(n, dtype=np.float32)
    for i in range(n):
        seg = wav[i * frame_len:(i + 1) * frame_len]
        out[i] = float(np.sqrt(np.mean(seg ** 2) + 1e-12))
    return out


def vad_segments(wav: np.ndarray, sr: int = 16000, energy_thr: float = 0.003,
                 silence_s: float = 0.5, min_speech_s: float = 0.3) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
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


def extract_f0(wav: np.ndarray, sr: int = 16000) -> dict[str, Any]:
    try:
        import librosa
        f0, voiced_flag, _ = librosa.pyin(wav, fmin=librosa.note_to_hz("C2"),
                                          fmax=librosa.note_to_hz("C7"), sr=sr)
        valid = f0[~np.isnan(f0)] if f0 is not None else np.array([])
        if len(valid) == 0:
            return {"median_f0": 0.0, "std_f0": 0.0, "p10": 0.0, "p90": 0.0,
                    "range_f0": 0.0, "final_slope": 0.0, "curve_t": [], "curve_f0": [], "voiced_ratio": 0.0}
        p10, p90 = float(np.percentile(valid, 10)), float(np.percentile(valid, 90))
        # slope 0.5s cuối
        tail = valid[-25:] if len(valid) >= 25 else valid
        slope = float(tail[-1] - tail[0]) if len(tail) >= 2 else 0.0
        # curve thưa 100 điểm để frontend vẽ
        idx = np.linspace(0, len(f0) - 1, min(100, len(f0))).astype(int)
        curve_t = [round(float(i) * 512 / sr, 2) for i in idx]  # pyin hop mặc định 512
        curve_f0 = [round(float(f0[i]) if not np.isnan(f0[i]) else 0.0, 1) for i in idx]
        return {"median_f0": round(float(np.median(valid)), 1), "std_f0": round(float(np.std(valid)), 1),
                "p10": round(p10, 1), "p90": round(p90, 1), "range_f0": round(p90 - p10, 1),
                "final_slope": round(slope, 1), "curve_t": curve_t, "curve_f0": curve_f0,
                "voiced_ratio": round(float(len(valid)) / max(1, len(f0)), 3)}
    except Exception as e:
        return {"median_f0": 0.0, "std_f0": 0.0, "p10": 0.0, "p90": 0.0, "range_f0": 0.0,
                "final_slope": 0.0, "curve_t": [], "curve_f0": [], "voiced_ratio": 0.0, "error": str(e)[:200]}

