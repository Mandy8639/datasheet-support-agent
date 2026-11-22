"""CI quality gate: retrieval must not regress on the dev split.

Runs the shipped retriever (per_board) on dev and fails if recall@5 or MRR@10 drops more than
TOLERANCE below the committed baseline in eval/gate_baseline.json. Dev only: CI never runs
the frozen test split, so gate decisions can't leak test information into development.
No model API calls are made.

    uv run python scripts/gate.py            # check
    uv run python scripts/gate.py --update   # accept the current numbers as the new baseline
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "eval" / "gate_baseline.json"
VARIANT = "per_board"
TOLERANCE = 0.02


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--update", action="store_true")
    args = ap.parse_args()

    sys.path.insert(0, str(ROOT / "scripts"))
    import eval_retrieval as er

    ev = er.evaluate("dev", [VARIANT])
    ranks = [ev["results"][VARIANT]["ranks"][q["id"]] for q in ev["questions"]]
    r5, r10, mrr = er.metrics(ranks)
    current = {
        "split": "dev",
        "variant": VARIANT,
        "n": len(ranks),
        "recall@5": round(r5, 4),
        "recall@10": round(r10, 4),
        "mrr@10": round(mrr, 4),
    }
    print("current:", json.dumps(current))
    if args.update or not BASELINE.exists():
        BASELINE.parent.mkdir(exist_ok=True)
        BASELINE.write_text(json.dumps(current, indent=1) + "\n")
        print(f"baseline written to {BASELINE.relative_to(ROOT)}")
        return 0
    base = json.loads(BASELINE.read_text())
    print("baseline:", json.dumps(base))
    failures = [
        f"{m} {current[m]:.3f} < baseline {base[m]:.3f} - {TOLERANCE}"
        for m in ("recall@5", "mrr@10")
        if current[m] < base[m] - TOLERANCE
    ]
    if current["n"] != base["n"]:
        failures.append(f"question count changed: {current['n']} vs {base['n']}")
    for f in failures:
        print("GATE FAIL:", f)
    print("gate:", "FAIL" if failures else "PASS")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
