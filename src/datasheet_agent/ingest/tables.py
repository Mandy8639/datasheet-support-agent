"""Turn classified tables into spec rows and pin rows."""

from dataclasses import dataclass

from datasheet_agent.ingest.pdf import Table
from datasheet_agent.ingest.units import normalize_unit, parse_number, split_value_unit


@dataclass
class SpecRow:
    page_no: int
    section: str
    symbol: str | None
    parameter: str
    min_raw: str | None
    typ_raw: str | None
    max_raw: str | None
    unit: str | None
    table_idx: int

    @property
    def values(self) -> tuple[float | None, float | None, float | None]:
        return parse_number(self.min_raw), parse_number(self.typ_raw), parse_number(self.max_raw)

    @property
    def si(self) -> tuple[str | None, float | None]:
        return normalize_unit(self.unit)


@dataclass
class PinRow:
    page_no: int
    section: str
    pin: str
    function: str | None
    type: str | None
    description: str | None
    table_idx: int


def _col(header: list[str], *names: str) -> int | None:
    lowered = [h.lower() for h in header]
    for name in names:
        if name in lowered:
            return lowered.index(name)
    return None


def _cell(row: list[str], idx: int | None) -> str | None:
    if idx is None or idx >= len(row):
        return None
    return row[idx] or None


def spec_rows(table: Table) -> list[SpecRow]:
    h = table.header
    c_sym = _col(h, "symbol")
    c_par = _col(h, "parameter", "description", "characteristic")
    c_min, c_typ, c_max = _col(h, "min"), _col(h, "typ", "nom"), _col(h, "max")
    c_unit = _col(h, "unit", "units")
    out = []
    for r in table.rows:
        parameter = _cell(r, c_par) or _cell(r, c_sym)
        values = [_cell(r, c) for c in (c_min, c_typ, c_max)]
        if not parameter or not any(values):
            continue  # sub-heading rows and empty rows carry no spec
        unit = _cell(r, c_unit)
        if unit is None:
            # Some tables print the unit inside each value ("-40 °C") and have no unit column.
            split = [split_value_unit(v) for v in values]
            units = {u for _, u in split if u}
            if len(units) == 1:
                values, unit = [v for v, _ in split], units.pop()
        out.append(
            SpecRow(
                table.page_no,
                table.section,
                _cell(r, c_sym),
                parameter,
                *values,
                unit,
                table.table_idx,
            )
        )
    return out


def pin_rows(table: Table) -> list[PinRow]:
    h = table.header
    c_pin = 0
    c_fn = _col(h, "function", "acronym")
    c_type = _col(h, "type")
    c_desc = _col(h, "description")
    out = []
    for r in table.rows:
        pin = _cell(r, c_pin)
        if not pin:
            continue
        out.append(
            PinRow(
                table.page_no,
                table.section,
                pin,
                _cell(r, c_fn),
                _cell(r, c_type),
                _cell(r, c_desc),
                table.table_idx,
            )
        )
    return out
