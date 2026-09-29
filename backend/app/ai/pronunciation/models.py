import glob
import json
import os
import threading
from pathlib import Path

from app.config import settings
from app.log import get_logger

log = get_logger("app.ai.pronunciation.models")


ARPA_TO_ESPEAK: dict[str, tuple[str, ...]] = {
    "AA": ("ɑ",), "AE": ("æ",), "AH": ("ʌ",), "AO": ("ɔ",),
    "AW": ("aʊ",), "AY": ("aɪ",),
    "EH": ("ɛ",), "ER": ("ɜ", "ɹ"), "EY": ("eɪ",),
    "IH": ("ɪ",), "IY": ("i",),
    "OW": ("oʊ",), "OY": ("ɔɪ",), "UH": ("ʊ",), "UW": ("u",),
    "P": ("p",), "B": ("b",), "T": ("t",), "D": ("d",),
    "K": ("k",), "G": ("ɡ",),
    "F": ("f",), "V": ("v",), "TH": ("θ",), "DH": ("ð",),
    "S": ("s",), "Z": ("z",), "SH": ("ʃ",), "ZH": ("ʒ",),
    "HH": ("h",), "M": ("m",), "N": ("n",), "NG": ("ŋ",),
    "L": ("l",), "R": ("ɹ",), "W": ("w",), "Y": ("j",),
    "CH": ("tʃ",), "JH": ("dʒ",),
}


acoustic_lock = threading.Lock()
ctc_processor = None
acoustic_model = None
torch_lib = None


def load_torch():
    global torch_lib
    if torch_lib is None:
        import torch

        torch_lib = torch
    return torch_lib


def acoustic_model_id() -> str:
    try:
        return settings.wav2vec_model_id or "facebook/wav2vec2-base-960h"
    except Exception:
        return "facebook/wav2vec2-base-960h"


def get_acoustic_model():
    global ctc_processor, acoustic_model
    if acoustic_model is not None:
        return ctc_processor, acoustic_model
    with acoustic_lock:
        if acoustic_model is not None:
            return ctc_processor, acoustic_model
        torch = load_torch()
        from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

        mid = acoustic_model_id()
        ctc_processor = Wav2Vec2Processor.from_pretrained(mid)
        acoustic_model = Wav2Vec2ForCTC.from_pretrained(mid)
        acoustic_model.eval()
        if torch.cuda.is_available():
            acoustic_model.to("cuda")
    return ctc_processor, acoustic_model


def phone_model_id() -> str:
    try:
        return settings.phoneme_model_id or "facebook/wav2vec2-xlsr-53-espeak-cv-ft"
    except Exception:
        return os.getenv("PHONEME_MODEL_ID", "facebook/wav2vec2-xlsr-53-espeak-cv-ft")


PHONE_MODEL_ID = phone_model_id()


phone_lock = threading.Lock()
phone_fe = None
phone_model = None
phone_vocab: dict[str, int] | None = None


def load_vocab() -> dict[str, int]:
    global phone_vocab
    if phone_vocab is not None:
        return phone_vocab
    pats = [
        str(Path.home() / ".cache" / "huggingface" / "hub" /
            ("models--" + PHONE_MODEL_ID.replace("/", "--")) / "snapshots" / "*" / "vocab.json"),
    ]
    found = [f for p in pats for f in glob.glob(p)]
    if not found:
        # ép download vocab (nhẹ, vài KB)
        from huggingface_hub import hf_hub_download
        fp = hf_hub_download(PHONE_MODEL_ID, "vocab.json")
        found = [fp]
    with open(found[0], encoding="utf-8") as f:
        phone_vocab = json.load(f)
    return phone_vocab


def get_phone_model():
    global phone_fe, phone_model
    if phone_model is not None:
        return phone_fe, phone_model
    with phone_lock:
        if phone_model is not None:
            return phone_fe, phone_model
        torch = load_torch()
        from transformers import AutoFeatureExtractor, Wav2Vec2ForCTC
        phone_fe = AutoFeatureExtractor.from_pretrained(PHONE_MODEL_ID)
        phone_model = Wav2Vec2ForCTC.from_pretrained(PHONE_MODEL_ID)
        phone_model.eval()
        if torch.cuda.is_available():
            phone_model.to("cuda")
        load_vocab()
    return phone_fe, phone_model


def arpa_to_espeak(arpa: list[str]) -> tuple[list[str], list[int]]:
    vocab = load_vocab()
    toks: list[str] = []
    back: list[int] = []
    for i, ph in enumerate(arpa):
        base = ph.rstrip("012")
        for t in ARPA_TO_ESPEAK.get(base, ()):
            if t in vocab:
                toks.append(t)
                back.append(i)
    return toks, back


def ctc_forced_align(log_probs, target_ids: list[int], blank_id: int):
    torch = load_torch()
    T = log_probs.shape[0]
    L = len(target_ids)
    if L == 0 or T == 0:
        return [0] * T, float("-inf")
    ext = [blank_id]
    for tid in target_ids:
        ext.append(int(tid))
        ext.append(blank_id)
    S = len(ext)
    NEG = -1e9
    ext_t = torch.tensor(ext, dtype=torch.long)
    lp = log_probs[:, ext_t]  # [T, S]
    trellis = torch.full((T, S), NEG)
    choice = torch.zeros((T, S), dtype=torch.long)  # 0=stay, 1=+1, 2=+2
    trellis[0, 0] = lp[0, 0]
    if S > 1:
        trellis[0, 1] = lp[0, 1]
    skip_ok = torch.zeros(S, dtype=torch.bool)
    for s in range(2, S):
        if ext[s] != blank_id and ext[s] != ext[s - 2]:
            skip_ok[s] = True
    neg_col = torch.full((S,), NEG)
    for t in range(1, T):
        prev = trellis[t - 1]
        stay = prev
        plus1 = torch.cat([neg_col[:1], prev[:-1]])
        if skip_ok.any():
            plus2 = torch.cat([neg_col[:2], prev[:-2]])
            plus2 = torch.where(skip_ok, plus2, neg_col)
            cand = torch.stack([stay, plus1, plus2], dim=0)
        else:
            cand = torch.stack([stay, plus1], dim=0)
        best, idx = cand.max(dim=0)
        trellis[t] = best + lp[t]
        choice[t] = idx
    last = S - 1
    if S > 1 and trellis[T - 1, S - 2] > trellis[T - 1, S - 1]:
        last = S - 2
    align = [0] * T
    s = last
    for t in range(T - 1, -1, -1):
        align[t] = s
        if t > 0:
            c = int(choice[t, s])
            s = s if c == 0 else (s - 1 if c == 1 else s - 2)
    return align, float(trellis[T - 1, last])


FRAME_STRIDE_S = 0.02  # wav2vec2 downsample 320x @16kHz ~= 20ms/frame


BLANK_RATIO_MISALIGNED = 0.70  # blank >70% word span -> misalignment, không phải lỗi phát âm

