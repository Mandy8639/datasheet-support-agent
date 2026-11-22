# End-to-end evaluation (test split, 2026-11-21)

Every question run through the agent once and scored deterministically (`src/datasheet_agent/evals/scoring.py`). Same prompt and model chain for both configs.

| Metric | baseline | full |
|---|---:|---:|
| **Passed (all questions)** | **61/77 (79%)** | **74/77 (96%)** |
| Answerable: correct content | 47/63 (75%) | 61/63 (97%) |
| Answerable: cited a gold page | 48/63 (76%) | 61/63 (97%) |
| Answerable: correct, and a cited page states the value (lenient) | 47/63 (75%) | 60/63 (95%) |
| Answerable but refused (false refusals) | 15/63 (24%) | 1/63 (2%) |
| Should refuse but answered (false answers) | 0/14 (0%) | 0/14 (0%) |
| Injection items passed | 8/8 (100%) | 8/8 (100%) |
| Answers containing forbidden content | 0 | 0 |
| Failed because every model was unavailable (rate limits) | 1 | 0 |
| Guardrail blocks | 0 | 0 |
| Latency p50 / p95 | 1.1 s / 2.5 s | 2.6 s / 5.7 s |
| Failovers | 35 | 11 |
| Tokens in / out | 87,916 / 11,693 | 155,519 / 12,229 |
| Cost | $0.0000 | $0.0000 |

Pass rate by category:

| Category | baseline | full |
|---|---:|---:|
| comparison | 0/6 (0%) | 4/6 (67%) |
| injection_document | 4/4 (100%) | 4/4 (100%) |
| injection_question | 4/4 (100%) | 4/4 (100%) |
| pin | 3/8 (38%) | 8/8 (100%) |
| refusal | 13/13 (100%) | 13/13 (100%) |
| spec_condition | 5/6 (83%) | 6/6 (100%) |
| spec_number | 23/24 (96%) | 24/24 (100%) |
| text_fact | 9/12 (75%) | 11/12 (92%) |

Models that produced the answer: baseline: particle-ai/particle-1:free 56, baidu/ernie-5.5-flash-preview:free 15, nvidia/nemotron-3.5-super-vl:free 4, none 2; full: baidu/ernie-5.5-flash-preview:free 9, particle-ai/particle-1:free 65, nvidia/nemotron-3.5-super-vl:free 1, none 2

## Failures: baseline (16)

- `sn02` (spec_number): refused (not_in_datasheet). Answer: "I can't confirm that from the datasheet. Please ask on the Arduino Forum (forum.arduino.cc), where Arduino staff and the community answer hardware questions."
- `sc09` (spec_condition): refused (not_in_datasheet). Answer: "I can't confirm that from the datasheet. Please ask on the Arduino Forum (forum.arduino.cc), where Arduino staff and the community answer hardware questions."
- `cp02` (comparison): refused (not_in_datasheet). Answer: "I can't confirm that from the datasheet. Please ask on the Arduino Forum (forum.arduino.cc), where Arduino staff and the community answer hardware questions."
- `cp03` (comparison): refused (not_in_datasheet). Answer: "I can't confirm that from the datasheet. Please ask on the Arduino Forum (forum.arduino.cc), where Arduino staff and the community answer hardware questions."
- `cp05` (comparison): refused (not_in_datasheet). Answer: "I can't confirm that from the datasheet. Please ask on the Arduino Forum (forum.arduino.cc), where Arduino staff and the community answer hardware questions."
- `cp06` (comparison): refused (not_in_datasheet). Answer: "I can't confirm that from the datasheet. Please ask on the Arduino Forum (forum.arduino.cc), where Arduino staff and the community answer hardware questions."
- `cp08` (comparison): refused (not_in_datasheet). Answer: "I can't confirm that from the datasheet. Please ask on the Arduino Forum (forum.arduino.cc), where Arduino staff and the community answer hardware questions."
- `cp09` (comparison): refused (not_in_datasheet). Answer: "I can't confirm that from the datasheet. Please ask on the Arduino Forum (forum.arduino.cc), where Arduino staff and the community answer hardware questions."
- `tf02` (text_fact): refused (not_in_datasheet). Answer: "I can't confirm that from the datasheet. Please ask on the Arduino Forum (forum.arduino.cc), where Arduino staff and the community answer hardware questions."
- `tf08` (text_fact): refused (not_in_datasheet). Answer: "I can't confirm that from the datasheet. Please ask on the Arduino Forum (forum.arduino.cc), where Arduino staff and the community answer hardware questions."
- `tf12` (text_fact): refused (not_in_datasheet). Answer: "I can't confirm that from the datasheet. Please ask on the Arduino Forum (forum.arduino.cc), where Arduino staff and the community answer hardware questions."
- `pn02` (pin): refused (not_in_datasheet). Answer: "I can't confirm that from the datasheet. Please ask on the Arduino Forum (forum.arduino.cc), where Arduino staff and the community answer hardware questions."
- `pn03` (pin): refused (not_in_datasheet). Answer: "I can't confirm that from the datasheet. Please ask on the Arduino Forum (forum.arduino.cc), where Arduino staff and the community answer hardware questions."
- `pn05` (pin): refused (not_in_datasheet). Answer: "I can't confirm that from the datasheet. Please ask on the Arduino Forum (forum.arduino.cc), where Arduino staff and the community answer hardware questions."
- `pn11` (pin): wrong or missing value. Answer: "The VRTC pin is for the real-time clock battery and is used to power the RTC while the board is off."
- `pn12` (pin): refused (not_in_datasheet). Answer: "I can't confirm that from the datasheet. Please ask on the Arduino Forum (forum.arduino.cc), where Arduino staff and the community answer hardware questions."

## Failures: full (3)

- `cp02` (comparison): refused (not_in_datasheet). Answer: "I can't confirm that from the datasheet. Please ask on the Arduino Forum (forum.arduino.cc), where Arduino staff and the community answer hardware questions."
- `cp08` (comparison): no citation to a gold page (cited [('A000067', 5), ('ABX00087', 2)]). Answer: "The UNO R4 WiFi runs from a lower minimum VIN: 6 V versus the Mega 2560 Rev3's 7 V."
- `tf09` (text_fact): wrong or missing value. Answer: "No. The Arduino MKR WAN 1310 only supports 3.3 V I/Os and is NOT 5 V tolerant, so directly connecting 5 V signals can damage the board."
