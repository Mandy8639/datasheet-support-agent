"""Retrievers over chunks. All use the read-only agent connection.

Variants compared in the ablation (one change per step):
  fts        Postgres full-text search (OR of query terms, ts_rank_cd)
  dense      bge-small cosine similarity (pgvector)
  hybrid     reciprocal rank fusion of fts + dense
  rerank     hybrid candidates re-scored by a cross-encoder
  filtered   rerank, restricted to the boards named in the question
  per_board  filtered, but a question naming several boards is decomposed: one sub-search
             per board, with the board names removed from the sub-query (the filter already
             fixes the board), results interleaved so one board can't crowd out another
"""

import math
from dataclasses import dataclass

from datasheet_agent.db import agent_conn
from datasheet_agent.retrieval.models import embed_query, rerank_scores
from datasheet_agent.retrieval.query import strip_boards, understand

RRF_K = 60
CANDIDATES = 40  # per retriever, before fusion / reranking


@dataclass
class Hit:
    chunk_id: int
    sku: str
    page_no: int
    page_end: int
    kind: str
    section: str
    text: str
    search_text: str
    score: float


_COLS = "c.id, d.sku, c.page_no, c.page_end, c.kind, c.section, c.text, c.search_text"


def _rows_to_hits(rows) -> list[Hit]:
    return [Hit(*r[:8], score=float(r[8])) for r in rows]


def _sku_clause(skus: list[str] | None) -> tuple[str, list]:
    if not skus:
        return "", []
    return " AND d.sku = ANY(%s)", [skus]


def fts(query: str, k: int, skus: list[str] | None = None) -> list[Hit]:
    clause, params = _sku_clause(skus)
    sql = f"""
        WITH q AS (
          SELECT to_tsquery('english', string_agg(lexeme, ' | ')) AS tsq
          FROM unnest(to_tsvector('english', %s)) )
        SELECT {_COLS}, ts_rank_cd(c.tsv, q.tsq) AS score
        FROM chunks c JOIN documents d ON d.id = c.doc_id, q
        WHERE q.tsq IS NOT NULL AND c.tsv @@ q.tsq {clause}
        ORDER BY score DESC, c.id LIMIT %s"""
    with agent_conn() as conn:
        return _rows_to_hits(conn.execute(sql, [query, *params, k]).fetchall())


def dense(query: str, k: int, skus: list[str] | None = None) -> list[Hit]:
    clause, params = _sku_clause(skus)
    vec = "[" + ",".join(f"{x:.6f}" for x in embed_query(query)) + "]"
    sql = f"""
        SELECT {_COLS}, 1 - (c.embedding <=> %s::vector) AS score
        FROM chunks c JOIN documents d ON d.id = c.doc_id
        WHERE c.embedding IS NOT NULL {clause}
        ORDER BY c.embedding <=> %s::vector, c.id LIMIT %s"""
    with agent_conn() as conn:
        return _rows_to_hits(conn.execute(sql, [vec, *params, vec, k]).fetchall())


def hybrid(query: str, k: int, skus: list[str] | None = None) -> list[Hit]:
    lists = [fts(query, CANDIDATES, skus), dense(query, CANDIDATES, skus)]
    fused: dict[int, Hit] = {}
    scores: dict[int, float] = {}
    for hits in lists:
        for rank, h in enumerate(hits, start=1):
            fused.setdefault(h.chunk_id, h)
            scores[h.chunk_id] = scores.get(h.chunk_id, 0.0) + 1.0 / (RRF_K + rank)
    ordered = sorted(fused.values(), key=lambda h: (-scores[h.chunk_id], h.chunk_id))
    for h in ordered:
        h.score = scores[h.chunk_id]
    return ordered[:k]


def rerank(query: str, k: int, skus: list[str] | None = None) -> list[Hit]:
    candidates = hybrid(query, CANDIDATES, skus)
    scores = rerank_scores(query, [c.search_text for c in candidates])
    for h, s in zip(candidates, scores, strict=True):
        h.score = s
    return sorted(candidates, key=lambda h: (-h.score, h.chunk_id))[:k]


def filtered(query: str, k: int, extra_aliases: tuple = ()) -> list[Hit]:
    skus = understand(query, extra_aliases).skus or None
    return rerank(query, k, skus)


def per_board(query: str, k: int, extra_aliases: tuple = ()) -> list[Hit]:
    skus = understand(query, extra_aliases).skus
    if len(skus) < 2:
        return rerank(query, k, skus or None)
    per = math.ceil(k / len(skus))
    sub_query = strip_boards(query, extra_aliases)
    lists = [rerank(sub_query, per, [sku]) for sku in skus]
    out: list[Hit] = []
    for i in range(per):
        out += [hits[i] for hits in lists if i < len(hits)]
    return out[:k]


VARIANTS = {
    "fts": fts,
    "dense": dense,
    "hybrid": hybrid,
    "rerank": rerank,
    "filtered": lambda q, k: filtered(q, k),
    "per_board": lambda q, k: per_board(q, k),
}
