"""Small text utils shared by aligner and scorer."""
import re


def _tok_words(text: str) -> list[str]:
    return [w for w in re.findall(r"[A-Za-z']+", (text or "").lower())]

