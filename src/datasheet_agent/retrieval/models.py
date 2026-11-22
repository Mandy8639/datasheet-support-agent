"""Local embedding and reranking models (no API calls, $0).

bge-small-en-v1.5 expects a short instruction in front of queries, not passages.
"""

from functools import cache

import numpy as np

EMBED_MODEL = "BAAI/bge-small-en-v1.5"  # 384-d
RERANK_MODEL = "BAAI/bge-reranker-base"  # cross-encoder
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


@cache
def embedder():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBED_MODEL)


@cache
def reranker():
    from sentence_transformers import CrossEncoder

    return CrossEncoder(RERANK_MODEL)


def embed_passages(texts: list[str]) -> np.ndarray:
    return embedder().encode(texts, normalize_embeddings=True, batch_size=32)


def embed_query(text: str) -> np.ndarray:
    return embedder().encode(QUERY_PREFIX + text, normalize_embeddings=True)


def rerank_scores(query: str, passages: list[str]) -> list[float]:
    if not passages:
        return []
    return [float(s) for s in reranker().predict([(query, p) for p in passages])]
