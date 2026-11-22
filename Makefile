.PHONY: setup up down reset test lint fmt check

setup:            ## create .env from the example and install dependencies
	@test -f .env || cp .env.example .env
	uv sync

up: setup         ## start Postgres + pgvector and wait until healthy
	docker compose --env-file .env up -d --wait db

down:
	docker compose --env-file .env down

reset:            ## drop the data volume (re-runs db/init on next up)
	docker compose --env-file .env down -v

test:
	uv run pytest -q

lint:
	uv run ruff check .
	uv run ruff format --check .

fmt:
	uv run ruff check --fix .
	uv run ruff format .

check: lint test
