"""TTS API: chon 1 trong 4 giong Anh + doc text thanh audio.

- GET  /tts/voices        -> 4 lua chon (Heart/Adam/Emma/George)
- POST /tts/speak         -> tra file mp3 (body: text, voice?, speed?)
"""

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.api.dependencies import require_auth
from app.schemas.tts import TTSSpeakRequest, TTSVoiceOption
from app.services import tts as tts_service

router = APIRouter()


@router.get("/voices", response_model=list[TTSVoiceOption])
def get_tts_voices(_: str = Depends(require_auth)) -> list[TTSVoiceOption]:
    return [TTSVoiceOption(**voice) for voice in tts_service.list_voices()]


@router.post("/speak")
def speak_text(payload: TTSSpeakRequest, _: str = Depends(require_auth)) -> Response:
    audio = tts_service.speak_text(payload.text, voice=payload.voice, speed=payload.speed)

    return Response(content=audio, media_type="audio/mpeg")
