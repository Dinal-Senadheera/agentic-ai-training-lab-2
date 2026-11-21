"""Embedding backends. Every backend returns L2-normalised float32 vectors."""
import hashlib
import json
import math
import re
from collections import Counter

import numpy as np

from labkit import config

_model = None


def _cache_path(kind: str):
    """One cache file per embedding model and corpus kind."""
    config.CACHE.mkdir(exist_ok=True)
    key = hashlib.sha1(f"{config.EMBEDDING_BACKEND}|{config.EMBEDDING_MODEL}|{kind}".encode()).hexdigest()[:12]
    return config.CACHE / f"emb_{key}.json"


def _normalise(m: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(m, axis=1, keepdims=True)
    n[n == 0] = 1
    return (m / n).astype(np.float32)


def _sentence_transformers(texts: list[str]) -> np.ndarray:
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(config.EMBEDDING_MODEL)
    return _normalise(np.asarray(_model.encode(texts, batch_size=32, show_progress_bar=False)))


# ---- stand-in: hashed word and character n-gram TF-IDF. Lexical, not semantic. ----
_DIM = 4096
_df: Counter | None = None
_n_docs = 0


def _features(text: str) -> Counter:
    text = text.lower()
    words = re.findall(r"[a-z0-9][a-z0-9\-\.]*", text)
    feats = Counter(words)
    for w in words:
        padded = f" {w} "
        for i in range(len(padded) - 3):
            feats["#" + padded[i:i + 4]] += 0.3
    return feats


def _stand_in(texts: list[str], fit: bool) -> np.ndarray:
    global _df, _n_docs
    feats = [_features(t) for t in texts]
    if fit or _df is None:
        _df = Counter(k for f in feats for k in f)
        _n_docs = len(texts)
    m = np.zeros((len(texts), _DIM), dtype=np.float32)
    for i, f in enumerate(feats):
        for k, v in f.items():
            idf = math.log((1 + _n_docs) / (1 + _df.get(k, 0))) + 1
            m[i, int(hashlib.md5(k.encode()).hexdigest(), 16) % _DIM] += (1 + math.log(v)) * idf if v >= 1 else v * idf
    return _normalise(m)


def embed_documents(texts: list[str]) -> np.ndarray:
    if config.EMBEDDING_BACKEND == "stand-in":
        return _stand_in(texts, fit=True)
    path = _cache_path("docs")
    cache = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    missing = [t for t in texts if hashlib.sha1(t.encode()).hexdigest() not in cache]
    if missing:
        vecs = _sentence_transformers(missing)
        for t, v in zip(missing, vecs):
            cache[hashlib.sha1(t.encode()).hexdigest()] = v.tolist()
        path.write_text(json.dumps(cache), encoding="utf-8")
    return np.asarray([cache[hashlib.sha1(t.encode()).hexdigest()] for t in texts], dtype=np.float32)


def embed_queries(texts: list[str]) -> np.ndarray:
    if config.EMBEDDING_BACKEND == "stand-in":
        return _stand_in(texts, fit=False)
    return _sentence_transformers([config.QUERY_PREFIX + t for t in texts])
