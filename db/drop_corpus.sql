-- Used only by `scripts/ingest.py --rebuild` after a schema change. Everything here is derived
-- from the PDFs in data/raw/ and is recreated in the same run.
DROP TABLE IF EXISTS chunks, pin_rows, spec_rows, doc_tables, pages, documents CASCADE;
