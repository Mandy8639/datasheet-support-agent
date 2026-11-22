"""Ask the agent a question from the command line.

uv run python -m datasheet_agent.cli "What's the max VIN of the UNO R4 WiFi?"
uv run python -m datasheet_agent.cli --json "..."
"""

import argparse
import json
import sys
import time

from datasheet_agent.agent.graph import ask
from datasheet_agent.agent.providers import from_settings
from datasheet_agent.agent.trace import record


def run(question: str) -> dict:
    llm = from_settings()
    started = time.monotonic()
    state = ask(question, llm)
    return record(state, llm.attempts_as_dicts() if state.get("turns") else [], started)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--json", action="store_true", help="print the full trace row")
    args = ap.parse_args()
    row = run(args.question)
    if args.json:
        print(json.dumps(row, indent=2, ensure_ascii=False))
        return 0
    cites = ", ".join(f"{c['sku']} p.{c['page']}" for c in row["citations"])
    print(row["answer"])
    if cites:
        print(f"Sources: {cites}")
    print(
        f"[{row['status']}{'/' + row['refusal_reason'] if row['refusal_reason'] else ''} | "
        f"model {row['model']} | {row['failovers']} failover(s) | {row['latency_ms']} ms | "
        f"${row['cost_usd']:.4f}]"
    )
    if row["violations"]:
        print("guardrail:", "; ".join(row["violations"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
