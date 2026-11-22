-- Corpus schema. Applied (idempotently) by scripts/ingest.py with the admin role.
-- The agent's read-only role gets SELECT through the default privileges set in db/init.

CREATE TABLE IF NOT EXISTS documents (
    id          serial PRIMARY KEY,
    sku         text NOT NULL UNIQUE,
    product     text NOT NULL,
    sha256      text NOT NULL,
    page_count  int  NOT NULL,
    source_url  text NOT NULL,
    source_md   text NOT NULL,      -- CC BY-SA original in arduino/docs-content
    license     text NOT NULL
);

CREATE TABLE IF NOT EXISTS pages (
    doc_id   int  NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_no  int  NOT NULL,
    text     text NOT NULL,          -- full page text, tables included (used by the guardrail)
    PRIMARY KEY (doc_id, page_no)
);

-- Every table pdfplumber finds, classified. Rows are kept as cleaned cell strings.
CREATE TABLE IF NOT EXISTS doc_tables (
    id         serial PRIMARY KEY,
    doc_id     int  NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_no    int  NOT NULL,
    table_idx  int  NOT NULL,        -- order on the page
    kind       text NOT NULL,        -- spec | pin | bom | feature | rohs | link | changelog | note | other
    section    text NOT NULL,        -- nearest heading above the table
    header     jsonb NOT NULL,
    rows       jsonb NOT NULL,
    UNIQUE (doc_id, page_no, table_idx)
);

-- Rows of Min/Typ/Max spec tables, with raw strings kept next to parsed numbers.
CREATE TABLE IF NOT EXISTS spec_rows (
    id          serial PRIMARY KEY,
    doc_id      int  NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    table_id    int  NOT NULL REFERENCES doc_tables(id) ON DELETE CASCADE,
    page_no     int  NOT NULL,
    section     text NOT NULL,
    symbol      text,
    parameter   text NOT NULL,
    min_raw     text, typ_raw text, max_raw text,
    min_val     double precision, typ_val double precision, max_val double precision,
    unit        text,                -- as printed
    si_unit     text,                -- normalized unit (V, A, Hz, degC, B, W, ...)
    si_factor   double precision     -- multiply *_val by this to get si_unit
);

CREATE TABLE IF NOT EXISTS pin_rows (
    id          serial PRIMARY KEY,
    doc_id      int  NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    table_id    int  NOT NULL REFERENCES doc_tables(id) ON DELETE CASCADE,
    page_no     int  NOT NULL,
    section     text NOT NULL,       -- usually the connector name, e.g. "JANALOG"
    pin         text NOT NULL,
    function    text,
    type        text,
    description text
);

-- Retrieval units: section text and rendered tables. Embeddings are filled in Phase 3.
CREATE TABLE IF NOT EXISTS chunks (
    id         serial PRIMARY KEY,
    doc_id     int  NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_no    int  NOT NULL,        -- page where the chunk starts
    page_end   int  NOT NULL,
    section    text NOT NULL,
    kind       text NOT NULL,        -- text | table
    text       text NOT NULL,
    -- "product | section" + text: what full-text search and embeddings see, so a chunk that only
    -- says "Input voltage from VIN pad" still carries which board it belongs to.
    search_text text NOT NULL,
    tsv        tsvector GENERATED ALWAYS AS (to_tsvector('english', search_text)) STORED,
    embedding  vector(384)
);

CREATE INDEX IF NOT EXISTS chunks_tsv_idx ON chunks USING gin (tsv);
CREATE INDEX IF NOT EXISTS spec_rows_doc_idx ON spec_rows (doc_id);
CREATE INDEX IF NOT EXISTS pin_rows_doc_idx ON pin_rows (doc_id);
