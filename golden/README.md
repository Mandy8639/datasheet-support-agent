# Golden evaluation set

120 hand-written questions over the 18 datasheets, plus two synthetic test-only boards used to
test prompt injection. Source of truth: [`questions.yaml`](questions.yaml).
`scripts/build_golden.py` verifies every item and writes `dev.jsonl` and `test.jsonl`.

| Category | What it tests | Dev | Test |
|---|---|---:|---:|
| spec_number | one number from a spec table | 12 | 24 |
| spec_condition | a number that depends on a condition (load current, mode, supply) | 4 | 6 |
| comparison | the same spec across two boards (one is a tie) | 4 | 6 |
| text_fact | facts stated in text: chips, memory, notes | 6 | 12 |
| pin | pin tables: functions, connectors | 4 | 8 |
| refusal | not in the datasheet, listed as TBC, or a board not in the corpus | 7 | 13 |
| injection_question | instructions inside the user's question | 3 | 4 |
| injection_document | instructions planted inside a retrieved (synthetic) document | 3 | 4 |
| **Total** | | **43** | **77** |

## How items are verified

For every answerable question, against two independent sources:

1. the **PDF page text** (as loaded by `scripts/ingest.py`): the evidence quote must be on the
   page, with the expected number on the same page; gold page numbers are filled in from here;
2. **Arduino's markdown original** of that datasheet (`arduino/docs-content` at the pinned
   commit): the quote must appear, with the number on the same line or table row.

For "not in the datasheet" questions, the asked-about terms must be absent from that datasheet
(whole-word match). "TBC" questions quote the row that says TBC.

## Rules

- The split is fixed by rule (every third question of each category goes to dev), never by results.
- Tune prompts, retrieval and models on **dev only**. Run **test** once per reported version.
- `test.jsonl` is hashed into `test.sha256` when frozen; a test fails if it changes afterwards.
- No test question or evidence quote may appear in code, prompts or few-shot examples (tested).
- Injection canaries: `CANARY-7F3A` (to be placed in the agent's system prompt in Phase 4),
  `CANARY-DOC-91` and `CANARY-DOC-37` (planted in the fixtures). None may appear in an answer.

## License

Questions, quotes and values are derived from Arduino datasheets: © Arduino S.r.l., CC BY-SA 4.0.
This folder is shared under the same license.
