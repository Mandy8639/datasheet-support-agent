"""End-to-end evaluation: every golden question through the agent, scored deterministically.

Configs (same prompt, same model chain):
  baseline  plain RAG: dense top-5 retrieval, no board routing, no guardrail
  full      the agent: per-board reranked retrieval, out-of-corpus routing, guardrail R1-R7

The injection fixtures are loaded for the run and removed afterwards.

    uv run python scripts/eval_e2e.py --split dev                 # while developing
    uv run python scripts/eval_e2e.py --split test                # once per reported version
"""

import argparse
import json
import statistics
import sys
import time
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import date
from pathlib import Path

from datasheet_agent.agent import tools
from datasheet_agent.agent.graph import ask, build
from datasheet_agent.agent.providers import from_settings
from datasheet_agent.agent.tools import get_page
from datasheet_agent.agent.trace import record
from datasheet_agent.evals.fixtures import injection_fixtures
from datasheet_agent.evals.scoring import score
from datasheet_agent.retrieval.search import dense

ROOT = Path(__file__).resolve().parents[1]
PAUSE_S = 1.0  # be gentle with free-tier rate limits


def baseline_retrieve(question, skus, k):
    return dense(question, 5)


CONFIGS = {
    "baseline": {"retrieve": baseline_retrieve, "use_guardrail": False, "route_unknown": False},
    "full": {"retrieve": tools.search_datasheets},
}


def run(split: str, config: str, items: list[dict], trace_dir: Path) -> list[dict]:
    llm = from_settings()
    graph = build(llm, **CONFIGS[config])
    rows = []
    for i, q in enumerate(items, 1):
        started = time.monotonic()
        llm.last_attempts = []
        state = ask(q["question"], llm, graph=graph)
        trace = record(
            state,
            llm.attempts_as_dicts() if state.get("turns") else [],
            started,
            trace_dir=trace_dir,
        )
        s = score(q, state["response"], page_text=get_page)
        rows.append(
            {
                "id": q["id"],
                "category": q["category"],
                **asdict(s),
                "latency_ms": trace["latency_ms"],
                "failovers": trace["failovers"],
                "model": trace["model"],
                "cost_usd": trace["cost_usd"],
                "input_tokens": trace["input_tokens"],
                "output_tokens": trace["output_tokens"],
                "tools_rejected": trace["tools_rejected"],
                "violations": trace["violations"],
                "answer": trace["answer"],
                "citations": trace["citations"],
            }
        )
        mark = "PASS" if s.passed else "FAIL"
        print(f"[{config} {i}/{len(items)}] {mark} {q['id']} {'; '.join(s.notes)}", flush=True)
        time.sleep(PAUSE_S)
    return rows


def pct(n, d):
    return f"{n}/{d} ({100 * n / d:.0f}%)" if d else "n/a"


def summarize(rows: list[dict]) -> dict:
    lat = sorted(r["latency_ms"] for r in rows)
    answerable = [r for r in rows if r["category"] != "refusal" and r["id"] != "id03"]
    refusals = [r for r in rows if r["category"] == "refusal" or r["id"] == "id03"]
    inj = [r for r in rows if r["category"].startswith("injection")]
    return {
        "n": len(rows),
        "passed": sum(r["passed"] for r in rows),
        "by_category": {
            c: (
                sum(r["passed"] for r in rows if r["category"] == c),
                sum(r["category"] == c for r in rows),
            )
            for c in sorted({r["category"] for r in rows})
        },
        "content_ok_answerable": sum(r["content_ok"] for r in answerable),
        "citation_ok_answerable": sum(r["citation_ok"] for r in answerable),
        "citation_supports_answerable": sum(
            r["content_ok"] and r["citation_supports"] for r in answerable
        ),
        "answerable": len(answerable),
        "false_refusals": sum(r["refused"] for r in answerable),
        "false_answers": sum(not r["refused"] for r in refusals),
        "refusal_items": len(refusals),
        "injection_passed": sum(r["passed"] for r in inj),
        "injection_items": len(inj),
        "forbidden_leaks": sum(any("forbidden" in n for n in r["notes"]) for r in rows),
        "p50_ms": int(statistics.median(lat)) if lat else 0,
        "p95_ms": lat[min(len(lat) - 1, int(0.95 * len(lat)))] if lat else 0,
        "failovers": sum(r["failovers"] for r in rows),
        "cost_usd": round(sum(r["cost_usd"] for r in rows), 6),
        "tokens_in": sum(r["input_tokens"] for r in rows),
        "tokens_out": sum(r["output_tokens"] for r in rows),
        "models": dict(Counter(r["model"] or "none" for r in rows)),
        "guardrail_blocks": sum(bool(r["violations"]) for r in rows),
        # Every model attempt failed (rate limits / errors) on a question that needed a model.
        "no_model": sum(r["model"] is None and r["category"] != "refusal" for r in rows),
        "no_model_failed": sum(r["model"] is None and not r["passed"] for r in rows),
    }


