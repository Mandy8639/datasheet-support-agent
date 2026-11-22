import asyncio

from fastapi.testclient import TestClient

from datasheet_agent import api
from datasheet_agent.mcp_server import server


def test_mcp_exposes_only_read_only_tools():
    listed = asyncio.run(server.list_tools())
    assert {t.name for t in listed} == {"search_datasheets", "get_spec", "get_page", "ask"}
    for t in listed:
        assert t.annotations.read_only_hint is True and t.annotations.destructive_hint is False


def test_api_ask_validates_and_returns_the_agent_row(monkeypatch):
    fake = {
        "status": "answered",
        "answer": "24 V.",
        "citations": [{"sku": "ABX00087", "page": 7}],
        "refusal_reason": None,
        "model": "m:free",
        "latency_ms": 5,
        "extra": "dropped",
    }
    monkeypatch.setattr("datasheet_agent.cli.run", lambda q: fake)
    client = TestClient(api.app)
    r = client.post("/ask", json={"question": "Max VIN of the UNO R4 WiFi?"})
    assert r.status_code == 200 and r.json()["citations"] == [{"sku": "ABX00087", "page": 7}]
    assert "extra" not in r.json()
    assert client.post("/ask", json={"question": ""}).status_code == 422
