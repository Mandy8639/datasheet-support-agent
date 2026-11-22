# Retrieval ablation (test split, 2026-11-21)

Scored 64 of 77 test questions (those with gold pages on the real corpus; injection_document and no-gold refusals are scored end to end later).

| Variant | recall@5 | recall@10 | MRR@10 | hits@5 | seconds |
|---|---:|---:|---:|---:|---:|
| fts | 0.453 | 0.609 | 0.310 | 29/64 | 0.5 |
| dense | 0.812 | 0.922 | 0.677 | 52/64 | 9.6 |
| hybrid | 0.766 | 0.875 | 0.574 | 49/64 | 2.6 |
| rerank | 0.906 | 0.969 | 0.783 | 58/64 | 109.9 |
| filtered | 0.906 | 0.953 | 0.773 | 58/64 | 122.8 |
| per_board | 0.938 | 1.000 | 0.788 | 60/64 | 129.4 |

recall@5 by category:

| Variant | comparison (n=6) | injection_question (n=4) | pin (n=8) | refusal (n=4) | spec_condition (n=6) | spec_number (n=24) | text_fact (n=12) |
|---|---:|---:|---:|---:|---:|---:|---:|
| fts | 1/6 | 1/4 | 1/8 | 1/4 | 4/6 | 15/24 | 6/12 |
| dense | 0/6 | 4/4 | 6/8 | 4/4 | 5/6 | 23/24 | 10/12 |
| hybrid | 1/6 | 2/4 | 6/8 | 4/4 | 6/6 | 19/24 | 11/12 |
| rerank | 1/6 | 4/4 | 8/8 | 3/4 | 6/6 | 24/24 | 12/12 |
| filtered | 1/6 | 4/4 | 8/8 | 3/4 | 6/6 | 24/24 | 12/12 |
| per_board | 3/6 | 4/4 | 8/8 | 3/4 | 6/6 | 24/24 | 12/12 |

Misses at k=5 for `per_board` (4):

- `cp02` Between the Nano RP2040 Connect and the Nano ESP32, which is rated for the higher maximum temperature?
- `cp03` Which can source more current from its 3.3 V output: the Portenta X8 or the Nano RP2040 Connect?
- `cp08` Which board runs from a lower minimum VIN, the Mega 2560 Rev3 or the UNO R4 WiFi?
- `rf06` What is the maximum power consumption of the Nano RP2040 Connect?
