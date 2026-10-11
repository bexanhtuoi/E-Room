import math
import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from app.ai.pronunciation.g2p import arpa_to_ipa, get_pronunciation, is_vowel
from app.ai.pronunciation.helpers import build_stt_span_map, gop_to_score
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
from app.ai.pronunciation.reductions import classify_phone_pair, reduction_floor, summarize_reductions
from app.log import get_logger

log = get_logger("app.ai.pronunciation.phonemes")


def observe_phones_fallback(greedy_text: str, canonical_arpa: List[str]) -> List[str]:
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


def score_word_sounds(w: Dict, greedy_text: str, accent: str, err_counter: Dict) -> Tuple:
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
        # phoneme sai -> trừ theo tỉ trọng 1/N từ (từ dài sai vài âm không mất trắng)
        penalty = 100.0 / max(1, len(arpa))

        pscore = char_score if typ == "match" else max(0.0, char_score - penalty)

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


def score_sounds(
    words_forced: List[Dict],
    greedy_text: str = "",
    accent: str = "en-US",
) -> Dict[str, Any]:
    phonemes: List[Dict] = []

    err_counter: Dict[str, Dict] = {}

    wdetails: List[Dict] = []

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




def score_stress(
    words_forced: List[Dict],
    wav: np.ndarray,
    sr: int = 16000,
    accent: str = "en-US",
) -> Dict:
    details: List[Dict] = []

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


def anchor_word_window(
    log_probs,
    target_ids_word: List[int],
    blank_id: int,
    stt_f0: int,
    stt_f1: int,
) -> Optional[tuple]:
    # 1. Căn lại phone trong cửa sổ STT khi CTC toàn câu bóp quá ngắn
    from app.ai.pronunciation.models import ctc_forced_align

    if stt_f1 < stt_f0:
        return None

    if len(target_ids_word) == 0:
        return None

    if (stt_f1 - stt_f0 + 1) < 3:
        return None

    sl = log_probs[stt_f0:stt_f1 + 1]

    align, _ = ctc_forced_align(sl, list(target_ids_word), blank_id)

    lps: List[float] = []

    spans: List[tuple] = []

    oks: List[bool] = []

    for i, tid in enumerate(target_ids_word):
        s = 2 * i + 1

        frames = [t for t in range(len(align)) if align[t] == s]

        if frames:
            vals = [float(sl[t, tid]) for t in frames]

            lps.append(sum(vals) / len(vals))

            spans.append((stt_f0 + frames[0], stt_f0 + frames[-1]))

            oks.append(True)
        else:
            lps.append(float("-inf"))

            spans.append((-1, -1))

            oks.append(False)

    if not any(oks):
        return None

    return lps, spans, oks


def score_phones_by_vad(
    warr,
    text: str,
    accent: str,
    word_spans: List[Dict],
    segs: List[tuple],
) -> Dict[str, Any]:
    # 1. Chẻ audio dài theo đoạn VAD rồi chấm từng chunk, gộp lại
    import re as re_local

    flat: List[Dict] = []

    for item in word_spans or []:
        if isinstance(item, dict) and isinstance(item.get("words"), list):
            flat.extend([w for w in item["words"] if isinstance(w, dict)])
        elif isinstance(item, dict) and item.get("word"):
            flat.append(item)

    chunks: List[Dict[str, Any]] = []

    for s, e in segs:
        s_i = max(0, int(s * 16000))

        e_i = min(len(warr), int(e * 16000))

        if e_i - s_i < 3200:
            continue

        part = [w for w in flat if span_mid(w) >= s and span_mid(w) < e]

        if not part:
            continue

        ctext = " ".join([str(w.get("word", "")) for w in part])

        if not re_local.findall(r"[A-Za-z']+", ctext):
            continue

        out = score_phones(warr[s_i:e_i], 16000, ctext, accent, part)

        if "error" in out:
            continue

        chunks.append(out)

    if not chunks:
        return score_phones(warr, 16000, text, accent, None)

    return merge_chunk_reports(chunks)


