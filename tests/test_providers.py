"""Failover, spend cap and traces, with OpenRouter replaced by a local mock (no network)."""

import json

import httpx
import pytest

from datasheet_agent.agent.providers import (
    OpenRouterChain,
    SpendCapReached,
    SpendTracker,
    parse_answer,
)

GOOD = {
    "status": "answered",
    "answer": "Max VIN is 24 V.",
    "citations": [{"sku": "ABX00087", "page": 7}],
}


def ok_body(content, cost=0.0):
    return {
        "choices": [{"message": {"content": content}}],
        "usage": {"prompt_tokens": 120, "completion_tokens": 20, "cost": cost},
    }


def chain(handler, models=("a/model-a:free", "b/model-b:free"), tmp_path=None, cap=0.0, attempts=4):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    spend = SpendTracker(cap, path=(tmp_path / "spend.json") if tmp_path else None)
    return OpenRouterChain("test-key", list(models), spend, max_attempts=attempts, client=client)


def by_model(responses):
    def handler(request):
        model = json.loads(request.content)["model"]
        status, body = responses[model]
        return httpx.Response(status, json=body)

    return handler


def test_forced_429_fails_over_to_next_model(tmp_path):
    c = chain(
        by_model(
            {
                "a/model-a:free": (429, {"error": "rate limited"}),
                "b/model-b:free": (200, ok_body(json.dumps(GOOD))),
            }
        ),
        tmp_path=tmp_path,
    )
    turn = c.turn("system", [{"role": "user", "content": "q"}])
    assert turn.model == "b/model-b:free" and turn.answer.answer == "Max VIN is 24 V."
    assert [(a.model, a.outcome) for a in c.last_attempts] == [
        ("a/model-a:free", "rate_limited"),
        ("b/model-b:free", "ok"),
    ]


def test_bad_json_and_server_errors_also_fail_over(tmp_path):
    c = chain(
        by_model(
            {"a/model-a:free": (200, ok_body('{"status": "answ')), "b/model-b:free": (503, {})}
        ),
        tmp_path=tmp_path,
        attempts=2,
    )
    turn = c.turn("system", [])
    assert [a.outcome for a in c.last_attempts] == ["bad_json", "server_error"]
    assert turn.model == "none" and turn.answer.status == "not_in_datasheet"  # -> handoff


def test_upstream_error_inside_http_200(tmp_path):
    c = chain(
        by_model(
            {
                "a/model-a:free": (200, {"error": {"code": 429, "message": "upstream"}}),
                "b/model-b:free": (200, ok_body(json.dumps(GOOD))),
            }
        ),
        tmp_path=tmp_path,
    )
    c.turn("system", [])
    assert c.last_attempts[0].outcome == "rate_limited"


def test_retry_budget_cycles_models_then_stops(tmp_path):
    calls = []

    def handler(request):
        calls.append(json.loads(request.content)["model"])
        return httpx.Response(429, json={})

    c = chain(handler, tmp_path=tmp_path, attempts=3)
    c.turn("system", [])
    assert calls == ["a/model-a:free", "b/model-b:free", "a/model-a:free"]


def test_zero_cap_refuses_paid_models(tmp_path):
    c = chain(
        lambda r: httpx.Response(200, json=ok_body(json.dumps(GOOD))),
        models=("anthropic/claude-haiku",),
        tmp_path=tmp_path,
    )
    with pytest.raises(SpendCapReached):
        c.turn("system", [])


def test_spend_cap_stops_calls_once_exceeded(tmp_path):
    c = chain(
        lambda r: httpx.Response(200, json=ok_body(json.dumps(GOOD), cost=0.6)),
        models=("p/paid",),
        tmp_path=tmp_path,
        cap=1.0,
    )
    c.turn("s", [])
    c.turn("s", [])  # 1.2 spent, over the cap
    with pytest.raises(SpendCapReached):
        c.turn("s", [])
    assert c.spend.spent_today() == pytest.approx(1.2)


def test_parse_answer_accepts_fenced_json():
    assert parse_answer("```json\n" + json.dumps(GOOD) + "\n```").status == "answered"


def test_request_asks_for_strict_json_schema_and_usage(tmp_path):
    seen = {}

    def handler(request):
        seen.update(json.loads(request.content))
        return httpx.Response(200, json=ok_body(json.dumps(GOOD)))

    chain(handler, tmp_path=tmp_path).turn("system", [])
    assert seen["response_format"]["json_schema"]["strict"] is True
    assert seen["usage"] == {"include": True} and seen["temperature"] == 0


def test_trace_records_failover(tmp_path):
    from datasheet_agent.agent.graph import ask
    from datasheet_agent.agent.trace import record
    from tests.test_graph import DEPS

    c = chain(
        by_model({"a/model-a:free": (429, {}), "b/model-b:free": (200, ok_body(json.dumps(GOOD)))}),
        tmp_path=tmp_path,
    )
    state = ask("Max VIN of the UNO R4 WiFi?", c, **DEPS)
    row = record(state, c.attempts_as_dicts(), started=0.0, trace_dir=tmp_path)
    assert row["model"] == "b/model-b:free" and row["failovers"] == 1
    assert row["status"] == "answered" and row["input_tokens"] == 120
    assert (tmp_path / next(p.name for p in tmp_path.glob("*.jsonl"))).read_text().count("\n") == 1
