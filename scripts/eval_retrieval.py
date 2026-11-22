"""Retrieval ablation on the golden set.

A question counts as retrieved at k when, for EVERY gold entry, some chunk in the top k is from
that board and covers one of its gold pages (comparisons need both boards). Its rank is the
position where the last gold entry is satisfied. Metrics: recall@5, recall@10, MRR@10.

Scored: every question with gold evidence on the real corpus. Not scored here: injection_document
(synthetic fixtures are loaded only by the end-to-end harness) and refusals with no gold page.

    uv run python scripts/eval_retrieval.py              # dev (use while developing)
    uv run python scripts/eval_retrieval.py --split test # test: once per reported version
"""

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

from datasheet_agent.retrieval.search import VARIANTS

ROOT = Path(__file__).resolve().parents[1]
K = 10


def rank_of(q: dict, hits) -> int | None:
    worst = 0
    for g in q["gold"]:
        pages = set(g["pages"])
        first = next(
            (
                i
                for i, h in enumerate(hits, 1)
                if h.sku == g["sku"] and pages & set(range(h.page_no, h.page_end + 1))
            ),
            None,
        )
        if first is None:
            return None
        worst = max(worst, first)
    return worst


def evaluate(split: str, variants: list[str] | None = None) -> dict:
    qs = [json.loads(x) for x in (ROOT / "golden" / f"{split}.jsonl").read_text().splitlines()]
    scored = [q for q in qs if q.get("gold") and q["category"] != "injection_document"]
    results = {}
    for name, fn in VARIANTS.items():
        if variants and name not in variants:
            continue
        t0 = time.time()
        per_q = {}
        for q in scored:
            per_q[q["id"]] = rank_of(q, fn(q["question"], K))
        results[name] = {"ranks": per_q, "seconds": time.time() - t0}
    return {"split": split, "n_total": len(qs), "questions": scored, "results": results}


def metrics(ranks: list[int | None]) -> tuple[float, float, float]:
    n = len(ranks)
    r5 = sum(r is not None and r <= 5 for r in ranks) / n
    r10 = sum(r is not None and r <= 10 for r in ranks) / n
    mrr = sum(1 / r for r in ranks if r is not None) / n
    return r5, r10, mrr


def report(ev: dict) -> str:
    qs = ev["questions"]
    n = len(qs)
    cats = sorted({q["category"] for q in qs})
    lines = [
        f"# Retrieval ablation ({ev['split']} split, {date.today().isoformat()})",
        "",
        f"Scored {n} of {ev['n_total']} {ev['split']} questions (those with gold pages on the real "
        "corpus; injection_document and no-gold refusals are scored end to end later).",
        "",
        "| Variant | recall@5 | recall@10 | MRR@10 | hits@5 | seconds |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, res in ev["results"].items():
        ranks = [res["ranks"][q["id"]] for q in qs]
        r5, r10, mrr = metrics(ranks)
        hits5 = sum(r is not None and r <= 5 for r in ranks)
        lines.append(
            f"| {name} | {r5:.3f} | {r10:.3f} | {mrr:.3f} | {hits5}/{n} | {res['seconds']:.1f} |"
        )
    lines += [
        "",
        "recall@5 by category:",
        "",
        "| Variant | "
        + " | ".join(f"{c} (n={sum(q['category'] == c for q in qs)})" for c in cats)
        + " |",
        "|---|" + "---:|" * len(cats),
    ]
    for name, res in ev["results"].items():
        row = []
        for c in cats:
            ranks = [res["ranks"][q["id"]] for q in qs if q["category"] == c]
            hits = sum(r is not None and r <= 5 for r in ranks)
            row.append(f"{hits}/{len(ranks)}")
        lines.append(f"| {name} | " + " | ".join(row) + " |")
    last = list(ev["results"])[-1]
    misses = [q for q in qs if (ev["results"][last]["ranks"][q["id"]] or 99) > 5]
    lines += ["", f"Misses at k=5 for `{last}` ({len(misses)}):", ""]
    lines += [f"- `{q['id']}` {q['question']}" for q in misses] or ["- none"]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["dev", "test"], default="dev")
    ap.add_argument("--variants", default="", help="comma-separated subset (CI gate)")
    args = ap.parse_args()
    ev = evaluate(args.split, [v for v in args.variants.split(",") if v] or None)
    out = ROOT / "reports" / f"retrieval-{args.split}.md"
    out.write_text(report(ev))
    raw = {k: v["ranks"] for k, v in ev["results"].items()}
    (ROOT / "reports" / f"retrieval-{args.split}.json").write_text(json.dumps(raw, indent=1) + "\n")
    print(out.read_text())
    return 0


if __name__ == "__main__":
    sys.exit(main())
