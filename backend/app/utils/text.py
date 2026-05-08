from __future__ import annotations

import re
from typing import Optional


def truncate(text: str, max_length: int = 500, ellipsis: str = "…") -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - len(ellipsis)] + ellipsis


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def sentence_count(text: str) -> int:
    return len(re.split(r"[.!?]+", text)) - 1 if text.strip() else 0


def levenshtein_ratio(s1: str, s2: str) -> float:
    m, n = len(s1), len(s2)
    if m == 0 and n == 0:
        return 1.0
    if m == 0 or n == 0:
        return 0.0
    prev = list(range(n + 1))
    for i in range(1, m + 1):
        curr = [i] + [0] * n
        for j in range(1, n + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            curr[j] = min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
        prev = curr
    distance = prev[n]
    return 1.0 - (distance / max(m, n))


def normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def sanitize_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text.strip("-")


def highlight_difference(original: str, corrected: str) -> dict[str, str]:
    if original == corrected:
        return {"original": original, "corrected": corrected, "diff": "same"}
    ratio = levenshtein_ratio(original, corrected)
    if ratio > 0.8:
        return {"original": original, "corrected": corrected, "diff": "minor"}
    return {"original": original, "corrected": corrected, "diff": "major"}
