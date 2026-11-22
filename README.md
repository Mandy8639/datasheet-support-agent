# Datasheet Support Agent

Answers engineers' questions about hardware from the product datasheets, citing the datasheet page
for every number, and refuses (with a pointer to the vendor forum) when the datasheet doesn't say.

**Status:** Phase 4 of 7 done: agent, tools and guardrail (tested offline with a scripted model). Next: real models with failover. Retrieval, agent and evaluation results will be
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

## Golden set (Phase 2)

120 hand-written questions (43 dev, 77 test) across spec numbers, conditional specs, comparisons,
text facts, pins, refusals (not in the datasheet, TBC, board not in corpus) and prompt injection
(in the question, and planted inside synthetic test-only documents). Every answer is verified
against both the PDF page and Arduino's markdown original before it can enter the set. See
[`golden/README.md`](golden/README.md).

## Retrieval (Phase 3)

Every chunk's searchable text carries its board and section (`Arduino UNO R4 WiFi | 2 Recommended
Operating Conditions`). Query understanding finds the boards named in a question from the names
and aliases in `data/sources.toml`, and flags board names that aren't in the corpus
(e.g. "Portenta H7") so the agent can refuse rather than answer from another datasheet.

Ablation, one change per row, on the **frozen test split** (run once; developed on dev only).
A question counts as retrieved when every gold page (both boards, for comparisons) is in the top k.

| Variant | recall@5 | recall@10 | MRR@10 |
|---|---:|---:|---:|
| Full-text search (Postgres) | 0.469 | 0.625 | 0.312 |
| Dense (bge-small, pgvector) | 0.812 | 0.906 | 0.682 |
| Hybrid (reciprocal rank fusion) | 0.750 | 0.875 | 0.561 |
| + cross-encoder rerank (bge-reranker-base) | 0.906 | 0.969 | 0.773 |
| + board filter from query understanding | 0.906 | 0.953 | 0.764 |
| + per-board decomposition for multi-board questions | **0.953** | **1.000** | **0.780** |

n = 64 test questions (the 13 others are injection-in-document and no-gold refusals, scored end to
end in Phase 6). Full tables and misses: [`reports/retrieval-test.md`](reports/retrieval-test.md);
dev: [`reports/retrieval-dev.md`](reports/retrieval-dev.md).

What the numbers say, including what didn't work:

- **Hybrid fusion was worse than dense alone** here (0.750 vs 0.812): full-text search is weak on
  this corpus (short spec rows, abbreviations like VIN/TOP), so fusing it in adds noise. The
  reranker recovers the loss.
- **The board filter added nothing measurable** on single-board questions once the reranker is
  in (0.906 both); it matters for correctness (no answers from the wrong datasheet), not recall.
- **Comparisons were the real gap**: with both board names in the query, the reranker scored any
  chunk naming a board highly. Decomposing into one sub-search per board, with board names
  removed (the filter already fixes the board), took comparisons from 1/6 to 4/6 at k=5.
- Remaining misses at k=5: two comparisons where one board's gold page ranks just outside its
  share of the 5 slots, and one "TBC" row. All 64 are found by k=10.
- Cost: reranking runs a 278M-parameter cross-encoder locally; about 2 s per question on a
  laptop (Apple MPS), versus 0.15 s for dense alone. A production version would cache, shrink
  the candidate pool, or use a smaller reranker.

## Agent, tools and guardrail (Phase 4)

A LangGraph flow: `understand → retrieve → answer → guardrail`, with a direct refusal when the
question names a board that isn't in the corpus (no model call is made).

- **Three read-only tools**, enforced by an allowlist: `search_datasheets` (the Phase 3
  per-board retriever), `get_spec` (spec-table rows) and `get_page` (a full page). They use the
  `agent_ro` database role, which can't write. Any other tool name (for example a "delete" tool
  named in an injected instruction) is refused and logged; at most 4 tool calls per question.
- **Structured output**: the model must return `status`, a one- or two-sentence `answer` and
  `citations` (SKU + page). Prompt: [`prompts/system.md`](prompts/system.md); its few-shot example
  uses a made-up board so no evaluation data can leak in (tested).
- **Deterministic guardrail** ([`agent/guardrail.py`](src/datasheet_agent/agent/guardrail.py)),
  run on every answer. Any violation replaces the answer with a refusal and a pointer to the
  Arduino Forum:

| Rule | Check |
|---|---|
| R1 | an answer cites at least one page |
| R2 | every cited page was actually retrieved |
| R3 | every number in the answer is on a cited page, with a compatible unit (300 mA = 0.3 A); digits in board names, SKUs and part numbers are ignored |
| R4 | cited boards are the boards the question asked about |
| R5 | no internal canary markers in the output (prompt-leak check) |
| R6 | no links or domains |
| R7 | a question about a board not in the corpus is refused |

Tests cover each rule with a passing and a failing case, the tool allowlist and call budget, and
the whole graph with a scripted model (answer, blocked hallucination, rejected injected tool
call, out-of-corpus refusal, tool-budget exhaustion), with no database or API needed.

## Run

```bash
make ingest   # starts Postgres + pgvector, downloads the corpus, loads it
make check    # lint + tests
make eval-retrieval        # retrieval ablation on dev (test: --split test, once)
```

The agent connects with a read-only database role (`agent_ro`); a test checks it cannot write.
