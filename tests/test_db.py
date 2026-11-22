"""Phase 0 smoke tests: pgvector is installed and the agent role is read-only."""

import psycopg
import pytest

from datasheet_agent.db import admin_conn, agent_conn

pytestmark = pytest.mark.db


def test_pgvector_extension_installed():
    with admin_conn() as conn:
        sql = "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
        row = conn.execute(sql).fetchone()
    assert row is not None


def test_vector_distance_works():
    with admin_conn() as conn:
        dist = conn.execute("SELECT '[1,0,0]'::vector <=> '[0,1,0]'::vector").fetchone()[0]
    assert dist == pytest.approx(1.0)


def test_agent_role_can_read_but_not_write():
    with admin_conn() as conn:
        conn.execute("DROP TABLE IF EXISTS _phase0_probe")
        conn.execute("CREATE TABLE _phase0_probe (id int)")
        conn.execute("INSERT INTO _phase0_probe VALUES (1)")
    try:
        with agent_conn() as conn:
            assert conn.execute("SELECT count(*) FROM _phase0_probe").fetchone()[0] == 1
        with agent_conn() as conn, pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.read_only = False  # even without the session flag, the role can't write
            conn.execute("INSERT INTO _phase0_probe VALUES (2)")
    finally:
        with admin_conn() as conn:
            conn.execute("DROP TABLE _phase0_probe")
