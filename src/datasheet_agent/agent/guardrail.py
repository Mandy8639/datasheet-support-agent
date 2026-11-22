"""Deterministic checks on every answer before the user sees it.

Rules (any violation replaces the answer with a refusal + handoff):
  R1 citation_required     an answer must cite at least one page
  R2 citation_not_seen     every cited page must be one the agent actually retrieved
  R3 number_not_on_page    every number in the answer must appear on a cited page,
                           with a compatible unit (300 mA == 0.3 A)
  R4 wrong_board           cited boards must be the boards the question asked about
  R5 leaked_marker         no internal canary markers (CANARY-...) in the output
  R6 link_in_answer        no links or domains in the answer
  R7 out_of_corpus         a question about a board not in the corpus must be refused
"""

import re
from collections.abc import Callable
from dataclasses import dataclass, field

from datasheet_agent.agent.schema import HANDOFF, ModelAnswer, Response
from datasheet_agent.ingest.units import _UNITS, normalize_unit
from datasheet_agent.retrieval.query import QueryInfo, board_aliases

_CANARY = re.compile(r"canary-[a-z0-9-]+", re.I)
_LINK = re.compile(r"https?://|www\.|\b[a-z0-9-]+\.(?:com|net|org|io|cc|example)\b", re.I)
_CITE_MARK = re.compile(r"\[[^\]]*\]|\(?\b(?:p\.|page|pp\.)\s*\d+(?:\s*[-,]\s*\d+)*\)?", re.I)
_SKU = re.compile(r"\b(?:A|ABX|AKX|ASX|AFX|ZZT)[A-Z]*\d{5,6}[A-Z0-9]*\b", re.I)
_UNIT_ALT = "|".join(sorted((re.escape(u) for u in _UNITS), key=len, reverse=True))
# A number not glued to letters/dots (so "RP2040", "802.11b" and "3V3" are not numbers).
_NUMBER = re.compile(rf"(?<![\w.])([+-]?\d+(?:\.\d+)?)(?:\s*({_UNIT_ALT}))?(?![\w.]*[a-zA-Z0-9])")


@dataclass
class Number:
    value: float
    raw: str
    unit: str | None


@dataclass
class GuardrailResult:
    violations: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.violations


def _strip_names(text: str) -> str:
    """Remove board names, SKUs and citation markers, whose digits are not spec values."""
    t = _CITE_MARK.sub(" ", text)
    t = _SKU.sub(" ", t)
    low = f" {t} "
    for alias, _ in board_aliases():
        low = re.sub(
            rf"(?i)(?<![\w]){re.escape(alias).replace(r'\ ', r'[\s-]+')}(?![\w])", " ", low
        )
    return low


def numbers_in(text: str) -> list[Number]:
    out = []
    for m in _NUMBER.finditer(_strip_names(text).replace("−", "-")):
        raw, unit = m.group(1), m.group(2)
        out.append(Number(float(raw), raw, unit))
    return out


def _forms(v: float) -> set[str]:
    forms = {f"{v:g}", f"{v:.1f}", f"{v:.2f}".rstrip("0").rstrip(".")}
    if v == int(v):
        forms.add(str(int(v)))
    return forms


def _unit_present(page: str, unit: str) -> bool:
    return bool(re.search(rf"(?<![A-Za-z]){re.escape(unit)}(?![A-Za-z])", page))


def _page_has(page: str, n: Number) -> bool:
    page = page.replace("−", "-").replace("μ", "µ")

    def has_value(v: float) -> bool:
        return any(re.search(rf"(?<![\d.]){re.escape(f)}(?![\d])", page) for f in _forms(v))

    if n.unit is None:
        return has_value(n.value)
    si, factor = normalize_unit(n.unit)
    if si is None:
        return has_value(n.value)
    # Same number, and some unit of the same dimension on the page.
    same_dim = [u for u, (s, _) in _UNITS.items() if s == si]
    unit_on_page = any(
        re.search(rf"(?<![A-Za-z]){re.escape(u)}(?![A-Za-z])", page) for u in same_dim
    )
    if has_value(n.value) and unit_on_page:
        return True
    # Or the same quantity written in another unit of that dimension (300 mA vs 0.3 A).
    base = n.value * factor
    return any(
        s == si and f != factor and _unit_present(page, u) and has_value(round(base / f, 6))
        for u, (s, f) in _UNITS.items()
    )


def check(
    answer: ModelAnswer,
    info: QueryInfo,
    seen_pages: set[tuple[str, int]],
    page_text: Callable[[str, int], str | None],
) -> GuardrailResult:
    res = GuardrailResult()
    text = answer.answer
    if _CANARY.search(text):
        res.violations.append("R5 leaked_marker")
    if _LINK.search(text):
        res.violations.append("R6 link_in_answer")
    if info.unknown_mentions and not info.skus and answer.status == "answered":
        res.violations.append("R7 out_of_corpus")
    if answer.status != "answered":
        return res

    cites = {(c.sku, c.page) for c in answer.citations}
    if not cites:
        res.violations.append("R1 citation_required")
        return res
    for sku, page in sorted(cites - seen_pages):
        res.violations.append(f"R2 citation_not_seen {sku} p.{page}")
    if info.skus:
        for sku in sorted({s for s, _ in cites} - set(info.skus)):
            res.violations.append(f"R4 wrong_board {sku}")
    pages = [t for t in (page_text(s, p) for s, p in cites & seen_pages) if t]
    for n in numbers_in(text):
        if not any(_page_has(p, n) for p in pages):
            unit = f" {n.unit}" if n.unit else ""
            res.violations.append(f"R3 number_not_on_page {n.raw}{unit}")
    return res


def apply(
    answer: ModelAnswer, result: GuardrailResult, refusal_reason: str | None = None
) -> Response:
    """Turn a model answer plus guardrail result into what the user sees."""
    if not result.ok:
        return Response(
            status="refused", text=HANDOFF, refusal_reason="guardrail", violations=result.violations
        )
    if answer.status != "answered":
        return Response(
            status="refused", text=HANDOFF, refusal_reason=refusal_reason or "not_in_datasheet"
        )
    return Response(status="answered", text=answer.answer, citations=answer.citations)
