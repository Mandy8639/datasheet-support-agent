"""Structured answer the model must return, and the final response shown to the user."""

from typing import Literal

from pydantic import BaseModel, Field

HANDOFF = (
    "I can't confirm that from the datasheet. Please ask on the Arduino Forum "
    "(forum.arduino.cc), where Arduino staff and the community answer hardware questions."
)


class Citation(BaseModel):
    sku: str = Field(description="Datasheet SKU, e.g. ABX00087")
    page: int = Field(ge=1, description="PDF page number the fact is on")


class ModelAnswer(BaseModel):
    """What the model returns. Every number in `answer` must be on a cited page."""

    status: Literal["answered", "not_in_datasheet"]
    answer: str = Field(description="One or two sentences for the engineer.")
    citations: list[Citation] = Field(default_factory=list)


class Response(BaseModel):
    """What the user receives after the guardrail."""

    status: Literal["answered", "refused"]
    text: str
    citations: list[Citation] = Field(default_factory=list)
    refusal_reason: str | None = None  # not_in_datasheet | out_of_corpus | guardrail
    violations: list[str] = Field(default_factory=list)  # guardrail findings, for traces
