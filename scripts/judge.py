"""Validate the LLM judge against human labels, then report its agreement.

    uv run python scripts/judge.py sheet  # golden/judge_labels_dev.md from reports/eval-dev.json
    uv run python scripts/judge.py score  # run the judge; compare with human + deterministic

The sheet lists the 30 answerable dev answers from the full config (spec, condition,
comparison, text, pin). The human marks each correct / incorrect; labels are stored in
golden/judge_labels_dev.json. Dev only: the judge is validated before it is trusted.
"""

import json
import sys
import time
from pathlib import Path

from datasheet_agent.agent.providers import SpendTracker
from datasheet_agent.config import get_settings
from datasheet_agent.evals.judge import Judge, Verdict, expected_text

ROOT = Path(__file__).resolve().parents[1]
CATS = ["spec_number", "spec_condition", "comparison", "text_fact", "pin"]
LABELS = ROOT / "golden" / "judge_labels_dev.json"
PAUSE_S = 4.0  # free-tier rate limits
SHEET = ROOT / "golden" / "judge_labels_dev.md"
# Judge order: start with a model that is last in the answering chain, to limit self-grading.
JUDGE_MODELS = [
    "nvidia/nemotron-3.5-super-vl:free",
    "baidu/ernie-5.5-flash-preview:free",
    "particle-ai/particle-1:free",
]


def items_and_answers():
    dev = {
        json.loads(x)["id"]: json.loads(x)
        for x in (ROOT / "golden" / "dev.jsonl").read_text().splitlines()
    }
    # The judge was validated on the v1 dev answers; keep reading those.
    full = json.loads((ROOT / "reports" / "eval-dev-v1.json").read_text())["full"]
    rows = [r for r in full if r["category"] in CATS]
    return [(dev[r["id"]], r) for r in rows]


def sheet() -> None:
    pairs = items_and_answers()
    L = [
        "# Judge validation: label 30 answers",
        "",
        "For each answer, decide whether it is **correct** (states the expected fact, no wrong "
        "figure) or **incorrect**. Ignore style. Reply in chat with the numbers you think are "
        'incorrect, e.g. "incorrect: 4, 17"; everything else is taken as correct.',
        "",
    ]
    for i, (q, r) in enumerate(pairs, 1):
        quote = "; ".join(f'{g["sku"]} p.{g["pages"]}: "{g["evidence"]}"' for g in q["gold"])
        L += [
            f"## {i}. `{q['id']}`",
            "",
            f"**Q:** {q['question']}",
            "",
            f"**Expected:** {expected_text(q['answer'])}  ",
            f"**Datasheet:** {quote}",
            "",
            f"**Agent answered:** {r['answer']}",
            "",
        ]
    SHEET.write_text("\n".join(L))
    print(f"wrote {SHEET.relative_to(ROOT)} ({len(pairs)} answers)")


def score() -> None:
    if not LABELS.exists():
        sys.exit("no human labels yet: golden/judge_labels_dev.json")
    human = json.loads(LABELS.read_text())["labels"]  # id -> true/false
    s = get_settings()
    judge = Judge(s.openrouter_api_key.strip(), JUDGE_MODELS, SpendTracker(s.daily_spend_cap_usd))
    # Keep verdicts from an earlier run; only grade answers the judge couldn't reach (rate limits).
    out_path = ROOT / "reports" / "judge-validation-dev.json"
    previous = {}
    if out_path.exists():
        previous = {
            r["id"]: r for r in json.loads(out_path.read_text())["rows"] if r["judge"] is not None
        }
    rows, agree_h, agree_d, n = [], 0, 0, 0
    for q, r in items_and_answers():
        if q["id"] in previous:
            p = previous[q["id"]]
            v = Verdict(p["judge"], p["reason"], p["judge_model"])
        else:
            v = judge.grade(q, r["answer"])
            time.sleep(PAUSE_S)
        h, d = human[q["id"]], r["passed"]
        if v.correct is not None:
            n += 1
            agree_h += v.correct == h
            agree_d += v.correct == d
        rows.append(
            {
                "id": q["id"],
                "human": h,
                "deterministic": d,
                "judge": v.correct,
                "judge_model": v.model,
                "reason": v.reason,
            }
        )
    det_vs_h = sum(r["human"] == r["deterministic"] for r in rows)
    out = {
        "n": len(rows),
        "judged": n,
        "judge_agrees_with_human": agree_h,
        "judge_agrees_with_deterministic": agree_d,
        "deterministic_agrees_with_human": det_vs_h,
        "rows": rows,
    }
    out_path.write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=1))
    for r in rows:
        if r["judge"] != r["human"] or r["deterministic"] != r["human"]:
            print(
                f"  {r['id']}: human={r['human']} det={r['deterministic']} judge={r['judge']} "
                f"({r['judge_model']}): {r['reason']}"
            )


if __name__ == "__main__":
    {"sheet": sheet, "score": score}[sys.argv[1]]()
