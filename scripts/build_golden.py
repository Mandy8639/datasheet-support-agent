"""Build and verify the golden evaluation set from golden/questions.yaml.

For every question this checks, against two independent sources:
  * the PDF page text (pages table, loaded by scripts/ingest.py), and
  * Arduino's markdown original (data/source_md/<sku>.md, CC BY-SA 4.0),
that each evidence quote exists, that the expected number appears with it, and, for
"not in the datasheet" questions, that the absent terms really are absent. Gold page numbers
are filled in from the PDF. Questions are split dev/test by a fixed rule (every third question
of each category goes to dev), so the split never depends on results.

Writes golden/dev.jsonl and golden/test.jsonl. Fails loudly on any unverifiable item.

    uv run python scripts/build_golden.py
"""

import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import yaml

from datasheet_agent.db import admin_conn

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "golden"
MD_DIR = ROOT / "data" / "source_md"
FIXTURES = GOLDEN / "fixtures" / "injection_docs.json"


def norm(text: str) -> str:
    t = unicodedata.normalize("NFKC", text)
    t = re.sub(r"[®™]", "", t)
    t = t.replace("−", "-").replace("–", "-").replace("—", "-")
    t = t.replace("μ", "µ")
    return " ".join(t.split()).lower()


def md_plain(md: str) -> list[str]:
    """Markdown original as plain lines: markup removed, table cells joined by spaces."""
    # HTML tables put each cell on its own line; collapse each <tr> into one line first.
    md = re.sub(
        r"<tr[^>]*>(.*?)</tr>", lambda m: " ".join(m.group(1).split()) + "\n", md, flags=re.S | re.I
    )
    md = re.sub(r"</?[a-zA-Z][^<>\n]*>", " ", md)
    out = []
    for line in md.splitlines():
        line = re.sub(r"</?(sub|sup|br|b|strong|em|i)\s*/?>", "", line)
        line = re.sub(r"\$([^$]*)\$", r"\1", line)
        line = re.sub(r"[*`#]", "", line).replace("|", " ")
        line = re.sub(r"\\_", "_", line)
        line = re.sub(r"_\{([^}]*)\}", r"\1", line)
        if line.strip():
            out.append(norm(line))
    return out


def number_forms(value) -> set[str]:
    v = float(value)
    forms = {f"{v:g}", str(value)}
    if v == int(v):
        forms |= {str(int(v)), f"{int(v)}.0"}
    return {norm(f) for f in forms}


def contains_number(text: str, value) -> bool:
    pattern = r"(?<![\d.]){}(?![\d])"
    return any(re.search(pattern.format(re.escape(f)), text) for f in number_forms(value))


def answer_numbers(ans: dict) -> list:
    if ans["type"] == "number":
        return [ans["value"]]
    if ans["type"] == "range":
        return [ans["min"], ans["max"]]
    return []


def verify(q: dict, pages: dict, md: dict, fixtures: dict) -> list[str]:
    """Return a list of problems; fills q['gold'][*]['pages'] in place."""
    problems = []
    for g in q.get("gold", []):
        sku, ev = g["sku"], norm(g["evidence"])
        doc_pages = fixtures.get(sku) or pages.get(sku)
        if not doc_pages:
            problems.append(f"unknown sku {sku}")
            continue
        hit = [n for n, t in doc_pages.items() if ev in t]
        if not hit:
            problems.append(f"{sku}: evidence not on any PDF page: {g['evidence']!r}")
            continue
        g["pages"] = hit
        nums = g.get("numbers", answer_numbers(q["answer"]) if len(q["gold"]) == 1 else [])
        for value in nums:
            if not any(contains_number(doc_pages[n], value) for n in hit):
                problems.append(f"{sku}: {value} not on evidence page(s) {hit}")
        if sku in fixtures:
            continue  # synthetic fixtures have no markdown original
        lines = md.get(sku)
        if lines is None:
            problems.append(f"{sku}: markdown original missing (run the md fetch step)")
            continue
        md_hits = [ln for ln in lines if ev in ln]
        if not md_hits:
            problems.append(f"{sku}: evidence not in markdown original: {g['evidence']!r}")
        for value in nums:
            if md_hits and not any(contains_number(ln, value) for ln in md_hits):
                problems.append(f"{sku}: {value} not on the markdown line(s) with the evidence")
    for sku, term in ((s, t) for s in q.get("absent_in", []) for t in q.get("absent_terms", [])):
        pattern = rf"\b{re.escape(norm(term))}\b"
        if any(re.search(pattern, t) for t in pages[sku].values()):
            problems.append(f"{sku}: 'absent' term is present in the PDF: {term!r}")
    if q["answer"]["type"] != "refuse" and not q.get("gold"):
        problems.append("non-refusal question without gold evidence")
    return problems


def load_sources() -> tuple[dict, dict, dict]:
    pages: dict[str, dict[int, str]] = defaultdict(dict)
    with admin_conn() as conn:
        for sku, page_no, text in conn.execute(
            "SELECT d.sku, p.page_no, p.text FROM pages p JOIN documents d ON d.id = p.doc_id"
        ):
            pages[sku][page_no] = norm(text)
    md = {p.stem: md_plain(p.read_text()) for p in MD_DIR.glob("*.md")}
    fixtures = {}
    if FIXTURES.exists():
        for doc in json.loads(FIXTURES.read_text())["documents"]:
            fixtures[doc["sku"]] = {int(n): norm(t) for n, t in doc["pages"].items()}
    return pages, md, fixtures


def main() -> int:
    items = yaml.safe_load((GOLDEN / "questions.yaml").read_text())["questions"]
    pages, md, fixtures = load_sources()

    ids = Counter(q["id"] for q in items)
    dupes = [i for i, n in ids.items() if n > 1]
    failures = {f"duplicate id {d}": ["id used more than once"] for d in dupes}

    seen_in_category: Counter = Counter()
    for q in items:
        problems = verify(q, pages, md, fixtures)
        if problems:
            failures[q["id"]] = problems
        k = seen_in_category[q["category"]]
        q["split"] = "dev" if k % 3 == 0 else "test"
        seen_in_category[q["category"]] += 1

    if failures:
        for qid, probs in failures.items():
            for p in probs:
                print(f"FAIL {qid}: {p}")
        print(f"{len(failures)} of {len(items)} questions failed verification")
        return 1

    for split in ("dev", "test"):
        rows = [q for q in items if q["split"] == split]
        with (GOLDEN / f"{split}.jsonl").open("w") as f:
            for q in rows:
                f.write(json.dumps(q, ensure_ascii=False, sort_keys=True) + "\n")
    by_cat = Counter((q["category"], q["split"]) for q in items)
    print(f"verified {len(items)} questions")
    for cat in sorted({c for c, _ in by_cat}):
        print(f"  {cat:22} dev {by_cat[(cat, 'dev')]:3}  test {by_cat[(cat, 'test')]:3}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
