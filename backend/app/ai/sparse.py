import math
from collections import Counter
from qdrant_client.models import SparseVector


def text_to_sparse(text: str, vocab_bits: int = 24) -> SparseVector:
    tokens = text.lower().split()
    tf = Counter(tokens)
    max_idx = 2 ** vocab_bits
    indices = [abs(hash(t)) % max_idx for t in tf.keys()]
    values = [math.log(1 + f) for f in tf.values()]
    return SparseVector(indices=indices, values=values)
