from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from app.infrastructure.audio_dictionary import CMUDictionary
from app.infrastructure.audio_whisper import whisper_model
from app.infrastructure.audio_wav2vec2 import aligner_model
from app.infrastructure.phoneme_compare import PhonemeComparator
from app.log import get_logger

logger = get_logger(__name__)

_EXECUTOR = ThreadPoolExecutor(max_workers=4)


class PronunciationPipeline:
    def __init__(self) -> None:
        self._dictionary = CMUDictionary()
        self._comparator = PhonemeComparator()

    async def assess(self, pcm_data: bytes) -> dict[str, Any]:
        _t0 = time.monotonic()
        logger.info("Bắt đầu pipeline đánh giá phát âm",
            extra={"pcm_bytes": len(pcm_data)})

        segments, info = await whisper_model.transcribe(pcm_data)
        elapsed_whisper = round(time.monotonic() - _t0, 2)
        logger.info("Whisper hoàn tất",
            extra={"segments": len(segments), "duration_s": round(info.duration, 2) if info.duration else 0, "elapsed_s": elapsed_whisper})

        text = " ".join(s.text.strip() for s in segments if s.text).strip()
        words = text.split() if text else []

        wav2vec_start = time.monotonic()
        alignment = aligner_model.align(pcm_data, text) if text else None
        elapsed_wav2vec = round(time.monotonic() - wav2vec_start, 2)
        logger.info("Wav2Vec2 hoàn tất",
            extra={"alignment_frames": len(alignment) if alignment else 0, "elapsed_s": elapsed_wav2vec})

        elapsed_dict = round(time.monotonic() - _t0, 2)
        logger.info("Tra từ điển CMU",
            extra={"word_count": len(words), "elapsed_s": elapsed_dict})

        aligned: list[dict[str, Any]] = []
        if words and alignment:
            logger.info("Bắt đầu căn chỉnh âm vị",
                extra={"word_count": len(words), "alignment_frames": len(alignment)})
            aligned = self._build_word_phoneme_context(words, alignment)
            elapsed_alignment = round(time.monotonic() - _t0, 2)
            logger.info("Căn chỉnh âm vị hoàn tất",
                extra={"aligned_count": len(aligned), "elapsed_s": elapsed_alignment})
        else:
            logger.info("Bỏ qua căn chỉnh âm vị (không có text hoặc alignment)",
                extra={"has_text": bool(words), "has_alignment": alignment is not None})

        word_scores: list[dict[str, Any]] = []
        total_confidence = 0.0
        word_count = 0
        for w in aligned:
            pron = w.get("pronunciation", "")
            score = min(w.get("confidence", 0.5) * 100, 100)
            total_confidence += score
            word_count += 1
            word_scores.append({
                "word": w["word"],
                "score": round(score, 1),
                "pronunciation": pron,
                "phonemes": w.get("phonemes", []),
                "duration": round(w.get("duration", 0), 3),
            })

        overall = round(total_confidence / max(word_count, 1), 1)
        needs_remediation = overall < 70
        total_elapsed = round(time.monotonic() - _t0, 2)
        logger.info("Kết thúc pipeline đánh giá phát âm",
            extra={
                "overall_score": overall,
                "needs_remediation": needs_remediation,
                "words_assessed": word_count,
                "total_s": total_elapsed,
                "transcribe_s": elapsed_whisper,
            })

        return {
            "text": text,
            "scores": {"overall": overall},
            "needs_remediation": needs_remediation,
            "words": word_scores,
            "aligned_phonemes": aligned,
            "timing": {
                "transcribe_s": elapsed_whisper,
                "total_s": total_elapsed,
            },
        }

    def _build_word_phoneme_context(
        self, words: list[str], alignment: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        import itertools

        word_letters_lists: list[list[dict[str, Any]]] = []
        word_boundaries: list[int] = []
        offset = 0

        for word in words:
            letters: list[dict[str, Any]] = []
            for ch in word.lower():
                if offset < len(alignment):
                    letters.append(alignment[offset])
                    offset += 1
            if letters:
                word_letters_lists.append(letters)
                word_boundaries.append(len(letters))

        merged = []
        for i, word in enumerate(words):
            letter_data = word_letters_lists[i] if i < len(word_letters_lists) else []
            confidence = (
                sum(ch.get("confidence", 0.5) for ch in letter_data) / max(len(letter_data), 1)
                if letter_data
                else 0.5
            )
            start = letter_data[0]["start"] if letter_data else 0.0
            end = letter_data[-1]["end"] if letter_data else 0.0
            phones = self._dictionary.lookup(word.lower())
            merged.append({
                "word": word,
                "confidence": round(confidence, 3),
                "start": start,
                "end": end,
                "duration": round(end - start, 3),
                "phonemes": phones,
                "pronunciation": " ".join(phones) if phones else "",
            })

        return merged
