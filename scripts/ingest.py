"""Parse every datasheet in data/raw/ and load it into Postgres (admin role).

Re-running replaces a document's rows, so the database always matches data/raw/.
Writes reports/ingestion.md with per-datasheet counts.

    uv run python scripts/ingest.py
"""

import json
import sys
import tomllib
from collections import Counter
from pathlib import Path

from psycopg.types.json import Jsonb

from datasheet_agent.db import admin_conn
from datasheet_agent.ingest.chunker import chunk_section, table_chunk
from datasheet_agent.ingest.pdf import parse_pdf
from datasheet_agent.ingest.tables import pin_rows, spec_rows

ROOT = Path(__file__).resolve().parents[1]
# bom/rohs/link/changelog/company/cert tables are stored but not used for retrieval.
CHUNK_TABLE_KINDS = {"spec", "pin", "feature", "rf", "note", "other"}


def ingest_one(conn, cfg: dict, ds: dict, checksums: dict) -> dict:
    sku = ds["sku"]
    parsed = parse_pdf(ROOT / "data" / "raw" / f"{sku}.pdf")
    conn.execute("DELETE FROM documents WHERE sku = %s", (sku,))
    doc_id = conn.execute(
        """INSERT INTO documents (sku, product, sha256, page_count, source_url, source_md, license)
           VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id""",
        (
            sku,
            ds["product"],
            checksums[sku]["sha256"],
            len(parsed.pages),
            cfg["url_template"].format(sku=sku),
            ds["source_md"],
            cfg["license"],
        ),
    ).fetchone()[0]

    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO pages (doc_id, page_no, text) VALUES (%s, %s, %s)",
            [(doc_id, n, t) for n, t in parsed.pages.items()],
        )

    n_spec = n_pin = 0
    chunks = [c for s in parsed.sections for c in chunk_section(s)]
    for t in parsed.tables:
        table_id = conn.execute(
            """INSERT INTO doc_tables (doc_id, page_no, table_idx, kind, section, header, rows)
               VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id""",
            (doc_id, t.page_no, t.table_idx, t.kind, t.section, Jsonb(t.header), Jsonb(t.rows)),
        ).fetchone()[0]
        if t.kind == "spec":
            for r in spec_rows(t):
                (mn, ty, mx), (si_unit, factor) = r.values, r.si
                conn.execute(
                    """INSERT INTO spec_rows (doc_id, table_id, page_no, section, symbol, parameter,
                       min_raw, typ_raw, max_raw, min_val, typ_val, max_val, unit, si_unit,
                       si_factor)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        doc_id,
                        table_id,
                        r.page_no,
                        r.section,
                        r.symbol,
                        r.parameter,
                        r.min_raw,
                        r.typ_raw,
                        r.max_raw,
                        mn,
                        ty,
                        mx,
                        r.unit,
                        si_unit,
                        factor,
                    ),
                )
                n_spec += 1
        elif t.kind == "pin":
            for r in pin_rows(t):
                conn.execute(
                    """INSERT INTO pin_rows (doc_id, table_id, page_no, section, pin, function,
                       type, description) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        doc_id,
                        table_id,
                        r.page_no,
                        r.section,
                        r.pin,
                        r.function,
                        r.type,
                        r.description,
                    ),
                )
                n_pin += 1
        if t.kind in CHUNK_TABLE_KINDS:
            chunks.append(table_chunk(t))

    with conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO chunks (doc_id, page_no, page_end, section, kind, text)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            [(doc_id, c.page_no, c.page_end, c.section, c.kind, c.text) for c in chunks],
        )

    return {
        "sku": sku,
        "product": ds["product"],
        "pages": len(parsed.pages),
        "toc_pages": parsed.toc_pages,
        "sections": len(parsed.sections),
        "tables": dict(Counter(t.kind for t in parsed.tables)),
        "spec_rows": n_spec,
        "pin_rows": n_pin,
        "chunks": len(chunks),
        "unknown_units": sorted(
            {
                r.unit
                for t in parsed.tables
                if t.kind == "spec"
                for r in spec_rows(t)
                if r.unit and r.si[0] is None
            }
        ),
    }


def write_report(results: list[dict]) -> Path:
    out = ROOT / "reports" / "ingestion.md"
    out.parent.mkdir(exist_ok=True)
    tot = Counter()
    lines = [
        "# Ingestion report",
        "",
        "Generated by `scripts/ingest.py`. Corpus: Arduino datasheets (CC BY-SA 4.0), see "
        "`data/sources.toml`.",
        "",
        "| SKU | Product | Pages | Sections | Tables | Spec rows | Pin rows | Chunks |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in results:
        n_tables = sum(r["tables"].values())
        lines.append(
            f"| {r['sku']} | {r['product']} | {r['pages']} | {r['sections']} | "
            f"{n_tables} | {r['spec_rows']} | {r['pin_rows']} | {r['chunks']} |"
        )
        tot.update(
            pages=r["pages"],
            sections=r["sections"],
            tables=n_tables,
            spec=r["spec_rows"],
            pin=r["pin_rows"],
            chunks=r["chunks"],
        )
    lines.append(
        f"| **Total** | {len(results)} datasheets | {tot['pages']} | {tot['sections']} | "
        f"{tot['tables']} | {tot['spec']} | {tot['pin']} | {tot['chunks']} |"
    )
    kinds = Counter()
    for r in results:
        kinds.update(r["tables"])
    lines += ["", "Tables by kind: " + ", ".join(f"{k} {v}" for k, v in kinds.most_common()), ""]
    unknown = sorted({u for r in results for u in r["unknown_units"]})
    lines.append("Spec units not normalized: " + (", ".join(unknown) if unknown else "none"))
    with admin_conn() as conn:
        total, no_num = conn.execute(
            """SELECT count(*), count(*) FILTER (WHERE min_val IS NULL AND typ_val IS NULL
               AND max_val IS NULL) FROM spec_rows"""
        ).fetchone()
    lines.append(
        f"Spec rows with no parseable number (TBC, expressions like 0.7*VDDIO): "
        f"{no_num} of {total}; raw text is kept for these."
    )
    lines += [
        "",
        "Extraction check: `tests/test_spec_extraction.py` compares 21 spec rows with "
        "Arduino's markdown sources (independent of this parser).",
    ]
    out.write_text("\n".join(lines) + "\n")
    return out


def main() -> int:
    cfg = tomllib.loads((ROOT / "data" / "sources.toml").read_text())
    checksums = json.loads((ROOT / "data" / "checksums.json").read_text())
    with admin_conn() as conn:
        conn.execute((ROOT / "db" / "schema.sql").read_text())
        results = []
        for ds in cfg["datasheet"]:
            results.append(ingest_one(conn, cfg, ds, checksums))
            r = results[-1]
            print(
                f"{r['sku']:9} pages={r['pages']:3} spec={r['spec_rows']:3} "
                f"pin={r['pin_rows']:3} chunks={r['chunks']:3}"
            )
    print(f"report: {write_report(results).relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
