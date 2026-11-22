import pytest

from datasheet_agent.agent import tools


def test_unlisted_tool_is_rejected_and_logged():
    log = tools.ToolLog()
    out = tools.call_tool("delete_chunks", {"all": True}, log)
    assert out == {"error": "tool 'delete_chunks' is not available"}
    assert log.rejected == ["delete_chunks"] and log.calls == []


def test_tool_call_budget(monkeypatch):
    monkeypatch.setitem(tools.ALLOWED, "get_page", lambda sku, page: "text")
    log = tools.ToolLog()
    for _ in range(tools.MAX_TOOL_CALLS):
        assert tools.call_tool("get_page", {"sku": "X", "page": 1}, log) == "text"
    assert tools.call_tool("get_page", {"sku": "X", "page": 1}, log)["error"]
    assert len(log.calls) == tools.MAX_TOOL_CALLS


def test_only_three_read_only_tools_exist():
    assert set(tools.ALLOWED) == {"search_datasheets", "get_spec", "get_page"}


@pytest.mark.db
def test_get_spec_and_get_page_read_the_corpus():
    rows = tools.get_spec("ABX00087", "Input voltage from VIN")
    if not rows:
        pytest.skip("corpus not ingested; run `make ingest`")
    assert rows[0]["max"] == "24" and rows[0]["unit"] == "V" and rows[0]["page"] == 7
    assert "Input voltage from VIN pad" in tools.get_page("ABX00087", 7)
    assert tools.get_page("ABX00087", 999) is None
