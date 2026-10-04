from typing import Optional

import models
from config import settings
from fastapi import APIRouter, Header, HTTPException
from helpers import check_auth, sanitize, temp_wav
from schemas import EmbedRequest, ScoreRequest

router = APIRouter()


@router.get("/warm")
def warm(authorization: Optional[str] = Header(default=None)):
    check_auth(authorization)
    models.warm_all()

    return {"warmed": True}


@router.post("/score")
def score(payload: ScoreRequest, authorization: Optional[str] = Header(default=None)):
    check_auth(authorization)

    reference = (payload.reference_text or "").strip()

    if not reference:
        raise HTTPException(status_code=400, detail="BAD_REQUEST")

    with temp_wav(payload.audio_base64) as wav_path:
        result = models.score_audio(
            audio_path=wav_path,
            reference_text=reference,
            language=payload.language,
            confidence=payload.confidence,
            avg_logprob=payload.avg_logprob,
            duration=payload.duration,
            words=payload.words,
        )

    return sanitize(result)


@router.post("/v1/embeddings")
def embeddings(payload: EmbedRequest, authorization: Optional[str] = Header(default=None)):
    check_auth(authorization)

    texts = payload.input if isinstance(payload.input, list) else [payload.input]
    vectors = models.embed_texts([str(text) for text in texts])

    return {
        "object": "list",
        "data": [{"object": "embedding", "index": i, "embedding": vec} for i, vec in enumerate(vectors)],
        "model": payload.model or settings.embed_model_id,
    }
