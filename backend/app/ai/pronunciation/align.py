from app.ai.pronunciation.helpers import tok_words


def align_transcripts(whisper_raw: str, user_corrected: str, whisper_segments: list[dict] | None = None) -> list[dict]:
    a, b = tok_words(whisper_raw), tok_words(user_corrected)
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
            i -= 1
            j -= 1
        elif i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + 1:
            h = whisper_hint(i - 1)
            ops.append({"word": b[j - 1], "source_word": a[i - 1], "alignment": "substitution",
                        "start_s": h["start_s"], "end_s": h["end_s"],
                        "span_available": h["start_s"] is not None, "ignored_for_pronunciation": False})
            i -= 1
            j -= 1
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

