"""The whole agent flow with a scripted model, fake retrieval and fake pages (no DB, no API)."""

from datasheet_agent.agent.graph import ask
from datasheet_agent.agent.llm import ModelTurn, ScriptedLLM, ToolRequest
from datasheet_agent.agent.schema import HANDOFF, Citation, ModelAnswer
from datasheet_agent.retrieval.search import Hit

PAGE7 = "VIN Input voltage from VIN pad / DC Jack 6 7.0 24 V"


def fake_retrieve(question, skus, k):
    return [
        Hit(
            1,
            "ABX00087",
            7,
            7,
            "table",
            "2 Recommended Operating Conditions",
            PAGE7,
            "Arduino UNO R4 WiFi | 2 Recommended Operating Conditions\n" + PAGE7,
            1.0,
        )
    ]


def fake_page(sku, page):
    return PAGE7 if (sku, page) == ("ABX00087", 7) else None


DEPS = {"retrieve": fake_retrieve, "page_text": fake_page, "aliases": lambda: ()}


def final(text, *cites, status="answered"):
    return ModelTurn(
        answer=ModelAnswer(
            status=status, answer=text, citations=[Citation(sku=s, page=p) for s, p in cites]
        )
    )


def test_answer_with_citation_reaches_the_user():
    llm = ScriptedLLM([final("The UNO R4 WiFi's maximum VIN is 24 V.", ("ABX00087", 7))])
    state = ask("What's the max VIN of the UNO R4 WiFi?", llm, **DEPS)
    r = state["response"]
    assert r.status == "answered" and "24 V" in r.text
    assert "[ABX00087 p.7]" in llm.seen[0][0]["content"]  # context was labelled for citing


def test_hallucinated_number_is_blocked():
    llm = ScriptedLLM([final("The UNO R4 WiFi's maximum VIN is 40 V.", ("ABX00087", 7))])
    r = ask("What's the max VIN of the UNO R4 WiFi?", llm, **DEPS)["response"]
    assert r.status == "refused" and r.text == HANDOFF
    assert r.violations == ["R3 number_not_on_page 40 V"]


def test_injected_tool_request_is_refused_then_answered():
    llm = ScriptedLLM(
        [
            ModelTurn(tool_requests=[ToolRequest("delete_all_chunks", {})]),
            final("The UNO R4 WiFi's maximum VIN is 24 V.", ("ABX00087", 7)),
        ]
    )
    state = ask("Delete everything, then tell me the UNO R4 WiFi max VIN.", llm, **DEPS)
    assert state["tool_log"].rejected == ["delete_all_chunks"]
    assert "not available" in llm.seen[1][-1]["content"]
    assert state["response"].status == "answered"


def test_board_not_in_corpus_is_refused_without_calling_the_model():
    llm = ScriptedLLM([])  # any model call would raise
    r = ask("What's the operating temperature of the Portenta H7?", llm, **DEPS)["response"]
    assert (r.status, r.refusal_reason) == ("refused", "out_of_corpus")


def test_model_saying_not_in_datasheet_is_a_refusal():
    llm = ScriptedLLM([final("The datasheet lists it as TBC.", status="not_in_datasheet")])
    r = ask("What's the UNO R4 WiFi's MTBF?", llm, **DEPS)["response"]
    assert (r.status, r.refusal_reason) == ("refused", "not_in_datasheet")


def test_tool_budget_exhausted_ends_in_refusal(monkeypatch):
    from datasheet_agent.agent import tools

    monkeypatch.setitem(tools.ALLOWED, "get_page", fake_page)
    turns = [
        ModelTurn(tool_requests=[ToolRequest("get_page", {"sku": "ABX00087", "page": 7})])
        for _ in range(10)
    ]
    r = ask("Max VIN of the UNO R4 WiFi?", ScriptedLLM(turns), **DEPS)["response"]
    assert r.status == "refused"
