"""OpenRouter provider with failover, a retry budget, a daily spend cap and attempt records.

Each model in the chain is tried in order. A rate limit (429), server error (5xx), timeout,
network error, or a reply that isn't valid JSON for the answer schema moves on to the next
model, until the attempt budget is used. Every attempt (model, outcome, latency, tokens,
cost) is recorded so the trace shows what happened.

Spend cap: with DAILY_SPEND_CAP_USD=0 only ":free" models are allowed, and any reported cost
above the cap stops further calls for the day.
"""

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

import httpx
from pydantic import ValidationError

from datasheet_agent.agent.llm import ModelTurn
from datasheet_agent.agent.schema import ModelAnswer

API = "https://openrouter.ai/api/v1/chat/completions"
ROOT = Path(__file__).resolve().parents[3]
SPEND_FILE = ROOT / "traces" / "spend.json"

ANSWER_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["status", "answer", "citations"],
    "properties": {
        "status": {"type": "string", "enum": ["answered", "not_in_datasheet"]},
        "answer": {"type": "string"},
        "citations": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["sku", "page"],
                "properties": {"sku": {"type": "string"}, "page": {"type": "integer"}},
            },
        },
    },
}


class SpendCapReached(RuntimeError):
    pass


@dataclass
class Attempt:
    model: str
    outcome: str  # ok | rate_limited | server_error | timeout | network | bad_json | http_<code>
    latency_ms: int
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    detail: str = ""


@dataclass
class SpendTracker:
    cap_usd: float
    path: Path | None = SPEND_FILE

    def __post_init__(self):
        self.path = self.path or SPEND_FILE

    def spent_today(self) -> float:
        try:
            return float(json.loads(self.path.read_text()).get(date.today().isoformat(), 0.0))
        except (FileNotFoundError, ValueError):
            return 0.0

    def add(self, usd: float) -> None:
        if usd <= 0:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = json.loads(self.path.read_text())
        except (FileNotFoundError, ValueError):
            data = {}
        today = date.today().isoformat()
        data[today] = data.get(today, 0.0) + usd
        self.path.write_text(json.dumps(data, indent=1))

    def check(self, model: str) -> None:
        if self.cap_usd <= 0 and not model.endswith(":free"):
            raise SpendCapReached(f"{model} is not a free model and the daily cap is $0")
        if self.spent_today() > self.cap_usd:
            raise SpendCapReached(f"daily spend cap ${self.cap_usd:.2f} reached")


def parse_answer(content: str) -> ModelAnswer:
    """Parse the model's JSON, tolerating a ```json fence some models add."""
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    return ModelAnswer.model_validate(json.loads(text))


@dataclass
class OpenRouterChain:
    api_key: str
    models: list[str]
    spend: SpendTracker
    max_attempts: int = 4
    timeout_s: float = 60.0
    client: httpx.Client | None = None
    last_attempts: list[Attempt] = field(default_factory=list)

    def __post_init__(self):
        if not self.models:
            raise ValueError("no models configured (OPENROUTER_MODELS)")
        self.client = self.client or httpx.Client(timeout=self.timeout_s)

    def _call(
        self, model: str, system: str, messages: list[dict]
    ) -> tuple[Attempt, ModelAnswer | None]:
        body = {
            "model": model,
            "messages": [{"role": "system", "content": system}, *messages],
            "temperature": 0,
            "max_tokens": 600,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "answer", "strict": True, "schema": ANSWER_SCHEMA},
            },
            "usage": {"include": True},
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "X-Title": "datasheet-support-agent"}
        t0 = time.monotonic()
        try:
            r = self.client.post(API, json=body, headers=headers)
        except httpx.TimeoutException:
            return Attempt(model, "timeout", int((time.monotonic() - t0) * 1000)), None
        except httpx.TransportError as e:
            return Attempt(
                model, "network", int((time.monotonic() - t0) * 1000), detail=str(e)
            ), None
        ms = int((time.monotonic() - t0) * 1000)
        if r.status_code == 429:
            return Attempt(model, "rate_limited", ms), None
        if r.status_code >= 500:
            return Attempt(model, "server_error", ms, detail=str(r.status_code)), None
        if r.status_code != 200:
            return Attempt(model, f"http_{r.status_code}", ms, detail=r.text[:200]), None
        data = r.json()
        if "error" in data:  # OpenRouter can return 200 with an upstream error object
            code = data["error"].get("code")
            outcome = "rate_limited" if code == 429 else "server_error"
            return Attempt(model, outcome, ms, detail=str(data["error"])[:200]), None
        usage = data.get("usage") or {}
        attempt = Attempt(
            model,
            "ok",
            ms,
            usage.get("prompt_tokens", 0),
            usage.get("completion_tokens", 0),
            float(usage.get("cost") or 0.0),
        )
        try:
            content = data["choices"][0]["message"]["content"] or ""
            return attempt, parse_answer(content)
        except (KeyError, IndexError, json.JSONDecodeError, ValidationError) as e:
            attempt.outcome, attempt.detail = "bad_json", str(e)[:200]
            return attempt, None

    def turn(self, system: str, messages: list[dict]) -> ModelTurn:
        self.last_attempts = []
        for i in range(self.max_attempts):
            model = self.models[i % len(self.models)]
            self.spend.check(model)
            attempt, answer = self._call(model, system, messages)
            self.last_attempts.append(attempt)
            self.spend.add(attempt.cost_usd)
            if answer is not None:
                return ModelTurn(
                    answer=answer,
                    model=model,
                    input_tokens=attempt.input_tokens,
                    output_tokens=attempt.output_tokens,
                )
        # Every attempt failed: an empty "not in datasheet" turn, so the user gets the handoff.
        return ModelTurn(
            answer=ModelAnswer(status="not_in_datasheet", answer="", citations=[]), model="none"
        )

    def attempts_as_dicts(self) -> list[dict]:
        return [asdict(a) for a in self.last_attempts]


def from_settings() -> OpenRouterChain:
    from datasheet_agent.config import get_settings

    s = get_settings()
    models = [m.strip() for m in s.openrouter_models.split(",") if m.strip()]
    return OpenRouterChain(
        s.openrouter_api_key.strip(), models, SpendTracker(s.daily_spend_cap_usd)
    )
