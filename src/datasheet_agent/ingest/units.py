"""Parse spec-table numbers and normalize units.

Datasheet cells are messy: "-40", "−40" (U+2212), "3.3", "TBD", "-", "", "~5", "<10".
Units come as printed: "°C", "ºC", "mA", "µA", "uA", "MHz", "KB" ...
"""

import re

# printed unit -> (SI unit, factor). Matching is exact after whitespace cleanup.
_UNITS: dict[str, tuple[str, float]] = {
    "V": ("V", 1.0),
    "mV": ("V", 1e-3),
    "kV": ("V", 1e3),
    "A": ("A", 1.0),
    "mA": ("A", 1e-3),
    "uA": ("A", 1e-6),
    "µA": ("A", 1e-6),
    "μA": ("A", 1e-6),
    "nA": ("A", 1e-9),
    "W": ("W", 1.0),
    "mW": ("W", 1e-3),
    "uW": ("W", 1e-6),
    "µW": ("W", 1e-6),
    "μW": ("W", 1e-6),
    "Hz": ("Hz", 1.0),
    "kHz": ("Hz", 1e3),
    "KHz": ("Hz", 1e3),
    "MHz": ("Hz", 1e6),
    "GHz": ("Hz", 1e9),
    "°C": ("degC", 1.0),
    "ºC": ("degC", 1.0),
    "℃": ("degC", 1.0),
    "C": ("degC", 1.0),
    "B": ("B", 1.0),
    "KB": ("B", 1024.0),
    "kB": ("B", 1024.0),
    "MB": ("B", 1024.0**2),
    "Kbit": ("bit", 1e3),
    "Mbit": ("bit", 1e6),
    "Ω": ("ohm", 1.0),
    "ohm": ("ohm", 1.0),
    "kΩ": ("ohm", 1e3),
    "s": ("s", 1.0),
    "ms": ("s", 1e-3),
    "us": ("s", 1e-6),
    "µs": ("s", 1e-6),
    "μs": ("s", 1e-6),
    "dBm": ("dBm", 1.0),
    "%": ("%", 1.0),
    "mm": ("m", 1e-3),
    "g": ("g", 1.0),
}

_NUM = re.compile(r"^[~<>≤≥]?\s*([+-]?\d+(?:\.\d+)?)$")


def clean_cell(cell: str | None) -> str:
    """Collapse whitespace; keep the text as printed otherwise."""
    return " ".join((cell or "").split())


def parse_number(cell: str | None) -> float | None:
    """Return the number in a Min/Typ/Max cell, or None for blanks, '-', 'TBD', ranges, text."""
    s = clean_cell(cell).replace("−", "-").replace("–", "-").replace(",", "")
    if s in {"", "-", "--", "—", "N/A", "n/a", "TBD", "tbd"}:
        return None
    m = _NUM.match(s)
    return float(m.group(1)) if m else None


_VALUE_WITH_UNIT = re.compile(r"^([~<>≤≥]?\s*[+-]?\d+(?:\.\d+)?)\s*([^\d\s].*)$")


def split_value_unit(cell: str | None) -> tuple[str | None, str | None]:
    """Split a cell like "-40 °C" into ("-40", "°C") when the unit is a known one."""
    s = clean_cell(cell).replace("\u2212", "-")
    # Drop a bracketed conversion after the unit: "-40 °C (-40 °F)" -> "-40 °C".
    s_main = re.sub(r"\s*\([^)]*\)\s*$", "", s)
    m = _VALUE_WITH_UNIT.match(s_main)
    if m and m.group(2).strip() in _UNITS:
        return m.group(1).strip(), m.group(2).strip()
    return (s or None), None


def normalize_unit(unit: str | None) -> tuple[str | None, float | None]:
    """Map a printed unit to (SI unit, factor). Unknown units return (None, None)."""
    u = clean_cell(unit)
    if not u:
        return None, None
    return _UNITS.get(u, (None, None))
