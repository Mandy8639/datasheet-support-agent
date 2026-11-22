# Datasheet Support Agent

Answers engineers' questions about hardware from the product datasheets, citing the datasheet page
for every number, and refuses (with a pointer to the vendor forum) when the datasheet doesn't say.

**Status:** Phase 1 of 7: corpus and ingestion. Retrieval, agent and evaluation results will be
added here as they are measured.

## Corpus and license

18 Arduino product datasheets (boards, carriers and modules: UNO, Nano, MKR, Portenta, Nicla, GIGA).

- Arduino documentation is licensed **CC BY-SA 4.0**. Each PDF's markdown original is listed in
  [`data/sources.toml`](data/sources.toml) with the pinned `arduino/docs-content` commit.
- PDFs are downloaded by `scripts/download.py` and are **not** stored in this repository; their
  SHA-256 checksums are in [`data/checksums.json`](data/checksums.json).
- Data derived from the datasheets (extracted rows, evaluation questions and answers) is shared
  under CC BY-SA 4.0 with attribution: *Datasheets © Arduino S.r.l., CC BY-SA 4.0*.
- Why not a chip vendor's datasheets? The vendor I first targeted prohibits automated download and
  data extraction in its website terms, so this demo uses openly licensed datasheets instead.

Independent demo. Not affiliated with or endorsed by Arduino.

## Ingestion (Phase 1)

`scripts/ingest.py` parses each PDF with pdfplumber into:

- **pages** (full text, used later by the citation guardrail)
- **sections** (from the datasheets' heading fonts; running header/footer and table of contents removed)
- **tables**, classified (spec, pin, BOM, feature, RF, note, RoHS, ...), kept out of body text so
  nothing is indexed twice
- **spec rows** from Min/Typ/Max tables: raw strings kept next to parsed numbers, units normalized
  (`mA`→A, `°C`→degC, values like `-40 °C (-40 °F)` split into number and unit)
- **pin rows** from pin tables
- **chunks** for retrieval: section text up to 1,200 characters, plus one chunk per useful table

Current counts: [`reports/ingestion.md`](reports/ingestion.md) (343 pages, 112 spec rows,
858 pin rows, 714 chunks).

Check: `tests/test_spec_extraction.py` compares 21 parsed spec rows with values copied by hand from
Arduino's markdown originals, so the parser is checked against an independent source (21/21 pass).

## Run

```bash
make ingest   # starts Postgres + pgvector, downloads the corpus, loads it
make check    # lint + tests
```

The agent connects with a read-only database role (`agent_ro`); a test checks it cannot write.
