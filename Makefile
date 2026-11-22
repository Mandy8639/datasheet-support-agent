.PHONY: setup up down reset download ingest embed golden eval-retrieval test lint fmt check

setup:            ## create .env from the example and install dependencies
	@test -f .env || cp .env.example .env
	uv sync

up: setup         ## start Postgres + pgvector and wait until healthy
	docker compose --env-file .env up -d --wait db

down:
	docker compose --env-file .env down

reset:            ## drop the data volume (re-runs db/init on next up)
	docker compose --env-file .env down -v

download:         ## fetch the corpus PDFs (CC BY-SA 4.0, see data/sources.toml)
	uv run python scripts/download.py

ingest: up download  ## parse PDFs and load Postgres; writes reports/ingestion.md
	uv run python scripts/ingest.py
	uv run python scripts/embed.py

embed:            ## embed chunks with bge-small-en-v1.5 (local)
	uv run python scripts/embed.py

eval-retrieval:   ## retrieval ablation on the dev split
	uv run python scripts/eval_retrieval.py

golden:           ## verify questions.yaml against the PDFs and markdown originals; write dev/test
	uv run python scripts/build_golden.py

test:
	uv run pytest -q

lint:
	uv run ruff check .
	uv run ruff format --check .

fmt:
	uv run ruff check --fix .
	uv run ruff format .

check: lint test
