import pytest

from datasheet_agent.ingest.pdf import classify


@pytest.mark.parametrize(
    ("header", "kind"),
    [
        (["Symbol", "Description", "Min", "Typ", "Max", "Unit"], "spec"),
        (["Description", "Min", "Typ", "Max", "Unit"], "spec"),
        (["Pin", "Function", "Type", "Description"], "pin"),
        (["Ref.", "Description"], "bom"),
        (["Substance", "Maximum Limit (ppm)"], "rohs"),
        (["Date", "Revision", "Changes"], "changelog"),
        (["Parameter", "Value"], "feature"),
        (["Company name", "Arduino SRL"], "company"),
        (["Certification", "Status"], "cert"),
        (["", "NOTE: something"], "note"),
        (["Frequency bands", "Maximum output power (ERP)"], "rf"),
    ],
)
def test_classify(header, kind):
    assert classify(header, []) == kind
