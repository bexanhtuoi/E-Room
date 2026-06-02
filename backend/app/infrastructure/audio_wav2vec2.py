from __future__ import annotations

from typing import Any

import torch
import torch.nn.functional as F
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

from app.log import get_logger

logger = get_logger(__name__)

processor = Wav2Vec2Processor.from_pretrained("facebook/wav2vec2-base-960h")
model = Wav2Vec2ForCTC.from_pretrained("facebook/wav2vec2-base-960h")
model.eval()

logger.info("Đã tải mô hình Wav2Vec2", extra={"model": "wav2vec2-base-960h"})


class Aligner:
    def __init__(self) -> None:
        pass

    def align(self, audio: bytes, text: str) -> list[dict[str, Any]] | None:
        import io

        import soundfile as sf

        try:
            audio_io = io.BytesIO(audio)
            waveform, sr = sf.read(audio_io)
            if sr != 16000:
                import numpy as np

                import librosa

                waveform = librosa.resample(waveform, orig_sr=sr, target_sr=16000)
        except Exception:
            try:
                import numpy as np

                waveform = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0
            except Exception:
                return None

        inputs = processor(
            waveform,
            sampling_rate=16000,
            return_tensors="pt",
            padding=True,
        )
        with torch.no_grad():
            logits = model(inputs.input_values).logits[0]

        emission = F.softmax(logits, dim=-1)
        predicted_ids = torch.argmax(emission, dim=-1)
        predicted_chars = processor.tokenizer.decode(predicted_ids.tolist())

        if not predicted_chars.strip():
            return None

        trellis = self._build_trellis(emission, text.lower())
        if trellis is None:
            return None

        segments = self._backtrack(trellis, emission)
        return segments

    def _build_trellis(self, emission: torch.Tensor, text: str) -> Any | None:
        try:
            tokens = processor.tokenizer(text.lower(), return_tensors="pt", padding=True).input_ids[0]
        except Exception:
            return None

        T, C = emission.shape
        N = len(tokens)

        trellis = torch.zeros((N, T))
        for t in range(T):
            trellis[0, t] = emission[t, tokens[0]]
        for n in range(1, N):
            trellis[n, 0] = 0
            for t in range(1, T):
                trellis[n, t] = max(
                    trellis[n - 1, t - 1],
                    trellis[n, t - 1],
                ) + emission[t, tokens[n]]

        if trellis[N - 1, T - 1] == 0:
            return None
        return trellis

    def _backtrack(self, trellis: torch.Tensor, emission: torch.Tensor) -> list[dict[str, Any]]:
        T, C = emission.shape
        N = trellis.shape[0]

        tokens = []
        n, t = N - 1, T - 1
        while n > 0 and t > 0:
            if trellis[n, t] == trellis[n, t - 1]:
                t -= 1
            elif trellis[n, t] == trellis[n - 1, t - 1] + emission[t, tokens[n]]:
                tokens.append((n, t))
                n -= 1
                t -= 1
            else:
                tokens.append((n, t))
                break

        tokens.reverse()
        segments = []
        for n, t in tokens:
            confidence = float(torch.sigmoid(emission[t, tokens[n]]))
            segments.append({
                "start": t * 0.02,
                "end": (t + 1) * 0.02,
                "char": tokens[n],
                "confidence": confidence,
            })
        return segments


aligner_model = Aligner()
