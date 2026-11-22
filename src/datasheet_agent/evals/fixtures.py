"""Load the synthetic injection fixtures for an evaluation run, and always remove them after."""

import json
from contextlib import contextmanager
from pathlib import Path

from datasheet_agent.db import admin_conn
from datasheet_agent.retrieval.models import embed_passages

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "golden" / "fixtures" / "injection_docs.json"


def _vec(v) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in v) + "]"


def remove_fixtures() -> int:
    with admin_conn() as conn:
        return conn.execute("DELETE FROM documents WHERE is_fixture").rowcount


@contextmanager
def injection_fixtures():
    docs = json.loads(FIXTURES.read_text())["documents"]
    remove_fixtures()  # in case an earlier run was interrupted
    try:
        with admin_conn() as conn:
            conn.execute((ROOT / "db" / "schema.sql").read_text())
            for d in docs:
                doc_id = conn.execute(
                    """INSERT INTO documents (sku, product, sha256, page_count, source_url,
                       source_md, license, is_fixture)
                       VALUES (%s, %s, 'fixture', %s, 'golden/fixtures/injection_docs.json',
                       '-', 'synthetic', true) RETURNING id""",
                    (d["sku"], d["product"], len(d["pages"])),
                ).fetchone()[0]
                pages = sorted((int(n), t) for n, t in d["pages"].items())
                texts = [f"{d['product']} | page {n}\n{t}" for n, t in pages]
                for (n, t), st, v in zip(pages, texts, embed_passages(texts), strict=True):
                    conn.execute(
                        "INSERT INTO pages (doc_id, page_no, text) VALUES (%s,%s,%s)",
                        (doc_id, n, t),
                    )
                    conn.execute(
                        """INSERT INTO chunks (doc_id, page_no, page_end, section, kind, text,
                           search_text, embedding) VALUES (%s,%s,%s,%s,'text',%s,%s,%s::vector)""",
                        (doc_id, n, n, f"page {n}", t, st, _vec(v)),
                    )
        yield [d["sku"] for d in docs]
    finally:
        remove_fixtures()
