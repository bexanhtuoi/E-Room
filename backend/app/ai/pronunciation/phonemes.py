import math
import re
from typing import Any

import numpy as np

from app.ai.pronunciation.g2p import arpa_to_ipa, get_pronunciation, is_vowel
from app.ai.pronunciation.metrics import needleman
from app.ai.pronunciation.models import (
    BLANK_RATIO_MISALIGNED,
    FRAME_STRIDE_S,
    PHONE_MODEL_ID,
    arpa_to_espeak,
    ctc_forced_align,
    get_phone_model,
    load_torch,
    load_vocab,
)
from app.log import get_logger

log = get_logger("app.ai.pronunciation.phonemes")


def observe_phones_fallback(greedy_text: str, canonical_arpa: list[str]) -> list[str]:
    g = (greedy_text or "").upper()

    # map chữ cái đầu từ greedy sang ARPAbet tương ứng để so với canonical
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


def score_word_sounds(w: dict, greedy_text: str, accent: str, err_counter: dict) -> tuple:
    word = w.get("word", "")

    status_in = w.get("status", "scored")

    if status_in != "scored":
        # Không evidence (misaligned/no_evidence): loại khỏi mẫu số, UI hiện "Không nghe rõ"
        detail = {"word": word, "score": 0.0, "status": "no_evidence",
                  "start_s": w.get("start_s"), "end_s": w.get("end_s"),
                  "acoustic_confidence": w.get("avg_log_prob"),
                  "expected_ipa": get_pronunciation(word, accent)["ipa"]}
        return detail, [], [], []

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

        pairs = needleman(arpa, (obs_full + arpa)[:len(arpa)])

    phonemes, v_scores, c_scores = [], [], []

    for exp, ob, typ in pairs:
        # phoneme sai -> phạt 25đ so với word score (MVP heuristic, thay bằng GOP thật ở v1.1)
        pscore = char_score if typ == "match" else max(0.0, char_score - 25.0)

        gop = math.log(max(1e-6, pscore / 100.0))

        phonemes.append({"word": word, "expected": "/" + arpa_to_ipa(exp) + "/",
                         "observed": "/" + arpa_to_ipa(ob) + "/" if ob != "-" else None,
                         "type": typ, "gop": round(gop, 3), "score": round(pscore, 1)})

        (v_scores if is_vowel(exp) else c_scores).append(pscore)

        if typ == "substitution":
            pat = f"/{arpa_to_ipa(exp)}/ → /{arpa_to_ipa(ob)}/"

            entry = err_counter.setdefault(pat, {"pattern": pat, "count": 0, "examples": []})

            entry["count"] += 1

            if word not in entry["examples"]:
                entry["examples"].append(word)

    status = "ok" if char_score >= 70 else "pronunciation_error"

    detail = {"word": word, "score": round(char_score, 1), "status": status,
              "start_s": w.get("start_s"), "end_s": w.get("end_s"),
              "acoustic_confidence": w.get("avg_logprob"),
              "expected_ipa": pron["ipa"]}

    return detail, phonemes, v_scores, c_scores


def score_sounds(words_forced: list[dict], greedy_text: str = "", accent: str = "en-US") -> dict[str, Any]:
    phonemes: list[dict] = []

    err_counter: dict[str, dict] = {}

    wdetails: list[dict] = []

    v_scores, c_scores = [], []

    for w in words_forced:
        detail, word_phonemes, v_part, c_part = score_word_sounds(w, greedy_text, accent, err_counter)

        wdetails.append(detail)

        phonemes.extend(word_phonemes)

        v_scores.extend(v_part)

        c_scores.extend(c_part)

    scored = [d for d in wdetails if d["status"] != "no_evidence"]

    sounds = round(sum(d["score"] for d in scored) / max(1, len(scored)), 1) if wdetails else 0.0

    top_errors = sorted(err_counter.values(), key=lambda x: -x["count"])[:5]

    return {"sounds": sounds,
            "vowel_score": round(sum(v_scores) / max(1, len(v_scores)), 1) if v_scores else sounds,
            "consonant_score": round(sum(c_scores) / max(1, len(c_scores)), 1) if c_scores else sounds,
            "word_details": wdetails, "phonemes": phonemes, "top_errors": top_errors}




