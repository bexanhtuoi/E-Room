from typing import Any, Dict, List

from config import settings

_embed_model = None


def get_embed_model():
    global _embed_model

    if _embed_model is None:
        from sentence_transformers import SentenceTransformer

        _embed_model = SentenceTransformer(settings.embed_model_id)

    return _embed_model


def embed_texts(texts: List[str]) -> List[List[float]]:
    return get_embed_model().encode(texts, normalize_embeddings=True).tolist()


def score_audio(
    audio_path: str,
    reference_text: str,
    language: str = "en",
    confidence: float = 1.0,
    avg_logprob: float = 0.0,
    duration: float = 0.0,
    words=None,
) -> Dict[str, Any]:
    from app.ai.pronunciation import score_pronunciation

    return score_pronunciation(
        audio_path=audio_path,
        reference_text=reference_text,
        language=language,
        confidence=confidence,
        avg_logprob=avg_logprob,
        duration=duration,
        words=words or [],
    )


def warm_all() -> None:
    from app.ai.pronunciation.models import get_acoustic_model, get_phone_model

    get_acoustic_model()
    get_phone_model()
    get_embed_model()
