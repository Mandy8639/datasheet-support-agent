"""Parse one datasheet PDF into page text, headed sections and classified tables.

Layout facts for Arduino datasheets (checked on the corpus, 2026-11-21):
- headings are RobotoMono-Bold at 18 pt (part), 14.4 pt (section) and 10.8 pt (subsection);
  body text is OpenSans 9 pt;
- every page has a running header (top ~46) and footer (top ~797) on an 842-pt page;
- pages 2-3 are a table of contents.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber

from datasheet_agent.ingest.units import clean_cell

HEADER_MAX_TOP = 70
FOOTER_MIN_TOP = 780
_TOC_LINE = re.compile(r"^\d+(\.\d+)*\s+.+\s(\d+)$")
TOC_SEARCH_PAGES = 5  # partial tables of contents only appear near the front


@dataclass
class Table:
    page_no: int
    table_idx: int
    section: str
    header: list[str]
    rows: list[list[str]]
    kind: str = "other"


@dataclass
class Section:
    heading: str
    level: int
    page_start: int
    page_end: int
    lines: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(self.lines).strip()


@dataclass
class ParsedDoc:
    pages: dict[int, str]
    sections: list[Section]
    tables: list[Table]
    toc_pages: list[int]


def _heading_level(line: dict) -> int | None:
    chars = [c for c in line["chars"] if c["text"].strip()]
    if not chars:
        return None
    bold_mono = sum("RobotoMono-Bold" in c["fontname"] for c in chars) / len(chars)
    size = max(c["size"] for c in chars)
    if bold_mono < 0.8 or size < 10.5:
        return None
    return 1 if size >= 17 else 2 if size >= 14 else 3


def _clean_table(raw: list[list[str | None]]) -> tuple[list[str], list[list[str]]]:
    header = [clean_cell(c) for c in raw[0]]
    rows = []
    for r in raw[1:]:
        cells = []
        for i, c in enumerate(r):
            # Symbol columns print subscripts on their own line ("V\nIN"); join them.
            is_symbol = i < len(header) and header[i].lower() == "symbol"
            cells.append("".join((c or "").split()) if is_symbol else clean_cell(c))
        if any(cells):
            rows.append(cells)
    return header, rows


def classify(header: list[str], rows: list[list[str]]) -> str:
    h = [x.lower() for x in header]
    joined = " ".join(h)
    if "min" in h and "max" in h:
        return "spec"
    if h == ["parameter", "value"]:
        return "feature"
    if h[:1] == ["company name"] or "company address" in h:
        return "company"
    if h[:1] == ["certification"]:
        return "cert"
    if h and h[0].startswith("pin") or ("pin" in joined and "function" in joined):
        return "pin"
    if h and h[0].startswith("ref") and "description" in joined:
        return "bom"
    if "substance" in joined:
        return "rohs"
    if "link" in h:
        return "link"
    if "date" in h and "revision" in h:
        return "changelog"
    if h[:1] in (["feature"], ["component"]) or "details" in h:
        return "feature"
    if "frequency bands" in joined:
        return "rf"
    if len(h) == 2 and h[0] == "":
        return "note"
    return "other"


def _is_toc_line(text: str, page_count: int) -> bool:
    m = _TOC_LINE.match(text.strip())
    return bool(m) and 1 <= int(m.group(2)) <= page_count


def _is_toc(lines: list[str]) -> bool:
    body = [t for t in lines if t.strip()]
    return len(body) >= 8 and sum(bool(_TOC_LINE.match(t)) for t in body) / len(body) > 0.5


def parse_pdf(path: Path) -> ParsedDoc:
    pages: dict[int, str] = {}
    sections: list[Section] = [Section("Overview", 1, 1, 1)]
    tables: list[Table] = []
    toc_pages: list[int] = []

    with pdfplumber.open(path) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            pages[page_no] = page.extract_text(y_tolerance=4) or ""
            found = page.find_tables()
            boxes = [t.bbox for t in found]

            def outside_tables(obj, boxes=boxes):
                x = (obj["x0"] + obj["x1"]) / 2
                y = (obj["top"] + obj["bottom"]) / 2
                return not any(b[0] <= x <= b[2] and b[1] <= y <= b[3] for b in boxes)

            body = page.filter(outside_tables)
            lines = [
                ln
                for ln in body.extract_text_lines(return_chars=True, y_tolerance=4)
                if HEADER_MAX_TOP < ln["top"] < FOOTER_MIN_TOP
            ]
            if _is_toc([ln["text"] for ln in lines]):
                toc_pages.append(page_no)
                continue
            if page_no <= TOC_SEARCH_PAGES:
                # A table of contents can share a page with real content; drop its lines
                # ("15.1 Declaration of Conformity 19") when the trailing number is a real page.
                lines = [ln for ln in lines if not _is_toc_line(ln["text"], len(pdf.pages))]

            # Walk lines and tables top to bottom so each table gets the heading above it.
            events = [("line", ln["top"], ln) for ln in lines]
            events += [("table", t.bbox[1], t) for t in found]
            events.sort(key=lambda e: e[1])
            table_idx = 0
            for kind, _top, obj in events:
                current = sections[-1]
                if kind == "line":
                    level = _heading_level(obj)
                    if level is not None:
                        sections.append(Section(obj["text"].strip(), level, page_no, page_no))
                    else:
                        current.lines.append(obj["text"])
                        current.page_end = page_no
                    continue
                raw = obj.extract()
                if not raw or not raw[0]:
                    continue
                header, rows = _clean_table(raw)
                t = Table(page_no, table_idx, current.heading, header, rows)
                t.kind = classify(header, rows)
                tables.append(t)
                table_idx += 1

    sections = [s for s in sections if s.text or any(t.section == s.heading for t in tables)]
    return ParsedDoc(pages, sections, tables, toc_pages)
