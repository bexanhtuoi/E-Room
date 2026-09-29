from app.ai.tts import list_voices
from app.ai.tts import speak as tts_speak
from app.shared.exceptions import TTSUnavailableError

__all__ = [
    "list_voices",
    "speak_text",
]


def speak_text(text: str, voice: str = "", speed: float = 1.0) -> bytes:
    audio = tts_speak(text, voice=voice, speed=speed)

    if not audio:
        raise TTSUnavailableError()

    return audio
