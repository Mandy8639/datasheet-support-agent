import psycopg
import pytest

from datasheet_agent.config import get_settings


def _db_reachable() -> bool:
    try:
        with psycopg.connect(get_settings().database_url, connect_timeout=2):
            return True
    except psycopg.OperationalError:
        return False


def pytest_collection_modifyitems(config, items):
    if _db_reachable():
        return
    skip = pytest.mark.skip(reason="Postgres not reachable; run `make up`")
    for item in items:
        if "db" in item.keywords:
            item.add_marker(skip)
