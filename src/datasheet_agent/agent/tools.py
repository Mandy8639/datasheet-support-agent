"""The agent's three read-only tools and the allowlist that enforces them.

Every tool uses the read-only `agent_ro` database role. A model asking for any other tool
(e.g. a "delete" tool named in an injected instruction) gets a refusal result, which is
logged in the trace; nothing else can run.
"""

from dataclasses import dataclass, field
from typing import Any

from datasheet_agent.db import agent_conn
from datasheet_agent.retrieval.search import Hit, per_board

MAX_TOOL_CALLS = 4


def search_datasheets(query: str, skus: list[str] | None = None, k: int = 8) -> list[Hit]:
    """Retrieve chunks with the best retriever from the Phase 3 ablation (per-board)."""
    return per_board(query, k, skus=skus)


def get_spec(sku: str, parameter: str) -> list[dict]:
    """Spec-table rows of one board whose parameter or symbol mentions `parameter`."""
    sql = """
        SELECT d.sku, s.page_no, s.section, s.symbol, s.parameter, s.min_raw, s.typ_raw,
               s.max_raw, s.unit
        FROM spec_rows s JOIN documents d ON d.id = s.doc_id
        WHERE d.sku = %s AND (s.parameter ILIKE %s OR s.symbol ILIKE %s)
        ORDER BY s.page_no, s.id LIMIT 20"""
    like = f"%{parameter}%"
    with agent_conn() as conn:
        rows = conn.execute(sql, (sku, like, like)).fetchall()
    keys = ["sku", "page", "section", "symbol", "parameter", "min", "typ", "max", "unit"]
    return [dict(zip(keys, r, strict=True)) for r in rows]


def get_page(sku: str, page: int) -> str | None:
    """Full text of one datasheet page (used to read around a hit, and by the guardrail)."""
    sql = """SELECT p.text FROM pages p JOIN documents d ON d.id = p.doc_id
             WHERE d.sku = %s AND p.page_no = %s"""
    with agent_conn() as conn:
        row = conn.execute(sql, (sku, page)).fetchone()
    return row[0] if row else None


ALLOWED = {"search_datasheets": search_datasheets, "get_spec": get_spec, "get_page": get_page}


@dataclass
class ToolLog:
    calls: list[dict] = field(default_factory=list)
    rejected: list[str] = field(default_factory=list)


def call_tool(name: str, args: dict[str, Any], log: ToolLog) -> Any:
    """Run an allowlisted tool, or refuse. Also caps the number of calls per question."""
    if name not in ALLOWED:
        log.rejected.append(name)
        return {"error": f"tool '{name}' is not available"}
    if len(log.calls) >= MAX_TOOL_CALLS:
        log.rejected.append(f"{name} (call limit)")
        return {"error": "tool call limit reached"}
    log.calls.append({"tool": name, "args": args})
    return ALLOWED[name](**args)
