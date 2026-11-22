"""Database connections. The agent only ever gets the read-only connection."""

from contextlib import contextmanager

import psycopg

from datasheet_agent.config import get_settings


@contextmanager
def admin_conn():
    """Writable connection for ingestion scripts. Never pass this to the agent."""
    with psycopg.connect(get_settings().database_url) as conn:
        yield conn


@contextmanager
def agent_conn():
    """Read-only connection for the agent's tools."""
    with psycopg.connect(get_settings().agent_database_url) as conn:
        conn.read_only = True
        yield conn
