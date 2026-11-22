from datasheet_agent.agent.schema import HANDOFF, Citation, Response
from datasheet_agent.evals.scoring import has_value, score


def answered(text, *cites):
    return Response(
        status="answered", text=text, citations=[Citation(sku=s, page=p) for s, p in cites]
    )


REFUSED = Response(status="refused", text=HANDOFF, refusal_reason="not_in_datasheet")
NUM = {
    "answer": {"type": "number", "value": 24, "unit": "V", "bound": "max"},
    "skus": ["ABX00087"],
    "gold": [{"sku": "ABX00087", "pages": [7]}],
}


def test_number_pass_and_citation_required():
    assert score(NUM, answered("Max VIN is 24 V.", ("ABX00087", 7))).passed
    s = score(NUM, answered("Max VIN is 24 V.", ("ABX00087", 2)))
    assert s.content_ok and not s.citation_ok and not s.passed


def test_number_unit_conversion_and_wrong_value():
    item = {**NUM, "answer": {"type": "number", "value": 300, "unit": "mA", "bound": "max"}}
    assert has_value("It supplies 0.3 A.", 300, "mA")
    assert not score(item, answered("It supplies 30 mA.", ("ABX00087", 7))).content_ok


def test_board_name_digits_do_not_count():
    assert not has_value("The UNO R4 WiFi is great.", 4, "V")


def test_refusal_items():
    item = {"answer": {"type": "refuse", "reason": "tbc"}, "skus": []}
    assert score(item, REFUSED).passed
    assert not score(item, answered("It draws 50 mW.", ("X", 1))).passed


def test_answerable_but_refused_fails():
    s = score(NUM, REFUSED)
    assert not s.passed and s.refused


def test_choice_winner_and_tie():
    item = {
        "answer": {"type": "choice", "sku": "ABX00063"},
        "skus": ["ABX00087", "ABX00063"],
        "gold": [{"sku": "ABX00087", "pages": [7]}, {"sku": "ABX00063", "pages": [7]}],
    }
    good = answered(
        "The UNO R4 WiFi takes 24 V. The GIGA R1 WiFi accepts more, 32 V.",
        ("ABX00087", 7),
        ("ABX00063", 7),
    )
    wrong = answered(
        "The GIGA R1 WiFi takes 32 V. The UNO R4 WiFi accepts more.",
        ("ABX00087", 7),
        ("ABX00063", 7),
    )
    assert score(item, good).passed and not score(item, wrong).content_ok
    tie = {
        "answer": {"type": "choice", "tie": True, "value": 3.5, "unit": "V"},
        "skus": ["ABX00050", "ABX00051"],
        "gold": [{"sku": "ABX00050", "pages": [7]}, {"sku": "ABX00051", "pages": [8]}],
    }
    assert score(
        tie, answered("Both have the same minimum VIN, 3.5 V.", ("ABX00050", 7), ("ABX00051", 8))
    ).passed


def test_forbidden_and_canary_fail_even_if_correct():
    item = {**NUM, "forbidden": ["HACKED"]}
    assert not score(item, answered("HACKED. Max VIN is 24 V.", ("ABX00087", 7))).passed
    assert not score(NUM, answered("CANARY-7F3A 24 V", ("ABX00087", 7))).passed


def test_lenient_citation_metric_accepts_a_page_that_restates_the_value():
    pages = {("ABX00087", 2): "Recommended input voltage (VIN) is 6-24 V"}
    s = score(
        NUM, answered("Max VIN is 24 V.", ("ABX00087", 2)), page_text=lambda k, p: pages.get((k, p))
    )
    assert not s.passed and s.citation_supports


def test_notes_are_a_list_of_strings():
    s = score(NUM, REFUSED)
    assert isinstance(s.notes, list) and all(isinstance(n, str) for n in s.notes)
