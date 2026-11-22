"""Model interface. Real providers (OpenRouter free models, Claude Haiku) arrive in Phase 5.

A model turn returns either a final structured answer or tool requests. Tool requests go
through the allowlist in tools.py, so a model (or an injected instruction) can never run
anything but the three read-only tools.
"""

from dataclasses import dataclass, field
from typing import Protocol

from datasheet_agent.agent.schema import ModelAnswer


@dataclass
class ToolRequest:
    name: str
    args: dict


@dataclass
class ModelTurn:
    answer: ModelAnswer | None = None
    tool_requests: list[ToolRequest] = field(default_factory=list)
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0


class LLM(Protocol):
    def turn(self, system: str, messages: list[dict]) -> ModelTurn: ...


class ScriptedLLM:
    """Returns pre-written turns in order. For tests and offline demos; makes no calls."""

    def __init__(self, turns: list[ModelTurn]):
        self.turns = list(turns)
        self.seen: list[list[dict]] = []

    def turn(self, system: str, messages: list[dict]) -> ModelTurn:
        self.seen.append(list(messages))
        if not self.turns:
            raise RuntimeError("ScriptedLLM ran out of turns")
        return self.turns.pop(0)
