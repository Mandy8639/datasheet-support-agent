"""Spec rows parsed from the PDFs must match Arduino's own markdown sources.

Expected values were copied by hand from the CC BY-SA markdown originals in
arduino/docs-content @ 65d578fc7de8 (see data/sources.toml), not from the PDF parser, so this
checks the parser against an independent source. Values: Arduino S.r.l., CC BY-SA 4.0.
"""

from functools import cache
from pathlib import Path

import pytest

from datasheet_agent.ingest.pdf import parse_pdf
from datasheet_agent.ingest.tables import spec_rows

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"

# (sku, symbol, parameter fragment, min, typ, max, unit) -- None means "cell blank or '-'".
EXPECTED = [
    ("ABX00087", "TOP", "Operating Temperature", "-40", "25", "85", "°C"),
    ("ABX00053", "I3V3", "3.3V output current", None, None, "800", "mA"),
    ("ABX00053", "IOHMax", "output set high", None, None, "8", "mA"),
    ("ABX00053", "VOH", "Output high voltage", "2.7", None, "3.3", "V"),
    ("ABX00053", "VOL", "Output low voltage", "0", None, "0.4", "V"),
    ("ABX00053", "TOP", "Operating Temperature", "-20", None, "80", "°C"),
    ("ABX00029", "VINMax", "Maximum input voltage from VIN", "-0.3", None, "5.5", "V"),
    ("ABX00029", "VUSBMax", "Maximum input voltage from USB", "-0.3", None, "5.5", "V"),
    ("ABX00029", "TST", "Storage Temperature", "-40", None, "85", "°C"),
    ("ABX00029", "I3V3", "3.3V output current available", None, None, "300", "mA"),
    ("ABX00050", "TOP", "Operating Temperature", "-40", "25", "85", "°C"),
    ("ABX00050", None, "sensor polling at 1Hz", None, "2.5", None, "mA"),
    ("ABX00050", None, "sensor polling once per hour", None, "1.15", None, "mA"),
    ("ABX00049", "I3V3", "3.3 V output current", None, None, "1000", "mA"),
    ("ABX00049", "PBL", "busy loop", None, "2350", None, "mW"),
    ("ABX00049", "PLP", "low power mode", None, "200", None, "mW"),
    ("ABX00049", "PMAX", "Maximum Power Consumption", None, "4000", None, "mW"),
    ("ABX00051", "TOP", "Operating Temperature", "-40", "25", "85", "°C"),
    ("ABX00051", None, "image capture", None, "105", None, "mA"),
    ("ABX00074", "TOP", "Operating Temperature", "-40", None, "85", "°C"),
    ("A000066", None, "Conservative thermal limits", "-40", None, "85", "°C"),
]


@cache
def rows_for(sku: str):
    parsed = parse_pdf(RAW / f"{sku}.pdf")
    return [r for t in parsed.tables if t.kind == "spec" for r in spec_rows(t)]


def _blank(v: str | None) -> str | None:
    return None if v in (None, "", "-") else v


@pytest.mark.parametrize("sku,symbol,fragment,mn,ty,mx,unit", EXPECTED)
def test_spec_row_matches_markdown_source(sku, symbol, fragment, mn, ty, mx, unit):
    if not (RAW / f"{sku}.pdf").exists():
        pytest.skip("corpus not downloaded; run `uv run python scripts/download.py`")
    candidates = [
        r
        for r in rows_for(sku)
        if fragment.lower() in r.parameter.lower() and (symbol is None or r.symbol == symbol)
    ]
    assert len(candidates) == 1, f"{sku} {symbol} {fragment!r}: {len(candidates)} matches"
    r = candidates[0]
    assert (_blank(r.min_raw), _blank(r.typ_raw), _blank(r.max_raw)) == (mn, ty, mx)
    assert r.unit == unit
