"""Fill chunks.embedding with bge-small-en-v1.5 vectors of chunks.search_text.

uv run python scripts/embed.py          # chunks without an embedding
uv run python scripts/embed.py --all    # re-embed everything
"""

import argparse
import sys
import time

from datasheet_agent.db import admin_conn
from datasheet_agent.retrieval.models import EMBED_MODEL, embed_passages


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    where = "" if args.all else "WHERE embedding IS NULL"
    with admin_conn() as conn:
        rows = conn.execute(f"SELECT id, search_text FROM chunks {where} ORDER BY id").fetchall()
        if not rows:
            print("nothing to embed")
            return 0
        t0 = time.time()
        vectors = embed_passages([r[1] for r in rows])
        with conn.cursor() as cur:
            cur.executemany(
                "UPDATE chunks SET embedding = %s::vector WHERE id = %s",
                [
                    ("[" + ",".join(f"{x:.6f}" for x in v) + "]", r[0])
                    for v, r in zip(vectors, rows, strict=True)
                ],
            )
    print(f"embedded {len(rows)} chunks with {EMBED_MODEL} in {time.time() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
