"""HTTP API.

uv run uvicorn datasheet_agent.api:app --port 8000
curl -s localhost:8000/ask -H 'content-type: application/json' -d '{"question": "..."}'
"""

from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="Datasheet Support Agent", version="0.1.0")


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class AskResponse(BaseModel):
    status: str
    answer: str
    citations: list[dict]
    refusal_reason: str | None
    model: str | None
    latency_ms: int


@app.get("/health")
def health() -> dict:
    from datasheet_agent.db import agent_conn

    with agent_conn() as conn:
        docs = conn.execute("SELECT count(*) FROM documents WHERE NOT is_fixture").fetchone()[0]
    return {"status": "ok", "datasheets": docs}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    from datasheet_agent.cli import run

    row = run(req.question)
    return AskResponse(**{k: row[k] for k in AskResponse.model_fields})