def score_stress(words_forced: list[dict], wav: np.ndarray, sr: int = 16000, accent: str = "en-US") -> dict:
    details: list[dict] = []

    correct = 0

    total = 0

    for w in words_forced:
        if w.get("status", "scored") == "no_evidence":
            details.append({"word": w.get("word", ""), "expected_stress": None,
                            "detected_stress": None, "correct": None, "reason": "no_evidence"})
            continue

        pron = get_pronunciation(w.get("word", ""), accent)

        n = pron["num_syllables"]

        if n <= 1 or w.get("start_s") is None:
            details.append({"word": w.get("word", ""), "expected_stress": pron["stress_index"],
                            "detected_stress": pron["stress_index"], "correct": True if n <= 1 else None,
                            "reason": "mono-syllable" if n <= 1 else "missing_span"})
            continue

        s, e = float(w["start_s"]), float(w["end_s"])

        s_i, e_i = max(0, int(s * sr)), min(len(wav), int(e * sr))

        seg = wav[s_i:e_i]

        if len(seg) < 160:
            details.append({"word": w.get("word", ""), "expected_stress": pron["stress_index"],
                            "detected_stress": None, "correct": False, "reason": "too_short"})
            total += 1

            continue

        # chia theo tỉ lệ phoneme trong syllable (MVP: đều theo số phone mỗi syllable — tốt hơn chia đều time)
        syls = pron["syllables"]

        lens = [max(1, len(x)) for x in syls]

        tot = sum(lens)

        bounds = []

        cur = 0

        for syllable_len in lens:
            nxt = cur + int(len(seg) * syllable_len / tot)

            bounds.append((cur, nxt))

            cur = nxt

        bounds[-1] = (bounds[-1][0], len(seg))

        try:
            import librosa

            f0, _, _ = librosa.pyin(seg, fmin=librosa.note_to_hz("C2"), fmax=librosa.note_to_hz("C7"), sr=sr)

            f0m = []

            hop = 512

            for a, b in bounds:
                fa, fb = a // hop, max(a // hop + 1, b // hop)

                vals = f0[fa:fb] if f0 is not None else []

                vals = [float(x) for x in vals if x == x]

                f0m.append(sum(vals) / len(vals) if vals else 0.0)
        except Exception:
            f0m = [0.0] * len(bounds)

        proms = []

        for (a, b), f in zip(bounds, f0m):
            part = seg[a:b]

            dur = (b - a) / sr

            energy = float(np.sqrt(np.mean(part ** 2) + 1e-12))

            proms.append((dur, energy, f))

        # z-norm trong word
        def znorm(xs):
            mean = sum(xs) / len(xs)

            var = sum((x - mean) ** 2 for x in xs) / len(xs)

            std = math.sqrt(var + 1e-9)

            return [(x - mean) / (std + 1e-9) for x in xs]

        dz = znorm([p[0] for p in proms])

        ez = znorm([p[1] for p in proms])

        fz = znorm([p[2] for p in proms])

        scores = [0.4 * d + 0.4 * e + 0.2 * f for d, e, f in zip(dz, ez, fz)]

        det = max(range(len(scores)), key=lambda i: scores[i])

        exp = pron["stress_index"]

        ok = (det == exp)

        details.append({"word": w.get("word", ""), "expected_stress": exp, "detected_stress": det,
                        "correct": ok, "reason": ""})
        total += 1

        if ok:
            correct += 1

    score = round(100.0 * correct / max(1, total), 1) if total else 85.0

    return {"stress": score, "correct": correct, "total": total, "details": details}


def score_phones(wav, sr: int, text: str, accent: str = "en-US") -> dict[str, Any]:
    torch = load_torch()

    fe, model = get_phone_model()

    vocab = load_vocab()

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
        pairs = needleman(canon, obs_w)

        # blank density trên word span
        if f0 >= 0:
            tot = f1 - f0 + 1

            n_blank = sum(1 for t in range(f0, f1 + 1) if pred_ids[t] == blank_id)

            blank_ratio = n_blank / max(1, tot)
        else:
            blank_ratio = 1.0
        has_frames = any(phone_ok[p0:p1])

        if not has_frames:
            # Thật sự không có frame nào khớp -> thiếu bằng chứng.
            status = "no_evidence"
        elif blank_ratio > BLANK_RATIO_MISALIGNED:
            # Model espeak-xlsr cho posterior peaky (blank 0.7-0.9 ngay cả
            # với từ đọc rõ) nên KHÔNG loại từ này: vẫn chấm bằng GOP
            # (posterior thấp tự cho điểm thấp trung thực), chỉ đánh dấu
            # để UI hiện "Khớp lệch" thay vì "Không nghe rõ".
            status = "misaligned"
        else:
            status = "scored"

        pscores: list[float] = []

        for (exp, ob, typ), pi in zip(pairs, range(p0, p1)):
            # GOP: mean log-posterior; no_evidence -> -inf
            g = phone_lp[pi] if phone_ok[pi] else float("-inf")

            s100 = round(max(0.0, min(100.0, math.exp(max(g, -10.0)) * 100.0)), 1) if math.isfinite(g) else 0.0

            if status in ("scored", "misaligned"):
                pscores.append(s100)
            disp_ob = ob if ob != "-" else None

            phonemes.append({"word": w, "expected": exp, "observed": disp_ob,
                             "type": typ, "gop": round(g, 3) if math.isfinite(g) else None,
                             "score": s100 if status in ("scored", "misaligned") else 0.0})
            if typ == "substitution" and status in ("scored", "misaligned"):
                pat = f"/{exp}/ -> /{ob}/"

                e = err_counter.setdefault(pat, {"pattern": pat, "count": 0, "examples": []})

                e["count"] += 1

                if w not in e["examples"]:
                    e["examples"].append(w)
        wscore = round(sum(pscores) / len(pscores), 1) if pscores else 0.0

        pron = get_pronunciation(w, accent)

        wdetails.append({"word": w, "score": wscore,
                         "status": "ok" if status == "scored" else status,
                         "start_s": round(f0 * FRAME_STRIDE_S, 2) if f0 >= 0 else 0.0,
                         "end_s": round((f1 + 1) * FRAME_STRIDE_S, 2) if f1 >= 0 else 0.0,
                         "acoustic_confidence": None, "expected_ipa": pron["ipa"],
                         "blank_ratio": round(blank_ratio, 3)})
    for w in skipped_words:
        wdetails.append({"word": w, "score": 0.0, "status": "no_evidence",
                         "start_s": 0.0, "end_s": 0.0, "acoustic_confidence": None,
                         "expected_ipa": "", "blank_ratio": 1.0})

    ok_w = [d for d in wdetails if d["status"] in ("ok", "misaligned")]

    sounds = round(sum(d["score"] for d in ok_w) / len(ok_w), 1) if ok_w else 0.0

    # vowel/consonant split theo ARPAbet gốc
    return {"sounds": sounds, "word_details": wdetails, "phonemes": phonemes,
            "top_errors": sorted(err_counter.values(), key=lambda x: -x["count"])[:5],
            "model": PHONE_MODEL_ID, "n_scored": len(ok_w),
            "n_no_evidence": len(wdetails) - len(ok_w)}

