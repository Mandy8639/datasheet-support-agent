import pytest

from datasheet_agent.ingest.units import clean_cell, normalize_unit, parse_number


@pytest.mark.parametrize(
    ("cell", "expected"),
    [
        ("-40", -40.0),
        ("−40", -40.0),
        ("3.3", 3.3),
        ("+85", 85.0),
        ("1,000", 1000.0),
        ("~5", 5.0),
        ("<10", 10.0),
        ("", None),
        ("-", None),
        ("TBD", None),
        (None, None),
        ("1.8-3.6", None),
        ("see note", None),
    ],
)
def test_parse_number(cell, expected):
    assert parse_number(cell) == expected


@pytest.mark.parametrize(
    ("unit", "si", "factor"),
    [
        ("mA", "A", 1e-3),
        ("µA", "A", 1e-6),
        ("uA", "A", 1e-6),
        ("°C", "degC", 1.0),
        ("ºC", "degC", 1.0),
        ("MHz", "Hz", 1e6),
        ("KB", "B", 1024.0),
        ("V", "V", 1.0),
    ],
)
def test_normalize_unit(unit, si, factor):
    assert normalize_unit(unit) == (si, pytest.approx(factor))


def test_unknown_and_blank_units():
    assert normalize_unit("furlongs") == (None, None)
    assert normalize_unit("") == (None, None)


def test_clean_cell_collapses_newlines():
    assert clean_cell("Input voltage\nfrom VIN") == "Input voltage from VIN"


def test_split_value_unit():
    from datasheet_agent.ingest.units import split_value_unit

    assert split_value_unit("-40 °C") == ("-40", "°C")
    assert split_value_unit("85 °C") == ("85", "°C")
    assert split_value_unit("3.3") == ("3.3", None)
    assert split_value_unit("0.7*V DDIO_EXT") == ("0.7*V DDIO_EXT", None)
    assert split_value_unit("-40 °C (-40 °F)") == ("-40", "°C")
    assert split_value_unit("85 °C ( 185 °F)") == ("85", "°C")
