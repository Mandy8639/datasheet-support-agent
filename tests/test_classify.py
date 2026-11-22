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


@pytest.mark.parametrize(
    ("line", "is_toc"),
    [
        ("15.1 Declaration of Conformity CE DoC (EU) 19", True),
        ("10 Revision History 16", True),
        ("19 Change Log 22", True),
        ("5.8 Board Recovery 15", True),
        ("2 Recommended Operating Conditions", False),  # a heading has no page number
        ("1x 16-bit Timer/Counter with input capture", False),
        ("12 channel DMA", False),
        ("3 Block Diagram 99", False),  # 99 is beyond the page count
    ],
)
def test_toc_line_detection(line, is_toc):
    from datasheet_agent.ingest.pdf import _is_toc_line

    assert _is_toc_line(line, page_count=24) is is_toc
