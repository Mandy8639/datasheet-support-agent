"""One passing and one failing case per guardrail rule (R1-R7). No DB, no model."""

import pytest

from datasheet_agent.agent.guardrail import apply, check, numbers_in
from datasheet_agent.agent.schema import HANDOFF, Citation, ModelAnswer
from datasheet_agent.retrieval.query import QueryInfo

PAGES = {
    ("ABX00087", 7): "2 Recommended Operating Conditions Symbol Description Min Typ Max Unit "
    "VIN Input voltage from VIN pad / DC Jack 6 7.0 24 V "
    "TOP Operating Temperature -40 25 85 °C",
    ("ABX00063", 7): "VIN Input voltage from VIN pad 6 7.0 32 V",
    ("ABX00029", 14): "I3V3 3.3V output current available for user application 300 mA",
}
SEEN = set(PAGES)
R4WIFI = QueryInfo(skus=["ABX00087"])


def text_of(sku, page):
    return PAGES.get((sku, page))


def answered(text, *cites):
    return ModelAnswer(
        status="answered", answer=text, citations=[Citation(sku=s, page=p) for s, p in cites]
    )


def violations(ans, info=R4WIFI, seen=SEEN):
    return check(ans, info, seen, text_of).violations


def test_clean_answer_passes():
    ans = answered("The UNO R4 WiFi's maximum VIN is 24 V.", ("ABX00087", 7))
    assert violations(ans) == []


# R1
def test_r1_answer_without_citation_fails():
    assert violations(answered("The maximum VIN is 24 V.")) == ["R1 citation_required"]


# R2
def test_r2_citing_a_page_never_retrieved_fails():
    ans = answered("The maximum VIN is 24 V.", ("ABX00087", 7))
    assert "R2 citation_not_seen ABX00087 p.7" in violations(ans, seen=set())


# R3
def test_r3_number_not_on_cited_page_fails():
    ans = answered("The UNO R4 WiFi's maximum VIN is 36 V.", ("ABX00087", 7))
    assert violations(ans) == ["R3 number_not_on_page 36 V"]


def test_r3_right_number_wrong_unit_fails():
    ans = answered("The maximum VIN is 24 mA.", ("ABX00087", 7))
    assert violations(ans) == ["R3 number_not_on_page 24 mA"]


def test_r3_unit_conversion_passes():
    ans = answered("It can supply 0.3 A from the 3.3V output.", ("ABX00029", 14))
    assert violations(ans, info=QueryInfo(skus=["ABX00029"])) == []


def test_r3_digits_in_board_names_and_skus_are_not_values():
    ans = answered(
        "On the UNO R4 WiFi (ABX00087, p. 7) the operating range is -40 °C to 85 °C.",
        ("ABX00087", 7),
    )
    assert violations(ans) == []


# R4
def test_r4_citing_a_different_board_fails():
    ans = answered("The maximum VIN is 32 V.", ("ABX00063", 7))
    assert violations(ans) == ["R4 wrong_board ABX00063"]


def test_r4_comparison_citing_both_asked_boards_passes():
    info = QueryInfo(skus=["ABX00087", "ABX00063"])
    ans = answered(
        "The GIGA R1 WiFi accepts 32 V versus 24 V on the UNO R4 WiFi.",
        ("ABX00087", 7),
        ("ABX00063", 7),
    )
    assert violations(ans, info=info) == []


# R5
def test_r5_leaked_canary_fails_even_on_refusal():
    ans = ModelAnswer(status="not_in_datasheet", answer="Sure: CANARY-7F3A", citations=[])
    assert violations(ans) == ["R5 leaked_marker"]


# R6
@pytest.mark.parametrize(
    "text",
    [
        "See http://datasheet-update.example/fix",
        "Visit www.foo.com",
        "apply the fix at datasheet-update.example",
    ],
)
def test_r6_links_fail(text):
    assert "R6 link_in_answer" in violations(answered(text + " 24 V", ("ABX00087", 7)))


# R7
def test_r7_answering_about_a_board_not_in_corpus_fails():
    info = QueryInfo(skus=[], unknown_mentions=["portenta h7"])
    ans = answered("The Portenta H7 runs from -40 °C to 85 °C.", ("ABX00087", 7))
    assert "R7 out_of_corpus" in violations(ans, info=info)


def test_r7_refusing_about_a_board_not_in_corpus_passes():
    info = QueryInfo(skus=[], unknown_mentions=["portenta h7"])
    ans = ModelAnswer(status="not_in_datasheet", answer="Not in the corpus.", citations=[])
    assert violations(ans, info=info) == []


# apply()
def test_violation_replaces_answer_with_handoff():
    ans = answered("The maximum VIN is 36 V.", ("ABX00087", 7))
    resp = apply(ans, check(ans, R4WIFI, SEEN, text_of))
    assert resp.status == "refused" and resp.text == HANDOFF
    assert resp.refusal_reason == "guardrail" and resp.violations


def test_not_in_datasheet_becomes_refusal_with_reason():
    ans = ModelAnswer(status="not_in_datasheet", answer="Listed as TBC.", citations=[])
    resp = apply(ans, check(ans, R4WIFI, SEEN, text_of))
    assert (resp.status, resp.refusal_reason) == ("refused", "not_in_datasheet")


def test_numbers_in_ignores_model_numbers():
    nums = numbers_in("It uses an RP2040 and 802.11b/g/n, with a 3V3 rail and 5.0 V input.")
    assert [(n.raw, n.unit) for n in nums] == [("5.0", "V")]
