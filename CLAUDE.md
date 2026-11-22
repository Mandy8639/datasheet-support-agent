# Datasheet Support Agent — project context

A portfolio build: a customer-support agent that answers engineers' questions from public
Analog Devices datasheets, with every number cited to a datasheet page, hybrid retrieval,
a deterministic guardrail and a frozen evaluation set. Independent demo; not affiliated with
or endorsed by Analog Devices.

Full plan (phases, done-when checks, honesty rules):
`~/Downloads/job-agent-starter/applications/analog-devices-enterprise-ai/build-plan.md`

## Rules
- Datasheet PDFs are downloaded by `scripts/download.py` into `data/raw/` and are never committed.
- The agent uses only the read-only `agent_ro` role (`agent_conn()`); ingestion uses `admin_conn()`.
- The golden test set is frozen and hashed before any retrieval or prompt tuning. Tune on dev only;
  run test once per reported version.
- Report every metric with its denominator, including failures. Never invent results.
- One change per version when comparing techniques.
- Phases end with `make check` passing and a commit.

## Stack
Python 3.12, uv, PostgreSQL 16 + pgvector (Docker, port 5433), pytest, ruff, GitHub Actions.
Later phases: pdfplumber + PyMuPDF, Sentence Transformers (bge-small), cross-encoder reranker,
LangGraph, OpenRouter free models with failover + optional Claude Haiku behind a daily cap,
FastAPI, MCP server.

## Commands
`make up` start the DB · `make test` · `make lint` · `make check` · `make reset` wipe the DB volume
