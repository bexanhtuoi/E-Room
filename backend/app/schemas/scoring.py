"""Data contract B1-B4 — deterministic scorer dùng chung cho demo + backend sau này."""
from __future__ import annotations
from datetime import datetime
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field

Mode = Literal["read_aloud", "free_speaking"]
AttemptStatus = Literal["recorded", "scoring", "scored", "feedback_generating", "completed", "failed"]
Accent = Literal["en-US", "en-GB"]


class SpeakingAttempt(BaseModel):
    id: str
    user_id: str = "local"
    mode: Mode = "free_speaking"
    original_text: Optional[str] = None
    whisper_raw: str = ""
    user_corrected: str = ""
    audio_url: str = ""
    duration_sec: float = 0.0
    reference_accent: Accent = "en-US"
    reference_voice_id: str = "af_heart"
    reference_speed: float = 0.9
    status: AttemptStatus = "recorded"
    scorer_version: str = "scorer-v2-mvp"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class WhisperWord(BaseModel):
    index: int
    text: str
    start_s: float
    end_s: float
    confidence: Optional[float] = None


class AlignedWord(BaseModel):
    word: str  # từ trong user_corrected
    source_word: Optional[str] = None  # từ whisper gốc (None nếu insertion)
    start_s: Optional[float] = None
    end_s: Optional[float] = None
    alignment: Literal["match", "substitution", "insertion", "deletion"] = "match"
    span_available: bool = True
    ignored_for_pronunciation: bool = False


class Scores(BaseModel):
    sounds: float = 0.0
    stress: float = 0.0
    fluency: float = 0.0
    completeness: float = 0.0
    intonation: Optional[float] = None  # v1.1, MVP để None hoặc monotone-only
    overall: float = 0.0


class TextInfo(BaseModel):
    original: Optional[str] = None
    whisper_raw: str = ""
    user_corrected: str = ""


class ReferenceInfo(BaseModel):
    accent: Accent = "en-US"
    voice_id: str = "af_heart"
    speed: float = 0.9
    audio_url: Optional[str] = None
    cached: bool = False


class WordDetail(BaseModel):
    word: str
    score: float
    status: str = "ok"  # ok | pronunciation_error | missing_span
    start_s: Optional[float] = None
    end_s: Optional[float] = None
    acoustic_confidence: Optional[float] = None
    expected_ipa: Optional[str] = None


class PhonemeDetail(BaseModel):
    word: str
    expected: str  # IPA, vd /θ/
    observed: Optional[str] = None  # IPA từ phone recognizer, None nếu chưa có model
    type: str = "unknown"  # match | substitution | deletion | insertion | unknown
    gop: Optional[float] = None  # true GOP khi có phoneme model, None = fallback char-level
    score: float = 0.0


class StressDetail(BaseModel):
    word: str
    expected_stress: Optional[int] = None  # index syllable CMU mark 1
    detected_stress: Optional[int] = None
    correct: Optional[bool] = None
    reason: str = ""


class IntonationDetail(BaseModel):
    median_f0: float = 0.0
    std_f0: float = 0.0
    range_f0: float = 0.0
    final_slope: float = 0.0
    monotone: bool = False
    note: str = "MVP: monotone detection only, DTW vs Kokoro deferred to v1.1"


class FluencyDetail(BaseModel):
    wpm: float = 0.0
    articulation_rate: float = 0.0
    pause_ratio: float = 0.0
    long_pause_count: int = 0
    hesitation_count: int = 0
    repetition_count: int = 0
    score: float = 0.0


class CompletenessDetail(BaseModel):
    mode: Mode = "free_speaking"
    missing_words: list[str] = []
    extra_words: list[str] = []
    wer_vs_original: Optional[float] = None
    score: float = 100.0


class ErrorDetail(BaseModel):
    pattern: str  # vd "/θ/ → /s/"
    count: int = 1
    examples: list[str] = []


class ScoringReport(BaseModel):
    scores: Scores
    texts: TextInfo
    reference: ReferenceInfo
    word_details: list[WordDetail] = []
    phonemes: list[PhonemeDetail] = []
    stress_detail: list[StressDetail] = []
    intonation: IntonationDetail = IntonationDetail()
    fluency: FluencyDetail = FluencyDetail()
    completeness: CompletenessDetail = CompletenessDetail()
    top_errors: list[ErrorDetail] = []
    scorer_version: str = "scorer-v2-mvp"
    warnings: list[str] = []


class PriorityError(BaseModel):
    word: str
    issue: str
    advice: str = ""


class FeedbackResult(BaseModel):
    summary: str = ""
    pronunciation_feedback: str = ""
    stress_feedback: str = ""
    intonation_feedback: str = ""
    fluency_feedback: str = ""
    priority_errors: list[PriorityError] = []
    practice_plan: list[str] = []
