"""One JSON line per question in traces/YYYY-MM-DD.jsonl: what was retrieved, which models
were tried and how each attempt went, tokens, cost, guardrail outcome and total latency."""

import json
import time
from datetime import UTC, date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TRACE_DIR = ROOT / "traces"


def record(state: dict, attempts: list[dict], started: float, trace_dir: Path = TRACE_DIR) -> dict:
    resp = state["response"]
    log = state.get("tool_log")
    row = {
        "ts": datetime.now(UTC).isoformat(timespec="seconds"),
        "question": state["question"],
        "boards": state["info"].skus,
        "unknown_boards": state["info"].unknown_mentions,
        "retrieved": sorted({(h.sku, h.page_no) for h in state.get("hits", [])}),
        "attempts": attempts,
        "model": next((a["model"] for a in reversed(attempts) if a["outcome"] == "ok"), None),
        "failovers": max(0, len(attempts) - 1),
        "input_tokens": sum(a["input_tokens"] for a in attempts),
        "output_tokens": sum(a["output_tokens"] for a in attempts),
        "cost_usd": round(sum(a["cost_usd"] for a in attempts), 6),
        "tool_calls": log.calls if log else [],
        "tools_rejected": log.rejected if log else [],
        "status": resp.status,
        "refusal_reason": resp.refusal_reason,
        "violations": resp.violations,
        "citations": [c.model_dump() for c in resp.citations],
        "answer": resp.text,
        "latency_ms": int((time.monotonic() - started) * 1000),
    }
    trace_dir.mkdir(parents=True, exist_ok=True)
    with (trace_dir / f"{date.today().isoformat()}.jsonl").open("a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row
