# Retrieval ablation (test split, 2026-11-21)

Scored 64 of 77 test questions (those with gold pages on the real corpus; injection_document and no-gold refusals are scored end to end later).

| Variant | recall@5 | recall@10 | MRR@10 | hits@5 | seconds |
|---|---:|---:|---:|---:|---:|
| fts | 0.469 | 0.625 | 0.312 | 30/64 | 0.5 |
| dense | 0.812 | 0.906 | 0.682 | 52/64 | 9.4 |
| hybrid | 0.750 | 0.875 | 0.561 | 48/64 | 2.5 |
| rerank | 0.906 | 0.969 | 0.773 | 58/64 | 140.2 |
| filtered | 0.906 | 0.953 | 0.764 | 58/64 | 140.0 |
| per_board | 0.953 | 1.000 | 0.780 | 61/64 | 139.3 |

recall@5 by category:

| Variant | comparison (n=6) | injection_question (n=4) | pin (n=8) | refusal (n=4) | spec_condition (n=6) | spec_number (n=24) | text_fact (n=12) |
|---|---:|---:|---:|---:|---:|---:|---:|
| fts | 1/6 | 1/4 | 1/8 | 1/4 | 4/6 | 16/24 | 6/12 |
| dense | 0/6 | 4/4 | 6/8 | 4/4 | 5/6 | 23/24 | 10/12 |
| hybrid | 0/6 | 2/4 | 6/8 | 4/4 | 6/6 | 19/24 | 11/12 |
| rerank | 1/6 | 4/4 | 8/8 | 3/4 | 6/6 | 24/24 | 12/12 |
| filtered | 1/6 | 4/4 | 8/8 | 3/4 | 6/6 | 24/24 | 12/12 |
| per_board | 4/6 | 4/4 | 8/8 | 3/4 | 6/6 | 24/24 | 12/12 |

Misses at k=5 for `per_board` (3):

- `cp02` Between the Nano RP2040 Connect and the Nano ESP32, which is rated for the higher maximum temperature?
- `cp08` Which board runs from a lower minimum VIN, the Mega 2560 Rev3 or the UNO R4 WiFi?
- `rf06` What is the maximum power consumption of the Nano RP2040 Connect?
