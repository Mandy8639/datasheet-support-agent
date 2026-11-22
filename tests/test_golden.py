"""Integrity of the golden set: split rules, no leakage into code or prompts, frozen test hash."""

import hashlib
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "golden"
FROZEN_HASH = GOLDEN / "test.sha256"
# Anything the agent reads at answer time. Prompts and few-shot examples live here (Phase 4+).
SCANNED = [ROOT / "src", ROOT / "prompts"]


def load(split: str) -> list[dict]:
    return [json.loads(line) for line in (GOLDEN / f"{split}.jsonl").read_text().splitlines()]


@pytest.fixture(scope="module")
def dev():
    return load("dev")


@pytest.fixture(scope="module")
def test():
    return load("test")


def test_ids_unique_and_splits_disjoint(dev, test):
    dev_ids, test_ids = [q["id"] for q in dev], [q["id"] for q in test]
    assert len(set(dev_ids)) == len(dev_ids)
    assert len(set(test_ids)) == len(test_ids)
    assert not set(dev_ids) & set(test_ids)
    assert {q["question"] for q in dev}.isdisjoint({q["question"] for q in test})


def test_split_field_matches_file(dev, test):
    assert all(q["split"] == "dev" for q in dev)
    assert all(q["split"] == "test" for q in test)


def test_every_answerable_question_has_gold_pages(dev, test):
    for q in dev + test:
        if q["answer"]["type"] != "refuse":
            assert q["gold"], q["id"]
            assert all(g["pages"] for g in q["gold"]), q["id"]


def _norm(s: str) -> str:
    return " ".join(s.lower().split())


def test_no_test_question_leaks_into_code_or_prompts(test):
    """Test questions must never appear in source code, prompts or few-shot examples."""
    corpus = []
    for base in SCANNED:
        if base.exists():
            corpus += [_norm(p.read_text(errors="ignore")) for p in base.rglob("*") if p.is_file()]
    text = "\n".join(corpus)
    leaked = [q["id"] for q in test if _norm(q["question"]) in text]
    assert not leaked, f"test questions found in code/prompts: {leaked}"


def test_no_test_evidence_quote_used_as_few_shot(test):
    prompts = ROOT / "prompts"
    if not prompts.exists():
        pytest.skip("no prompts yet (Phase 4)")
    text = "\n".join(_norm(p.read_text()) for p in prompts.rglob("*") if p.is_file())
    leaked = [
        q["id"]
        for q in test
        for g in q.get("gold", [])
        if _norm(g["evidence"]) in text and len(g["evidence"]) > 25
    ]
    assert not leaked, f"test evidence quoted in prompts: {leaked}"


def test_frozen_test_set_unchanged():
    if not FROZEN_HASH.exists():
        pytest.skip("test set not frozen yet (freeze after the spot-check)")
    expected = FROZEN_HASH.read_text().split()[0]
    actual = hashlib.sha256((GOLDEN / "test.jsonl").read_bytes()).hexdigest()
    assert actual == expected, "golden/test.jsonl changed after it was frozen"


def test_injection_canaries_documented():
    fixtures = json.loads((GOLDEN / "fixtures" / "injection_docs.json").read_text())
    planted = " ".join(t for d in fixtures["documents"] for t in d["pages"].values())
    for canary in ("CANARY-DOC-91", "CANARY-DOC-37"):
        assert canary in planted
    assert re.search(r"datasheet-update\.example", planted)
