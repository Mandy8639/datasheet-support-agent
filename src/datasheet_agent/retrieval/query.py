"""Query understanding: which boards a question is about.

Board names come from data/sources.toml (product name, SKU and listed aliases), so nothing
here is tuned to particular questions. Matching is longest-first on a normalized form, so
"Nano 33 BLE Rev2" wins over "Nano 33 BLE". Mentions of an Arduino family name that match
no known board (e.g. "Portenta H7") are reported as unknown, so the agent can refuse
instead of answering from a different board's datasheet.
"""

import re
import tomllib
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FAMILIES = (
    r"(?:uno|nano|mkr|portenta|nicla|giga|mega|opta|leonardo|due|zero|esplora|pico|raspberry pi)"
)
# A family word plus up to three following tokens, e.g. "Portenta H7", "Nano Matter".
_MENTION = re.compile(rf"\b{FAMILIES}\b(?:[\s-]+[a-z0-9]+){{0,3}}", re.I)


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower().replace("®", "")).strip()


@dataclass
class QueryInfo:
    skus: list[str] = field(default_factory=list)
    unknown_mentions: list[str] = field(default_factory=list)


@cache
def board_aliases(extra: tuple[tuple[str, str], ...] = ()) -> list[tuple[str, str]]:
    """(normalized alias, sku), longest alias first."""
    cfg = tomllib.loads((ROOT / "data" / "sources.toml").read_text())
    pairs = set()
    for ds in cfg["datasheet"]:
        names = [
            ds["sku"],
            ds["product"],
            ds["product"].removeprefix("Arduino "),
            *ds.get("aliases", []),
        ]
        pairs |= {(_norm(n), ds["sku"]) for n in names}
    pairs |= {(_norm(n), sku) for n, sku in extra}
    return sorted(pairs, key=lambda p: -len(p[0]))


def understand(question: str, extra_aliases: tuple[tuple[str, str], ...] = ()) -> QueryInfo:
    """Find boards in the question. extra_aliases lets eval fixtures register test boards."""
    text = f" {_norm(question)} "
    info = QueryInfo()
    for alias, sku in board_aliases(extra_aliases):
        needle = f" {alias} "
        if needle in text:
            if sku not in info.skus:
                info.skus.append(sku)
            text = text.replace(needle, " # ")  # consume, so a shorter alias can't re-match
    for m in _MENTION.finditer(text):
        mention = m.group(0).strip()
        if mention and "#" not in mention:
            info.unknown_mentions.append(mention)
    return info


def strip_boards(question: str, extra_aliases: tuple[tuple[str, str], ...] = ()) -> str:
    """The question with every recognised board name removed.

    Used for per-board sub-searches: the board filter already fixes which datasheet is
    searched, and leaving the names in makes a reranker favour any chunk that names a board.
    """
    text = f" {_norm(question)} "
    for alias, _sku in board_aliases(extra_aliases):
        text = text.replace(f" {alias} ", " ")
    return " ".join(text.split())
