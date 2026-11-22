"""LLM-as-judge for answer correctness, used alongside (never instead of) deterministic scores.

The judge sees the question, the expected answer, the datasheet quote it comes from and the
agent's answer, and returns correct / incorrect with a one-line reason. It is validated
against human labels before its numbers are reported (scripts/judge.py).
"""

import json
from dataclasses import dataclass

import httpx

from datasheet_agent.agent.providers import API, SpendTracker

JUDGE_SYSTEM = """You grade answers from a hardware datasheet assistant.
You get: the user's question, the expected answer, the datasheet quote it comes from, and
the assistant's answer. Decide whether the assistant's answer is correct: it must state the
expected fact (same value and unit, or the same board as the winner of a comparison, or the
same component), must not contradict it, and must not add a wrong figure. Wording may differ.
Return JSON: {"verdict": "correct" | "incorrect", "reason": "<one short sentence>"}."""

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["verdict", "reason"],
    "properties": {
        "verdict": {"type": "string", "enum": ["correct", "incorrect"]},
        "reason": {"type": "string"},
    },
}


def expected_text(ans: dict) -> str:
    t = ans["type"]
    if t == "number":
        return f"{ans['value']} {ans['unit']} ({ans['bound']})"
    if t == "range":
        return f"{ans['min']} to {ans['max']} {ans['unit']}"
    if t == "text":
        return "must mention: " + ", ".join(ans["must_include"])
    if t == "choice":
        return (
            f"both are equal at {ans['value']} {ans['unit']}"
            if ans.get("tie")
            else f"the winner is board {ans['sku']}"
        )
    return "the assistant should say the datasheet doesn't give this"


@dataclass
class Verdict:
    correct: bool | None  # None = the judge failed to answer
    reason: str
    model: str


@dataclass
class Judge:
    api_key: str
    models: list[str]
    spend: SpendTracker
    client: httpx.Client | None = None

    def __post_init__(self):
        self.client = self.client or httpx.Client(timeout=60)

    def grade(self, item: dict, answer: str) -> Verdict:
        quotes = "; ".join(f'{g["sku"]}: "{g["evidence"]}"' for g in item.get("gold", []))
        user = (
            f"Question: {item['question']}\nExpected answer: {expected_text(item['answer'])}\n"
            f"Datasheet quote: {quotes or '(none)'}\nAssistant's answer: {answer}"
        )
        for model in self.models:
            self.spend.check(model)
            body = {
                "model": model,
                "temperature": 0,
                "max_tokens": 200,
                "messages": [
                    {"role": "system", "content": JUDGE_SYSTEM},
                    {"role": "user", "content": user},
                ],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {"name": "verdict", "strict": True, "schema": SCHEMA},
                },
            }
            try:
                r = self.client.post(
                    API, json=body, headers={"Authorization": f"Bearer {self.api_key}"}
                )
                data = r.json()
                v = json.loads(
                    data["choices"][0]["message"]["content"].strip().strip("`").removeprefix("json")
                )
                return Verdict(v["verdict"] == "correct", v["reason"], model)
            except (httpx.HTTPError, KeyError, IndexError, ValueError, TypeError, AttributeError):
                # empty reply, error object or bad JSON: try the next judge model
                continue
        return Verdict(None, "judge unavailable", "none")
