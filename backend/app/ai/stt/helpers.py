import io
import re
import wave
from typing import List

import numpy as np

from app.config import settings

SPOKEN_LANGUAGES = ("en", "vi", "auto")
MIN_SEGMENT_LOGPROB = -1.0

STT_PROMPTS = {
    "en": (
        "This is an English speaking practice session in Vietnam. "
        "The speakers are Vietnamese learners introducing themselves in English. "
        "Common Vietnamese names you may hear: Hoang, Huong, An, Minh, Linh, Nam, Trang. "
        "Transcribe exactly what is said, word for word."
    ),
    "vi": (
        "Đây là một buổi luyện nói tiếng Việt. Người nói là người Việt Nam. "
        "Các tên thường gặp: Hoàng, Hương, An, Minh, Linh, Nam, Trang, Hà Nội, Sài Gòn. "
        "Ghi lại chính xác từng từ được nói, giữ nguyên dấu tiếng Việt."
    ),
    "auto": "Transcribe exactly what is said, word for word.",
}


def resolve_stt_language(value) -> str:
    text = str(value if value is not None else settings.stt_language or "en").strip().lower()
    return text if text in SPOKEN_LANGUAGES else "en"


def build_stt_prompt(language: str) -> str:
    return STT_PROMPTS.get(language, STT_PROMPTS["auto"])


def normalize_word_entry(word: dict) -> dict:
    return {
        "word": str(word.get("word", "")).strip(),
        "start": float(word.get("start", 0.0)),
        "end": float(word.get("end", 0.0)),
        "probability": float(word.get("probability", 1.0)),
    }


def normalize_pcm_int16(audio_data) -> np.ndarray:
    if isinstance(audio_data, np.ndarray):
        if audio_data.dtype == np.int16:
            return audio_data
        return (np.clip(audio_data, -1.0, 1.0) * 32767).astype(np.int16)

    return np.frombuffer(bytes(audio_data), dtype=np.int16)


def convert_audio_to_float32(audio_data: np.ndarray | bytes) -> np.ndarray:
    int16_arr = normalize_pcm_int16(audio_data)
    return int16_arr.astype(np.float32) / 32768.0


def convert_audio_to_wav_bytes(audio_data: np.ndarray | bytes, sample_rate: int = 16000) -> bytes:
    raw_int16 = normalize_pcm_int16(audio_data).tobytes()

    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(raw_int16)

    return wav_buffer.getvalue()


def normalize_words(text: str) -> List[str]:
    return re.findall(r"[a-zà-ỹ0-9]+", text.lower())


def is_repetitive_hallucination(text: str, min_repeats: int = 4) -> bool:
    words = text.lower().split()
    if len(words) < min_repeats:
        return False

    for unit in range(1, len(words) // 2 + 1):
        if len(words) % unit != 0:
            continue
        if words == words[:unit] * (len(words) // unit):
            return True

    return is_loopy_hallucination(text)


def is_loopy_hallucination(text: str, phrase_words: int = 4) -> bool:
    words = normalize_words(text)
    if len(words) < phrase_words * 2:
        return False

    seen = set()
    for i in range(len(words) - phrase_words + 1):
        phrase = " ".join(words[i : i + phrase_words])
        if phrase in seen:
            return True
        seen.add(phrase)

    return False


def is_prompt_echo(text: str, prompt: str) -> bool:
    text_words = normalize_words(text)
    prompt_words = normalize_words(prompt)
    if not text_words or not prompt_words:
        return False

    prompt_set = set(prompt_words)

    if len(text_words) >= 5 and all(word in prompt_set for word in text_words):
        return True

    joined_text = " ".join(text_words)
    joined_prompt = " ".join(prompt_words)
    if joined_prompt in joined_text:
        return True
    return len(text_words) >= 5 and joined_text in joined_prompt