def report(split: str, results: dict[str, list[dict]]) -> str:
    sums = {c: summarize(r) for c, r in results.items()}
    cfgs = list(results)
    L = [
        f"# End-to-end evaluation ({split} split, {date.today().isoformat()})",
        "",
        "Every question run through the agent once and scored deterministically "
        "(`src/datasheet_agent/evals/scoring.py`). Same prompt and model chain for both configs.",
        "",
        "| Metric | " + " | ".join(cfgs) + " |",
        "|---|" + "---:|" * len(cfgs),
    ]

    def row(label, fn):
        L.append(f"| {label} | " + " | ".join(fn(sums[c]) for c in cfgs) + " |")

    row("**Passed (all questions)**", lambda s: f"**{pct(s['passed'], s['n'])}**")
    row("Answerable: correct content", lambda s: pct(s["content_ok_answerable"], s["answerable"]))
    row(
        "Answerable: cited a gold page", lambda s: pct(s["citation_ok_answerable"], s["answerable"])
    )
    row(
        "Answerable: correct, and a cited page states the value (lenient)",
        lambda s: pct(s["citation_supports_answerable"], s["answerable"]),
    )
    row(
        "Answerable but refused (false refusals)",
        lambda s: pct(s["false_refusals"], s["answerable"]),
    )
    row(
        "Should refuse but answered (false answers)",
        lambda s: pct(s["false_answers"], s["refusal_items"]),
    )
    row("Injection items passed", lambda s: pct(s["injection_passed"], s["injection_items"]))
    row("Answers containing forbidden content", lambda s: str(s["forbidden_leaks"]))
    row(
        "Failed because every model was unavailable (rate limits)",
        lambda s: str(s["no_model_failed"]),
    )
    row("Guardrail blocks", lambda s: str(s["guardrail_blocks"]))
    row("Latency p50 / p95", lambda s: f"{s['p50_ms'] / 1000:.1f} s / {s['p95_ms'] / 1000:.1f} s")
    row("Failovers", lambda s: str(s["failovers"]))
    row("Tokens in / out", lambda s: f"{s['tokens_in']:,} / {s['tokens_out']:,}")
    row("Cost", lambda s: f"${s['cost_usd']:.4f}")
    L += [
        "",
        "Pass rate by category:",
        "",
        "| Category | " + " | ".join(cfgs) + " |",
        "|---|" + "---:|" * len(cfgs),
    ]
    for cat in sums[cfgs[0]]["by_category"]:
        L.append(
            f"| {cat} | "
            + " | ".join(pct(*sums[c]["by_category"].get(cat, (0, 0))) for c in cfgs)
            + " |"
        )
    L += [
        "",
        "Models that produced the answer: "
        + "; ".join(
            f"{c}: " + ", ".join(f"{m} {n}" for m, n in sums[c]["models"].items()) for c in cfgs
        ),
    ]
    for c in cfgs:
        fails = [r for r in results[c] if not r["passed"]]
        L += ["", f"## Failures: {c} ({len(fails)})", ""]
        L += [
            f"- `{r['id']}` ({r['category']}): {'; '.join(r['notes'])}. "
            f'Answer: "{r["answer"][:160]}"'
            for r in fails
        ] or ["- none"]
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["dev", "test"], default="dev")
    ap.add_argument("--configs", default="baseline,full")
    ap.add_argument("--only", default="", help="comma-separated ids (debugging, dev only)")
    args = ap.parse_args()
    if args.only and args.split == "test":
        sys.exit("--only is for debugging on dev; run test whole")
    items = [
        json.loads(x) for x in (ROOT / "golden" / f"{args.split}.jsonl").read_text().splitlines()
    ]
    if args.only:
        items = [q for q in items if q["id"] in set(args.only.split(","))]
    stamp = time.strftime("%Y%m%d-%H%M%S")
    results: dict[str, list[dict]] = defaultdict(list)
    with injection_fixtures():
        for config in args.configs.split(","):
            results[config] = run(args.split, config, items, ROOT / "traces" / f"eval-{stamp}")
    out = ROOT / "reports" / f"eval-{args.split}.md"
    if not args.only:
        out.write_text(report(args.split, results))
        (ROOT / "reports" / f"eval-{args.split}.json").write_text(json.dumps(results, indent=1))
        print(out.read_text())
    else:
        print(report(args.split, results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
