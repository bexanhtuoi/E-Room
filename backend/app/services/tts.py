from app.ai.tts import list_voices as ai_list_voices
from app.ai.tts import speak as tts_speak
from app.services.base import ServiceBase
from app.shared.exceptions import TTSUnavailableError

__all__ = [
    "TTSService",
    "tts_service",
]


class TTSService(ServiceBase):
    def list_voices(self) -> list:
        return ai_list_voices()

    def speak_text(self, text: str, voice: str = "", speed: float = 1.0) -> bytes:
        audio = tts_speak(text, voice=voice, speed=speed)

        if not audio:
            raise TTSUnavailableError()

        return audio



tts_service = TTSService()
