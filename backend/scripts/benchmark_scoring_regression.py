"""Hoi quy diem scoring: Pearson, |delta|, flip-rate status (mock khong can model).

Usage (from backend/):
    uv run python scripts/benchmark_scoring_regression.py --mock [--pairs 20] [--mode stability|noise]
    uv run python scripts/benchmark_scoring_regression.py --dataset manifest.jsonl --out run_b.json
    uv run python scripts/benchmark_scoring_regression.py --compare run_a.json run_b.json
    uv run python scripts/benchmark_scoring_regression.py --self-test
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

PEARSON_MIN = 0.99

MEAN_DELTA_MAX = 1.0

FLIP_RATE_MAX = 0.05

MOCK_VERSION = "regression-mock-v1"

CRITERIA_KEYS = [
    "sounds",
    "stress",
    "fluency",
    "completeness",
    "overall",
]

MOCK_SENTENCES = [
    "she sells seashells by the seashore",
    "three thin thinkers thought through theories",
    "the quick brown fox jumps over the lazy dog",
    "a cat sat on a mat in the morning",
    "pronunciation matters more than perfection",
    "world peace begins with hello",
]


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    # 1. Ba che do: mock (khong model), dataset (thu run that), compare (cham pass/fail)
    parser = argparse.ArgumentParser(description="Hoi quy diem scoring XLSR-only.")

    parser.add_argument("--mock", action="store_true", help="Dung report gia lap, khong can model.")

    parser.add_argument("--pairs", type=int, default=20, help="So cau gia lap cho --mock.")

    parser.add_argument("--mode", default="noise", choices=["stability", "noise"], help="stability: A==B, noise: B lech nhe.")

    parser.add_argument("--dataset", default="", help="Manifest jsonl {audio, reference} de thu run that.")

    parser.add_argument("--compare", nargs=2, default=None, metavar=("A", "B"), help="So 2 file run.")

    parser.add_argument("--out", default="", help="Ghi JSON ket qua ra file.")

    parser.add_argument("--self-test", action="store_true", help="Kiem tra ham thong ke, khong can model.")

    return parser.parse_args(argv)


def pearson(xs: List[float], ys: List[float]) -> float:
    # 2. Tuong quan tuyen tinh, dung so sanh diem truoc/sau toi uu
    n = len(xs)

    if n < 2 or len(ys) != n:
        return 0.0

    mean_x = sum(xs) / n

    mean_y = sum(ys) / n

    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))

    den_x = sum((x - mean_x) ** 2 for x in xs)

    den_y = sum((y - mean_y) ** 2 for y in ys)

    den = math.sqrt(den_x * den_y)

    if den == 0.0:
        return 1.0 if den_x == 0.0 and den_y == 0.0 else 0.0

    return round(num / den, 4)


def deltas(xs: List[float], ys: List[float]) -> Dict[str, float]:
    # 3. Do lech tuyet doi trung binh va lon nhat giua 2 lan chay
    pairs = [abs(x - y) for x, y in zip(xs, ys)]

    if not pairs:
        return {
            "mean": 0.0,
            "max": 0.0,
            "n": 0,
        }

    return {
        "mean": round(sum(pairs) / len(pairs), 3),
        "max": round(max(pairs), 3),
        "n": len(pairs),
    }


def flip_rate(status_a: List[str], status_b: List[str]) -> Dict[str, Any]:
    # 4. Ti le tu doi status (ok/misaligned/no_evidence), nhay cam hon diem so
    total = min(len(status_a), len(status_b))

    if total == 0:
        return {
            "rate": 0.0,
            "flips": 0,
            "total": 0,
        }

    flips = sum(1 for i in range(total) if status_a[i] != status_b[i])

    return {
        "rate": round(flips / total, 4),
        "flips": flips,
        "total": total,
    }


def mock_report(index: int, noise: float = 0.0) -> Dict[str, Any]:
    # 5. Report gia lap nhung giu dung shape that de test pipeline so sanh
    base = 72.0 + (index % 9) * 2.5 + noise

    words = MOCK_SENTENCES[index % len(MOCK_SENTENCES)].split()

    details: List[Dict[str, Any]] = []

    for pos, word in enumerate(words):
        score = round(base - (pos % 4) * 6.0 + noise, 1)

        if score >= 70.0:
            status = "ok"
        elif score >= 40.0:
            status = "pronunciation_error"
        else:
            status = "no_evidence"

        details.append({
            "word": word,
            "score": score,
            "status": status,
        })

    return {
        "id": "mock-%d" % index,
        "scores": {
            "sounds": round(base, 1),
            "stress": round(base + 3.0, 1),
            "fluency": round(base + 5.0, 1),
            "completeness": 100.0,
            "overall": round(base + 1.0, 1),
        },
        "word_details": details,
        "top_errors": [],
        "scorer_version": MOCK_VERSION,
    }


def collect_mock(pairs: int, mode: str) -> Dict[str, List[Dict[str, Any]]]:
    # 6. Tao 2 run: stability thi giong het, noise thi lech nhe nhu sau quantize
    run_a: List[Dict[str, Any]] = []

    run_b: List[Dict[str, Any]] = []

    for index in range(max(1, pairs)):
        run_a.append(mock_report(index, 0.0))

        if mode == "stability":
            run_b.append(mock_report(index, 0.0))
        else:
            run_b.append(mock_report(index, 0.3))

    return {
        "a": run_a,
        "b": run_b,
    }


def collect_dataset(manifest: str) -> List[Dict[str, Any]]:
    # 7. Chay scorer that tren manifest, loi cau nao giu lai error chu khong dung ca lo
    from app.ai.pronunciation.scorer import score_pronunciation

    run: List[Dict[str, Any]] = []

    for line in Path(manifest).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue

        entry = json.loads(line)

        audio = str(entry.get("audio", ""))

        reference = str(entry.get("reference", ""))

        item: Dict[str, Any] = {
            "id": audio,
        }

        try:
            scored = score_pronunciation(audio_path=audio, reference_text=reference)

            item["scores"] = (scored.get("report") or {}).get("scores", scored.get("scores", {}))

            report = scored.get("report", scored)

            item["word_details"] = report.get("word_details", [])

            item["top_errors"] = report.get("top_errors", [])

            item["scorer_version"] = scored.get("scorer_version", report.get("scorer_version", ""))
        except Exception as error:
            item["error"] = str(error)[:200]

        run.append(item)

    return run


def compare_runs(run_a: List[Dict[str, Any]], run_b: List[Dict[str, Any]]) -> Dict[str, Any]:
    # 8. So 2 run theo dung nguong da chot: Pearson>=0.99, mean|d|<1.0, flip<=5%
    clean_a = [r for r in run_a if "error" not in r]

    clean_b = [r for r in run_b if "error" not in r]

    n = min(len(clean_a), len(clean_b))

    criteria: Dict[str, Any] = {}

    for key in CRITERIA_KEYS:
        xs = [float(r["scores"][key]) for r in clean_a[:n] if key in r.get("scores", {})]

        ys = [float(r["scores"][key]) for r in clean_b[:n] if key in r.get("scores", {})]

        criteria[key] = {
            "pearson": pearson(xs, ys),
            "delta": deltas(xs, ys),
        }

    status_a: List[str] = []

    status_b: List[str] = []

    for ra, rb in zip(clean_a[:n], clean_b[:n]):
        for wa, wb in zip(ra.get("word_details", []), rb.get("word_details", [])):
            status_a.append(str(wa.get("status", "")))

            status_b.append(str(wb.get("status", "")))

    flips = flip_rate(status_a, status_b)

    overall = criteria.get("overall", {})

    passed = (
        float(overall.get("pearson", 0.0)) >= PEARSON_MIN
        and float(overall.get("delta", {}).get("mean", 999.0)) <= MEAN_DELTA_MAX
        and float(flips.get("rate", 1.0)) <= FLIP_RATE_MAX
    )

    return {
        "n_pairs": n,
        "n_errors_a": len(run_a) - len(clean_a),
        "n_errors_b": len(run_b) - len(clean_b),
        "criteria": criteria,
        "status_flips": flips,
        "thresholds": {
            "pearson_min": PEARSON_MIN,
            "mean_delta_max": MEAN_DELTA_MAX,
            "flip_rate_max": FLIP_RATE_MAX,
        },
        "versions": {
            "a": sorted({str(r.get("scorer_version", "")) for r in run_a}),
            "b": sorted({str(r.get("scorer_version", "")) for r in run_b}),
        },
        "passed": bool(passed),
    }


def run_self_test() -> int:
    # 9. Tu kiem tra khong can model de khoa vao CI
    assert pearson([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == 1.0

    assert pearson([80.0, 80.0], [80.0, 80.0]) == 1.0

    assert deltas([80.0, 70.0], [80.3, 69.8])["mean"] == 0.25

    assert flip_rate(["ok", "ok"], ["ok", "misaligned"])["rate"] == 0.5

    collected = collect_mock(6, "stability")

    result = compare_runs(collected["a"], collected["b"])

    assert result["passed"] is True

    assert result["n_pairs"] == 6

    print("self-test OK: pearson/delta/flip/compare deu dung.")

    return 0


def print_result(result: Dict[str, Any]) -> None:
    # 10. In gon de R&D quyet pass/fail trong 10 giay
    overall = result["criteria"].get("overall", {})

    print("pairs=%s errors(a/b)=%s/%s" % (result["n_pairs"], result["n_errors_a"], result["n_errors_b"]))

    print("overall pearson=%s mean|d|=%s max|d|=%s" % (
        overall.get("pearson"),
        overall.get("delta", {}).get("mean"),
        overall.get("delta", {}).get("max"),
    ))

    print("status flips=%s/%s rate=%s" % (
        result["status_flips"].get("flips"),
        result["status_flips"].get("total"),
        result["status_flips"].get("rate"),
    ))

    print("PASSED" if result["passed"] else "FAILED")


def main(argv: Optional[List[str]] = None) -> int:
    # 11. Dieu phoi 4 che do, collect luon exit 0, compare thi exit theo pass/fail
    args = parse_args(argv)

    if args.self_test:
        return run_self_test()

    if args.compare is not None:
        run_a = json.loads(Path(args.compare[0]).read_text(encoding="utf-8"))

        run_b = json.loads(Path(args.compare[1]).read_text(encoding="utf-8"))

        if isinstance(run_a, dict) and "a" in run_a:
            run_a = run_a["a"]

        if isinstance(run_b, dict) and "b" in run_b:
            run_b = run_b["b"]

        if isinstance(run_a, dict) and "run" in run_a:
            run_a = run_a["run"]

        if isinstance(run_b, dict) and "run" in run_b:
            run_b = run_b["run"]

        result = compare_runs(list(run_a), list(run_b))

        print_result(result)

        if args.out:
            Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

        return 0 if result["passed"] else 1

    if args.mock:
        collected = collect_mock(max(1, args.pairs), args.mode)

        result = compare_runs(collected["a"], collected["b"])

        print_result(result)

        if args.out:
            Path(args.out).write_text(
                json.dumps({
                    "run": collected["b"],
                    "baseline": collected["a"],
                    "comparison": result,
                }, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        return 0 if result["passed"] else 1

    if args.dataset:
        run = collect_dataset(args.dataset)

        payload = {
            "run": run,
        }

        if args.out:
            Path(args.out).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

            print("Da thu %d cau -> %s" % (len(run), args.out))
        else:
            print(json.dumps({"n": len(run)}, ensure_ascii=False))

        return 0

    print("Chon --mock, --dataset hoac --compare (xem --help).")

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
