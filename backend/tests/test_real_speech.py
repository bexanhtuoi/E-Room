"""Quick test: download one real speech sample and check forced alignment"""
import asyncio
import sys
from pathlib import Path

import numpy as np
from datasets import load_dataset

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.infrastructure.audio_wav2vec2 import Wav2Vec2PhonemeModel


async def main():
    print("Downloading sample...")
    ds = load_dataset(
        "hf-internal-testing/librispeech_asr_dummy",
        "clean",
        split="validation",
        streaming=True,
    )
    sample = next(iter(ds.take(1)))
    audio = np.array(sample["audio"]["array"], dtype=np.float32)
    sr = sample["audio"]["sampling_rate"]
    text = sample["text"]
    print(f"Text: {text!r}")
    print(f"Duration: {len(audio)/sr:.2f}s")

    w2v = Wav2Vec2PhonemeModel()
    result = w2v.process(audio, sr)
    print(f"Greedy: {result['greedy_text']!r}")

    char_ids = w2v.text_to_token_ids(text)
    print(f"Token IDs: {char_ids}")
    print(f"Decoded: {[w2v.processor.tokenizer.decode([i]) for i in char_ids]}")

    aligned = w2v.forced_align_viterbi(result["log_probs"], char_ids)
    print(f"\nAligned items: {len(aligned)}")
    for a in aligned[:10]:
        token_text = w2v.processor.tokenizer.decode([a["token_id"]])
        print(f"  '{token_text}' id={a['token_id']:2d} frames={a['start_frame']:3d}-{a['end_frame']:3d}  conf={a['confidence']:.3f}")

    # Also run full pipeline
    from app.infrastructure.audio_pipeline import PronunciationPipeline
    pipe = PronunciationPipeline()
    pipe_result = await pipe.assess(audio, sr)
    print(f"\nPipeline text: {pipe_result['text']!r}")
    print(f"Scores: {pipe_result['scores']}")
    print(f"Alignments: {len(pipe_result['aligned_phonemes'])}")


asyncio.run(main())
