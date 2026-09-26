"""TTS API: chon 1 trong 4 giong Anh + doc text thanh audio.

- GET  /tts/voices        -> 4 lua chon (Heart/Adam/Emma/George)
- POST /tts/speak         -> tra file mp3 (body: text, voice?, speed?)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from app.ai.tts import list_voices
from app.ai.tts import speak as tts_speak
from app.api.dependencies import require_auth
from app.schemas.tts import TTSSpeakRequest, TTSVoiceOption

router = APIRouter()


@router.get("/voices", response_model=list[TTSVoiceOption])
def get_tts_voices(_: str = Depends(require_auth)) -> list[TTSVoiceOption]:
    return [TTSVoiceOption(**v) for v in list_voices()]


@router.post("/speak")
def speak_text(payload: TTSSpeakRequest, _: str = Depends(require_auth)) -> Response:
    audio = tts_speak(payload.text, voice=payload.voice, speed=payload.speed)
    if not audio:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="TTS server unavailable")
    return Response(content=audio, media_type="audio/mpeg")
