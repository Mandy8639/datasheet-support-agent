# Retrieval ablation (dev split, 2026-11-21)

Scored 34 of 43 dev questions (those with gold pages on the real corpus; injection_document and no-gold refusals are scored end to end later).

| Variant | recall@5 | recall@10 | MRR@10 | hits@5 | seconds |
|---|---:|---:|---:|---:|---:|
| fts | 0.382 | 0.529 | 0.271 | 13/34 | 0.3 |
| dense | 0.824 | 0.941 | 0.554 | 28/34 | 7.6 |
| hybrid | 0.765 | 0.941 | 0.556 | 26/34 | 1.5 |
| rerank | 0.912 | 0.912 | 0.728 | 31/34 | 63.1 |
| filtered | 0.912 | 0.912 | 0.741 | 31/34 | 68.0 |
| per_board | 0.941 | 0.971 | 0.764 | 32/34 | 79.3 |

recall@5 by category:

| Variant | comparison (n=4) | injection_question (n=3) | pin (n=4) | refusal (n=1) | spec_condition (n=4) | spec_number (n=12) | text_fact (n=6) |
|---|---:|---:|---:|---:|---:|---:|---:|
| fts | 0/4 | 1/3 | 2/4 | 1/1 | 3/4 | 3/12 | 3/6 |
| dense | 1/4 | 2/3 | 4/4 | 1/1 | 4/4 | 11/12 | 5/6 |
| hybrid | 0/4 | 1/3 | 4/4 | 1/1 | 4/4 | 10/12 | 6/6 |
| rerank | 1/4 | 3/3 | 4/4 | 1/1 | 4/4 | 12/12 | 6/6 |
| filtered | 1/4 | 3/3 | 4/4 | 1/1 | 4/4 | 12/12 | 6/6 |
| per_board | 2/4 | 3/3 | 4/4 | 1/1 | 4/4 | 12/12 | 6/6 |

Misses at k=5 for `per_board` (2):

- `cp01` Which accepts a higher maximum VIN, the UNO R4 WiFi or the GIGA R1 WiFi?
- `cp04` Does the Nicla Sense ME or the Nicla Vision have the lower minimum VIN?
