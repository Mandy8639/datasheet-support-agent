"""The retrieval metric: every gold entry must be covered; rank is where the last one is met."""

import importlib.util
from pathlib import Path

from datasheet_agent.retrieval.search import Hit

spec = importlib.util.spec_from_file_location(
    "eval_retrieval", Path(__file__).resolve().parents[1] / "scripts" / "eval_retrieval.py"
)
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)


def hit(sku, page, page_end=None):
    return Hit(0, sku, page, page_end or page, "text", "", "", "", 0.0)


def test_single_gold_rank():
    q = {"gold": [{"sku": "A", "pages": [7]}]}
    assert ev.rank_of(q, [hit("A", 2), hit("B", 7), hit("A", 7)]) == 3


def test_chunk_spanning_pages_counts():
    q = {"gold": [{"sku": "A", "pages": [5]}]}
    assert ev.rank_of(q, [hit("A", 4, 6)]) == 1


def test_comparison_needs_both_boards():
    q = {"gold": [{"sku": "A", "pages": [7]}, {"sku": "B", "pages": [3]}]}
    assert ev.rank_of(q, [hit("A", 7), hit("A", 1)]) is None
    assert ev.rank_of(q, [hit("A", 7), hit("C", 3), hit("B", 3)]) == 3


def test_metrics():
    assert ev.metrics([1, 2, None, 6]) == (0.5, 0.75, (1 + 0.5 + 1 / 6) / 4)