def span_mid(w: Dict) -> float:
    # 2. Điểm giữa span STT để gán từ vào đoạn VAD
    try:
        s = float(w.get("start", w.get("start_s", 0.0)))

        e = float(w.get("end", w.get("end_s", 0.0)))
    except (TypeError, ValueError):
        return 0.0

    return (s + e) / 2.0


def merge_chunk_reports(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    # 3. Gộp điểm các chunk theo trọng số số phone
    wdetails: List[Dict] = []

    phonemes: List[Dict] = []

    err: Dict[str, Dict] = {}

    total_phones = 0

    weighted = 0.0

    scored = 0

    no_ev = 0

    for ch in chunks:
        for d in ch.get("word_details", []):
            wdetails.append(d)

        for p in ch.get("phonemes", []):
            phonemes.append(p)

        for t in ch.get("top_errors", []):
            e = err.setdefault(t["pattern"], {"pattern": t["pattern"], "count": 0, "examples": []})

            e["count"] += int(t.get("count", 0))

            for ex in t.get("examples", []):
                if ex not in e["examples"]:
                    e["examples"].append(ex)

        for d in ch.get("word_details", []):
            if d.get("status") in ("ok", "pronunciation_error", "misaligned"):
                weighted += float(d.get("score", 0.0)) * int(d.get("n_phones", 0))

                total_phones += int(d.get("n_phones", 0))

        scored += int(ch.get("n_scored", 0))

        no_ev += int(ch.get("n_no_evidence", 0))

    sounds = round(weighted / total_phones, 1) if total_phones > 0 else 0.0

    return {"sounds": sounds, "word_details": wdetails, "phonemes": phonemes,
            "top_errors": sorted(err.values(), key=lambda x: -x["count"])[:5],
            "model": chunks[0].get("model", ""), "n_scored": scored,
            "n_no_evidence": no_ev}


def score_phones(
    wav,
    sr: int,
    text: str,
    accent: str = "en-US",
    word_spans: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    torch = load_torch()

    try:
        fe, model = get_phone_model()
    except Exception as error:
        return {"error": f"Model XLSR chưa sẵn sàng: {error}"}

    try:
        vocab = load_vocab()
    except Exception as error:
        return {"error": f"Không tải được vocab XLSR: {error}"}

    device = next(model.parameters()).device

    blank_id = 0  # <pad>

    # 1. Validate audio trước khi forward để fail-fast với lỗi tiếng Việt
    warr = np.asarray(wav, dtype=np.float32).reshape(-1)

    if warr.size == 0:
        return {"error": "Audio rỗng — hãy thu lại rồi chấm."}

    effective_sr = int(sr or 16000)

    if effective_sr != 16000:
        try:
            import librosa

            warr = librosa.resample(warr, orig_sr=effective_sr, target_sr=16000).astype(np.float32)
        except Exception:
            ratio = 16000 / float(effective_sr)

            idx = (np.arange(int(len(warr) * ratio)) / ratio).astype(int)

            idx = np.clip(idx, 0, len(warr) - 1)

            warr = warr[idx]

        effective_sr = 16000

    duration_s = len(warr) / 16000.0

    if duration_s < 0.2:
        return {"error": "Audio quá ngắn (<0.2s) — hãy nói dài hơn rồi chấm."}

    if duration_s > 600:
        return {"error": "Audio dài quá 10 phút — hãy chia thành nhiều lần chấm."}

    if duration_s > 60.0 and word_spans:
        # 2. Audio dài thì chẻ theo VAD để trellis ổn định, chống OOM
        from app.ai.pronunciation.audio import vad_segments

        segs, _ = vad_segments(warr, 16000)

        if len(segs) > 1:
            return score_phones_by_vad(warr, text, accent, word_spans, segs)

    words = [w for w in re.findall(r"[A-Za-z']+", text)]

    if not words:
        return {"error": "Text rỗng."}

    # 3. Canonical phone sequence + word ranges
    seq: List[str] = []

    wranges: List[Tuple[int, int, str, List[str]]] = []

    skipped_words: List[str] = []

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

    try:
        inputs = fe(warr, sampling_rate=16000, return_tensors="pt", padding=True)
    except Exception as error:
        return {"error": f"Audio không hợp lệ cho XLSR: {error}"}

    try:
        with torch.no_grad():
            logits = model(inputs.input_values.to(device)).logits[0].cpu()
    except Exception as error:
        # 2. OOM giữa chừng: dọn cache để lần chấm sau không chết theo
        try:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass

        return {"error": f"XLSR hết bộ nhớ khi chấm (audio {duration_s:.1f}s): {error}"}

    log_probs = torch.log_softmax(logits, dim=-1)

    T = log_probs.shape[0]

    pred_ids: List[int] = torch.argmax(logits, dim=-1).tolist()

    align, _ = ctc_forced_align(log_probs, target_ids, blank_id)

    # 4. GOP từng phone
    phone_lp: List[float] = []

    phone_span: List[Tuple[int, int]] = []

    phone_ok: List[bool] = []

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

    # 5. Observed phones: free recognition (greedy collapse, không LM)
    id2tok = {i: t for t, i in vocab.items()}

    span_map = build_stt_span_map(word_spans)

    collapsed, prev = [], None

    for pid in pred_ids:
        if pid != prev:
            if pid != blank_id:
                collapsed.append(id2tok.get(pid, ""))
        prev = pid

    phonemes: List[Dict] = []

    wdetails: List[Dict] = []

    err_counter: Dict[str, Dict] = {}

    red_counter: List[Dict] = []

    for idx, (p0, p1, w, arpa) in enumerate(wranges):
        canon = seq[p0:p1]

        next_w = wranges[idx + 1][2] if idx + 1 < len(wranges) else ""

        anchored = False

        stt_start = 0.0

        stt_end = 0.0

        # 6. Neo STT: CTC toàn câu hay bóp từ chức năng còn 1 frame
        ctc_f0 = phone_span[p0][0] if phone_ok[p0] else -1

        ctc_f1 = phone_span[p1 - 1][1] if phone_ok[p1 - 1] else -1

        ctc_dur = (ctc_f1 - ctc_f0 + 1) * FRAME_STRIDE_S if ctc_f0 >= 0 else 0.0

        queue = span_map.get(str(w).upper())

        if queue and ctc_dur < 0.08:
            stt_start, stt_end = queue.pop(0)

            stt_dur = stt_end - stt_start

            if stt_dur >= 0.08:
                margin = 0.05

                a = max(0, int((stt_start - margin) / FRAME_STRIDE_S))

                b = min(T - 1, int((stt_end + margin) / FRAME_STRIDE_S))

                fixed = anchor_word_window(log_probs, target_ids[p0:p1], blank_id, a, b)

                if fixed is not None:
                    lps, spans, oks = fixed

                    phone_lp[p0:p1] = lps

                    phone_span[p0:p1] = spans

                    phone_ok[p0:p1] = oks

                    anchored = True

        # 7. Observed evidence: align needleman toàn câu quá nặng nên so trong vùng từ
        f0 = phone_span[p0][0] if phone_ok[p0] else -1

        f1 = phone_span[p1 - 1][1] if phone_ok[p1 - 1] else -1

        if anchored:
            f0 = max(0, int(stt_start / FRAME_STRIDE_S))

            f1 = min(T - 1, int(stt_end / FRAME_STRIDE_S))

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

        span_dur = (f1 - f0 + 1) * FRAME_STRIDE_S if f0 >= 0 else 0.0

        if status == "scored" and span_dur < 0.08:
            # 3. Span quá ngắn (từ chức năng bị trellis bóp) -> không kết luận sai
            status = "misaligned"

        if anchored and status == "scored":
            # 4. Từ đã neo bằng STT thì chỉ báo khớp lệch để nghe lại
            status = "misaligned"

        pscores: List[float] = []

        n_ph0 = len(phonemes)

        for (exp, ob, typ), pi in zip(pairs, range(p0, p1)):
            # GOP: mean log-posterior chuẩn hoá; phone không frame loại khỏi mẫu số
            g = phone_lp[pi] if phone_ok[pi] else float("-inf")

            s100 = gop_to_score(g)

            disp_ob = ob if ob != "-" else None

            out_typ = typ

            if typ == "substitution" and status in ("scored", "misaligned"):
                rule = classify_phone_pair(exp, disp_ob, w, accent, next_w)

                if rule is not None:
                    out_typ = "reduction"

                    s100 = max(s100, reduction_floor(str(rule.get("kind", ""))))

                    red_counter.append({"pattern": f"/{exp}/ -> /{disp_ob}/ ({rule.get('label', '')})", "examples": [w]})

            if out_typ != "insertion" and status in ("scored", "misaligned") and math.isfinite(g):
                pscores.append(s100)

            phonemes.append({"word": w, "expected": exp, "observed": disp_ob,
                             "type": out_typ, "gop": round(g, 3) if math.isfinite(g) else None,
                             "score": s100 if status in ("scored", "misaligned") else 0.0})
            if out_typ == "substitution" and status in ("scored", "misaligned"):
                pat = f"/{exp}/ -> /{ob}/"

                e = err_counter.setdefault(pat, {"pattern": pat, "count": 0, "examples": []})

                e["count"] += 1

                if w not in e["examples"]:
                    e["examples"].append(w)
        wscore = round(sum(pscores) / len(pscores), 1) if pscores else 0.0

        if anchored and not pscores:
            # 5. Neo STT mà không có phone chuẩn để chấm thì cho qua trung tính
            wscore = 70.0

        n_phones = len(phonemes) - n_ph0

        if status == "scored":
            word_status = "ok" if pscores and wscore >= 70.0 else "pronunciation_error" if pscores else "no_evidence"
        else:
            word_status = status

        pron = get_pronunciation(w, accent)

        wdetails.append({"word": w, "score": wscore,
                         "status": word_status,
                         "start_s": round(f0 * FRAME_STRIDE_S, 2) if f0 >= 0 else 0.0,
                         "end_s": round((f1 + 1) * FRAME_STRIDE_S, 2) if f1 >= 0 else 0.0,
                         "acoustic_confidence": None, "expected_ipa": pron["ipa"],
                         "blank_ratio": round(blank_ratio, 3),
                         "n_phones": n_phones})
    for w in skipped_words:
        wdetails.append({"word": w, "score": 0.0, "status": "no_evidence",
                         "start_s": 0.0, "end_s": 0.0, "acoustic_confidence": None,
                         "expected_ipa": "", "blank_ratio": 1.0, "n_phones": 0})

    scored_w = [d for d in wdetails if d["status"] in ("ok", "pronunciation_error", "misaligned")]

    total_phones = sum(d.get("n_phones", 0) for d in scored_w)

    if scored_w and total_phones > 0:
        sounds = round(sum(d["score"] * d.get("n_phones", 0) for d in scored_w) / total_phones, 1)
    elif scored_w:
        sounds = round(sum(d["score"] for d in scored_w) / len(scored_w), 1)
    else:
        sounds = 0.0

    # 7. Tổng hợp điểm sounds theo trọng số số phone
    return {"sounds": sounds, "word_details": wdetails, "phonemes": phonemes,
            "top_errors": sorted(err_counter.values(), key=lambda x: -x["count"])[:5],
            "reductions": summarize_reductions(red_counter),
            "model": PHONE_MODEL_ID, "n_scored": len(scored_w),
            "n_no_evidence": len(wdetails) - len(scored_w)}

