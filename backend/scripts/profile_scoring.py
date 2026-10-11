"""Do chi phi tung stage scoring XLSR-only (mock mac dinh, khong tai model).

Usage (from backend/):
    uv run python scripts/profile_scoring.py --mock [--seconds 10] [--repeat 3]
    uv run python scripts/profile_scoring.py --real --wav rec.wav --text "hello world"
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DEFAULT_SECONDS = 10

DEFAULT_REPEAT = 3

SAMPLE_RATE = 16000

SYNTH_FREQ_HZ = 440.0

TRELLIS_FRAMES_PER_SECOND = 50

CHAR_VOCAB_SIZE = 32

BLANK_ID = 0

G2P_WORDS = [
    "think",
    "she",
    "church",
    "sing",
    "cat",
    "bird",
    "water",
    "pronunciation",
    "morning",
    "world",
    "hello",
    "through",
]

ALIGN_RAW = "she sells seashells by the seashore"

ALIGN_FIXED = "she sells sea shells by the sea shore"


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    # 1. Khai bao CLI: mock do stage nhe, real moi cham model that
    parser = argparse.ArgumentParser(description="Profile tung stage scoring XLSR-only.")

    parser.add_argument("--mock", action="store_true", help="Chi do stage nhe, khong tai model.")

    parser.add_argument("--real", action="store_true", help="Do them forward model that (nang).")

    parser.add_argument("--wav", default="", help="File wav cho --real.")

    parser.add_argument("--text", default="hello world", help="Reference text cho --real.")

    parser.add_argument("--seconds", type=int, default=DEFAULT_SECONDS, help="Do dai audio gia cho --mock.")

    parser.add_argument("--repeat", type=int, default=DEFAULT_REPEAT, help="So lan lap moi stage.")

    parser.add_argument("--out", default="", help="Ghi JSON ket qua ra file.")

    return parser.parse_args(argv)


def synth_wav(seconds: int, sr: int = SAMPLE_RATE) -> np.ndarray:
    # 2. Tao sine + noise thay tieng noi de do pipeline ma khong can mic
    total = max(1, int(seconds * sr))

    axis = np.arange(total, dtype=np.float64) / float(sr)

    tone = 0.3 * np.sin(2.0 * np.pi * SYNTH_FREQ_HZ * axis)

    envelope = 0.6 + 0.4 * np.sin(2.0 * np.pi * 2.0 * axis)

    rng = np.random.default_rng(7)

    noise = 0.02 * rng.standard_normal(total)

    wav = (tone * envelope + noise).astype(np.float32)

    return wav


def time_call(func: Callable[[], Any], repeat: int, warmup: bool = True) -> Dict[str, Any]:
    # 3. Chay mo 1 lan truoc de loai cold-start (torch/numba), roi moi do lap
    if warmup:
        try:
            func()
        except Exception:
            pass

    samples: List[float] = []

    result: Any = None

    for _ in range(max(1, repeat)):
        start = time.perf_counter()

        result = func()

        samples.append((time.perf_counter() - start) * 1000.0)

    return {
        "mean_ms": round(sum(samples) / len(samples), 2),
        "min_ms": round(min(samples), 2),
        "max_ms": round(max(samples), 2),
        "n": len(samples),
        "result": result,
    }


def measure_rss_mb() -> Dict[str, Any]:
    # 4. Do RAM thuc te, khong doan mo bang so tham so
    try:
        import psutil

        proc = psutil.Process()

        return {
            "rss_mb": round(proc.memory_info().rss / 1024.0 / 1024.0, 1),
            "note": "psutil",
        }
    except Exception:
        return {
            "rss_mb": 0.0,
            "note": "can psutil de do RSS",
        }


def profile_lightweight(wav: np.ndarray, repeat: int) -> Dict[str, Any]:
    # 5. Do cac stage thuan Python/CPU, khong can model
    from app.ai.pronunciation.align import align_transcripts
    from app.ai.pronunciation.audio import check_audio_quality, extract_f0, load_wav_16k, vad_segments
    from app.ai.pronunciation.g2p import get_pronunciation
    from app.ai.pronunciation.metrics import calculate_overall, score_completeness, score_fluency
    from app.ai.pronunciation.models import ctc_forced_align

    stages: Dict[str, Any] = {}

    import soundfile as sf

    buf = io.BytesIO()

    sf.write(buf, wav, SAMPLE_RATE, format="WAV", subtype="PCM_16")

    raw = buf.getvalue()

    stages["synth_wav_s"] = {
        "mean_ms": 0.0,
        "note": "da tao truoc: %.1fs @ %dHz" % (len(wav) / SAMPLE_RATE, SAMPLE_RATE),
    }

    timed = time_call(lambda: load_wav_16k(raw), repeat)

    stages["load_wav_16k"] = {
        "mean_ms": timed["mean_ms"],
        "min_ms": timed["min_ms"],
        "max_ms": timed["max_ms"],
    }

    timed = time_call(lambda: check_audio_quality(wav, SAMPLE_RATE), repeat)

    stages["check_audio_quality"] = {
        "mean_ms": timed["mean_ms"],
        "ok": bool(timed["result"]["ok"]),
    }

    timed = time_call(lambda: vad_segments(wav, SAMPLE_RATE), repeat)

    stages["vad_segments"] = {
        "mean_ms": timed["mean_ms"],
        "n_segments": len(timed["result"][0]),
        "n_pauses": len(timed["result"][1]),
    }

    timed = time_call(lambda: align_transcripts(ALIGN_RAW, ALIGN_FIXED, None), repeat)

    stages["align_transcripts"] = {
        "mean_ms": timed["mean_ms"],
        "n_ops": len(timed["result"]),
    }

    cold_start = time.perf_counter()

    get_pronunciation(G2P_WORDS[0], "en-US")

    stages["g2p_cold_first_word_ms"] = round((time.perf_counter() - cold_start) * 1000.0, 2)

    timed = time_call(lambda: [get_pronunciation(w, "en-US") for w in G2P_WORDS], repeat)

    stages["g2p_warm_12_words"] = {
        "mean_ms": timed["mean_ms"],
    }

    timed = time_call(lambda: score_fluency(len(wav) / SAMPLE_RATE, 24, [], ALIGN_RAW), repeat)

    stages["score_fluency"] = {
        "mean_ms": timed["mean_ms"],
        "score": timed["result"]["score"],
    }

    timed = time_call(lambda: score_completeness(None, ALIGN_FIXED, "free_speaking", []), repeat)

    stages["score_completeness"] = {
        "mean_ms": timed["mean_ms"],
    }

    timed = time_call(lambda: calculate_overall(80.0, 85.0, 90.0, 100.0), repeat)

    stages["calculate_overall"] = {
        "mean_ms": timed["mean_ms"],
        "overall": timed["result"],
    }

    frames = max(50, int(len(wav) / SAMPLE_RATE * TRELLIS_FRAMES_PER_SECOND))

    targets = [1, 2, 3, 4, 5] * 8

    timed = time_call(lambda: synth_trellis(frames, targets, ctc_forced_align), repeat)

    stages["ctc_forced_align_synth"] = {
        "mean_ms": timed["mean_ms"],
        "min_ms": timed["min_ms"],
        "max_ms": timed["max_ms"],
        "frames": frames,
        "targets": len(targets),
        "note": "thay the cho align char/phone that, de quyet co thay trellis khong",
    }

    timed = time_call(lambda: extract_f0(wav, SAMPLE_RATE), repeat)

    stages["extract_f0_whole"] = {
        "mean_ms": timed["mean_ms"],
        "std_f0": timed["result"].get("std_f0", 0.0),
    }

    stages["pyin_call_count_note"] = {
        "mean_ms": 0.0,
        "note": "score_stress goi pyin 1 lan/tu da am tiet + extract_f0 1 lan/cau",
    }

    return stages


def synth_trellis(frames: int, targets: List[int], align_func: Callable[..., Any]) -> int:
    # 6. Dung log_probs ngaunhien de co lap trellis ma khong can forward model
    import torch

    logits = torch.randn(frames, CHAR_VOCAB_SIZE, dtype=torch.float32)

    log_probs = torch.log_softmax(logits, dim=-1)

    align, _ = align_func(log_probs, list(targets), BLANK_ID)

    return len(align)


def profile_real(wav_path: str, text: str) -> Dict[str, Any]:
    # 7. Do forward that: chi chay khi user chon --real vi tai model XLSR ~1.2GB
    from app.ai.pronunciation.models import get_phone_model, phone_model_id
    from app.ai.pronunciation.scorer import score_attempt_v2

    stages: Dict[str, Any] = {}

    raw = Path(wav_path).read_bytes()

    stages["audio_bytes"] = {
        "mean_ms": 0.0,
        "note": "%d bytes" % len(raw),
    }

    start = time.perf_counter()

    feeder, phone_model = get_phone_model()

    stages["load_phone_model_cold_ms"] = round((time.perf_counter() - start) * 1000.0, 2)

    stages["phone_model"] = {
        "mean_ms": 0.0,
        "id": phone_model_id(),
    }

    _ = feeder

    _ = phone_model

    try:
        import soundfile as sf

        wav_arr, sr = sf.read(io.BytesIO(raw), dtype="float32", always_2d=False)

        wav_np = np.asarray(wav_arr, dtype=np.float32).reshape(-1)

        timed = time_call(
            lambda: score_attempt_v2(wav_np, int(sr), "", text, "free_speaking", None, "en-US", None, None, ""),
            1,
        )

        report = timed["result"]

        stages["score_attempt_v2_full"] = {
            "mean_ms": timed["mean_ms"],
            "overall": (report.get("scores") or {}).get("overall"),
            "scorer_version": report.get("scorer_version", ""),
            "error": report.get("error", ""),
        }
    except Exception as error:
        stages["real_error"] = {
            "mean_ms": 0.0,
            "note": "that bai: %s" % str(error)[:200],
        }

    return stages


def print_table(stages: Dict[str, Any]) -> None:
    # 8. In bang de R&D nhin 1 phat biet tien nam o dau
    timed_keys = [k for k, v in stages.items() if isinstance(v, dict) and "mean_ms" in v and v["mean_ms"] > 0]

    total = sum(float(stages[k]["mean_ms"]) for k in timed_keys) or 1.0

    print("%-28s %12s %8s" % ("stage", "mean_ms", "share"))

    for key in timed_keys:
        mean = float(stages[key]["mean_ms"])

        print("%-28s %12.2f %7.1f%%" % (key, mean, 100.0 * mean / total))

    print("%-28s %12.2f" % ("TOTAL(timed)", total))


def main(argv: Optional[List[str]] = None) -> int:
    # 9. Dieu phoi: mock luon chay, real chi khi duoc yeu cau ro rang
    args = parse_args(argv)

    if not args.mock and not args.real:
        print("Chon --mock hoac --real (xem --help).")

        return 2

    stages: Dict[str, Any] = {}

    if args.mock:
        wav = synth_wav(max(1, args.seconds), SAMPLE_RATE)

        stages.update(profile_lightweight(wav, max(1, args.repeat)))

    if args.real:
        if not args.wav:
            print("--real can --wav duong dan file wav.")

            return 2

        stages.update(profile_real(args.wav, args.text))

    stages["rss"] = measure_rss_mb()

    print_table(stages)

    if args.out:
        Path(args.out).write_text(json.dumps(stages, ensure_ascii=False, indent=2), encoding="utf-8")

        print("Da ghi %s" % args.out)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
