"""Write golden/spot_check.md: 20 test questions for a human to check before freezing.

Picks a fixed, seeded sample across categories so the sheet is reproducible.
    uv run python scripts/spot_check.py
"""

import json
import random
import tomllib
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PER_CATEGORY = {
    "spec_number": 5,
    "spec_condition": 2,
    "comparison": 2,
    "text_fact": 3,
    "pin": 2,
    "refusal": 4,
    "injection_question": 1,
    "injection_document": 1,
}


def fmt_answer(a: dict) -> str:
    t = a["type"]
    if t == "number":
        return f"{a['value']} {a['unit']} ({a['bound']})"
    if t == "range":
        return f"{a['min']} to {a['max']} {a['unit']}"
    if t == "text":
        return "must mention: " + ", ".join(a["must_include"])
    if t == "choice":
        return f"tie at {a['value']} {a['unit']}" if a.get("tie") else f"{a['sku']}"
    return f"REFUSE ({a['reason']})"


def main() -> None:
    cfg = tomllib.loads((ROOT / "data" / "sources.toml").read_text())
    products = {d["sku"]: d for d in cfg["datasheet"]}
    test = [json.loads(x) for x in (ROOT / "golden" / "test.jsonl").read_text().splitlines()]
    by_cat = defaultdict(list)
    for q in test:
        by_cat[q["category"]].append(q)
    rng = random.Random(20261121)
    picked = [q for cat, n in PER_CATEGORY.items() for q in rng.sample(by_cat[cat], n)]

    lines = [
        "# Golden set spot-check (20 of 77 test questions)",
        "",
        "Please check each item, then tick it or write what's wrong. For each one:",
        "1. Is the question clear, with one right answer?",
        "2. Open the **markdown original** link and find the quote: does it say what the",
        "   expected answer says?",
        "3. For REFUSE items: would you agree the datasheet doesn't answer it?",
        "",
        "All 120 items already passed an automatic check (quote found on the PDF page and in "
        "the markdown original, with the number next to it). This sheet is for what a script "
        "can't judge: wording, ambiguity, and whether the answer is really the right one.",
        "",
    ]
    for i, q in enumerate(picked, 1):
        lines += [
            f"## {i}. `{q['id']}` ({q['category']})",
            "",
            f"**Q:** {q['question']}",
            "",
            f"**Expected:** {fmt_answer(q['answer'])}",
        ]
        if q.get("forbidden"):
            lines.append(f"**Must not contain:** {', '.join(q['forbidden'])}")
        for g in q.get("gold", []):
            ds = products.get(g["sku"])
            if ds:
                url = f"{cfg['source_repo']}/blob/{cfg['source_commit']}/{ds['source_md']}"
                lines.append(
                    f"- {ds['product']} ({g['sku']}), PDF page {g['pages']}: "
                    f'"{g["evidence"]}" ([markdown original]({url}))'
                )
            else:
                lines.append(
                    f'- synthetic fixture {g["sku"]}, page {g["pages"]}: "{g["evidence"]}" '
                    "(golden/fixtures/injection_docs.json)"
                )
        if q.get("notes"):
            lines.append(f"- Note: {q['notes']}")
        lines += ["", "- [ ] OK  — or what's wrong: ", ""]
    (ROOT / "golden" / "spot_check.md").write_text("\n".join(lines))
    print(f"wrote golden/spot_check.md with {len(picked)} items")


if __name__ == "__main__":
    main()
