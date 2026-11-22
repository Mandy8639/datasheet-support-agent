#!/bin/bash
# Runs once, on the first start of an empty data volume.
# Enables pgvector and creates the agent's read-only role (least privilege:
# the agent can SELECT and nothing else; ingestion uses the admin role).
set -euo pipefail
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
     -v agent_pw="$AGENT_DB_PASSWORD" <<'SQL'
CREATE EXTENSION IF NOT EXISTS vector;
CREATE ROLE agent_ro LOGIN PASSWORD :'agent_pw';
GRANT CONNECT ON DATABASE datasheets TO agent_ro;
GRANT USAGE ON SCHEMA public TO agent_ro;
-- Tables created later by the admin role are readable, never writable.
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO agent_ro;
SQL
