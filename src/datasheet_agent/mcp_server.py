"""MCP server: the agent's read-only tools plus a guarded `ask`, over stdio.

    uv run python -m datasheet_agent.mcp_server

Exposed: search_datasheets, get_spec, get_page (the same allowlisted, read-only tools the agent
uses, on the read-only database role) and ask (the full agent, so answers pass the same
guardrail R1-R7). Nothing that writes is exposed. All tools are annotated read-only.
"""

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from datasheet_agent.agent import tools

READ_ONLY = ToolAnnotations(
    read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False
)

server = MCPServer(
    name="datasheet-support-agent",
    instructions=(
        "Answers questions about Arduino boards from their datasheets (CC BY-SA 4.0). "
        "Use `ask` for a checked answer with page citations; the other tools return raw excerpts."
    ),
)


@server.tool(annotations=READ_ONLY)
def search_datasheets(query: str, skus: list[str] | None = None, k: int = 8) -> list[dict]:
    """Search datasheet excerpts. Optionally restrict to board SKUs (e.g. ["ABX00087"])."""
    k = max(1, min(k, 20))
    return [
        {"sku": h.sku, "page": h.page_no, "section": h.section, "kind": h.kind, "text": h.text}
        for h in tools.search_datasheets(query, skus, k)
    ]


@server.tool(annotations=READ_ONLY)
def get_spec(sku: str, parameter: str) -> list[dict]:
    """Spec-table rows (min/typ/max/unit, page) of one board matching a parameter name."""
    return tools.get_spec(sku, parameter)


@server.tool(annotations=READ_ONLY)
def get_page(sku: str, page: int) -> str:
    """Full text of one datasheet page."""
    return tools.get_page(sku, page) or f"no page {page} for {sku}"


@server.tool(annotations=READ_ONLY)
def ask(question: str) -> dict:
    """Ask the support agent. Returns a checked answer with citations, or a refusal + handoff."""
    from datasheet_agent.cli import run

    row = run(question)
    return {k: row[k] for k in ("status", "answer", "citations", "refusal_reason", "model")}


if __name__ == "__main__":
    server.run("stdio")
