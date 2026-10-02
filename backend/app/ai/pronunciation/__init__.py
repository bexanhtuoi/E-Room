from app.ai.pronunciation.align import align_transcripts, apply_forced_spans
from app.ai.pronunciation.articulation import guide_for_word, mouth_guide, parse_confusion, vi_reading
from app.ai.pronunciation.audio import (
    QUIET_PEAK_THRESHOLD,
    QUIET_RMS_THRESHOLD,
    check_audio_quality,
    extract_f0,
    frame_rms,
    load_wav_16k,
    vad_segments,
)
from app.ai.pronunciation.g2p import arpa_to_ipa, get_pronunciation, split_syllables
from app.ai.pronunciation.helpers import tok_words
from app.ai.pronunciation.metrics import (
    calculate_overall,
    needleman,
    score_completeness,
    score_fluency,
)
from app.ai.pronunciation.models import (
    BLANK_RATIO_MISALIGNED,
    FRAME_STRIDE_S,
    arpa_to_espeak,
    ctc_forced_align,
    get_acoustic_model,
    get_phone_model,
)
from app.ai.pronunciation.phonemes import observe_phones_fallback, score_phones, score_sounds, score_stress
from app.ai.pronunciation.scorer import (
    heuristic_score,
    normalize_reference,
    score_attempt_v2,
    score_local,
    score_pronunciation,
    score_utterance,
    score_via_pronun_service,
    score_with_wav2vec2,
)

_FEEDBACK_NAMES = frozenset({
    "SESSION_FEEDBACK_PROMPT",
    "SYSTEM_PROMPT",
    "build_fallback_feedback",
    "extract_json",
    "generate_feedback",
    "load_feedback_prompts",
    "request_pronun_feedback",
    "strip_reasoning",
})


def __getattr__(name: str):
    if name in _FEEDBACK_NAMES:
        from app.ai.pronunciation import feedback

        return getattr(feedback, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BLANK_RATIO_MISALIGNED",
    "FRAME_STRIDE_S",
    "QUIET_PEAK_THRESHOLD",
    "QUIET_RMS_THRESHOLD",
    "SESSION_FEEDBACK_PROMPT",
    "SYSTEM_PROMPT",
    "extract_json",
    "load_feedback_prompts",
    "strip_reasoning",
    "tok_words",
    "align_transcripts",
    "apply_forced_spans",
    "arpa_to_espeak",
    "arpa_to_ipa",
    "build_fallback_feedback",
    "calculate_overall",
    "check_audio_quality",
    "ctc_forced_align",
    "extract_f0",
    "frame_rms",
    "generate_feedback",
    "get_acoustic_model",
    "get_phone_model",
    "get_pronunciation",
    "guide_for_word",
    "heuristic_score",
    "load_wav_16k",
    "mouth_guide",
    "needleman",
    "normalize_reference",
    "observe_phones_fallback",
    "parse_confusion",
    "request_pronun_feedback",
    "score_attempt_v2",
    "score_completeness",
    "score_fluency",
    "score_local",
    "score_phones",
    "score_pronunciation",
    "score_sounds",
    "score_stress",
    "score_utterance",
    "score_via_pronun_service",
    "score_with_wav2vec2",
    "split_syllables",
    "vad_segments",
    "vi_reading",
]
