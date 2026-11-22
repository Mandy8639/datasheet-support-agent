"""The agent as a LangGraph flow:

understand -> (board not in corpus?) -> refuse
           -> retrieve -> answer (model, with allowlisted tool calls) -> guardrail -> END
"""

import json
from functools import cache
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, StateGraph

from datasheet_agent.agent import tools
from datasheet_agent.agent.guardrail import apply, check
from datasheet_agent.agent.llm import LLM, ModelTurn
from datasheet_agent.agent.schema import HANDOFF, ModelAnswer, Response
from datasheet_agent.db import agent_conn
from datasheet_agent.retrieval.query import QueryInfo, understand
from datasheet_agent.retrieval.search import Hit

ROOT = Path(__file__).resolve().parents[3]
K = 8


@cache
def system_prompt() -> str:
    return (
        (ROOT / "prompts" / "system.md").read_text()
        + "\n"
        + (ROOT / "prompts" / "examples.md").read_text()
    )


def db_aliases() -> tuple[tuple[str, str], ...]:
    """Every document in the database is recognisable by its product name (incl. fixtures)."""
    with agent_conn() as conn:
        rows = conn.execute("SELECT sku, product FROM documents").fetchall()
    out = []
    for sku, product in rows:
        name = product.replace(" (synthetic)", "")
        out += [(name, sku), (name.removeprefix("Arduino "), sku)]
    return tuple(out)


class State(TypedDict, total=False):
    question: str
    info: QueryInfo
    hits: list[Hit]
    seen: set[tuple[str, int]]
    answer: ModelAnswer
    response: Response
    tool_log: tools.ToolLog
    turns: list[ModelTurn]


def format_context(hits: list[Hit]) -> str:
    blocks = []
    for h in hits:
        pages = f"p.{h.page_no}" if h.page_end == h.page_no else f"p.{h.page_no}-{h.page_end}"
        blocks.append(f"[{h.sku} {pages}] {h.search_text}")
    return "\n\n".join(blocks)


def seen_pages(hits: list[Hit]) -> set[tuple[str, int]]:
    return {(h.sku, p) for h in hits for p in range(h.page_no, h.page_end + 1)}


def build(llm: LLM, retrieve=tools.search_datasheets, page_text=tools.get_page, aliases=db_aliases):
    """Compile the graph. Dependencies are injectable so tests run without models or a DB."""

    def n_understand(state: State) -> State:
        return {
            "info": understand(state["question"], aliases()),
            "tool_log": tools.ToolLog(),
            "turns": [],
        }

    def route(state: State) -> str:
        info = state["info"]
        return "refuse" if info.unknown_mentions and not info.skus else "retrieve"

    def n_refuse(state: State) -> State:
        return {
            "response": Response(status="refused", text=HANDOFF, refusal_reason="out_of_corpus")
        }

    def n_retrieve(state: State) -> State:
        hits = retrieve(state["question"], state["info"].skus or None, K)
        return {"hits": hits, "seen": seen_pages(hits)}

    def n_answer(state: State) -> State:
        log, seen, turns = state["tool_log"], set(state["seen"]), list(state["turns"])
        messages = [
            {
                "role": "user",
                "content": (
                    f"Context:\n{format_context(state['hits'])}\n\nQuestion: {state['question']}"
                ),
            }
        ]
        for _ in range(tools.MAX_TOOL_CALLS + 1):
            turn = llm.turn(system_prompt(), messages)
            turns.append(turn)
            if turn.answer is not None:
                return {"answer": turn.answer, "seen": seen, "turns": turns}
            results = []
            for req in turn.tool_requests:
                out = tools.call_tool(req.name, req.args, log)
                if req.name == "get_page" and isinstance(out, str):
                    seen.add((req.args["sku"], int(req.args["page"])))
                if req.name == "get_spec" and isinstance(out, list):
                    seen |= {(r["sku"], r["page"]) for r in out}
                results.append(
                    {"tool": req.name, "result": out if isinstance(out, dict | list) else str(out)}
                )
            messages.append(
                {
                    "role": "user",
                    "content": "Tool results:\n" + json.dumps(results, default=str)[:20000],
                }
            )
        # The model never produced an answer within the tool budget.
        return {
            "answer": ModelAnswer(status="not_in_datasheet", answer="", citations=[]),
            "seen": seen,
            "turns": turns,
        }

    def n_guardrail(state: State) -> State:
        result = check(state["answer"], state["info"], state["seen"], page_text)
        return {"response": apply(state["answer"], result)}

    g = StateGraph(State)
    g.add_node("understand", n_understand)
    g.add_node("refuse", n_refuse)
    g.add_node("retrieve", n_retrieve)
    g.add_node("answer", n_answer)
    g.add_node("guardrail", n_guardrail)
    g.set_entry_point("understand")
    g.add_conditional_edges("understand", route, {"refuse": "refuse", "retrieve": "retrieve"})
    g.add_edge("retrieve", "answer")
    g.add_edge("answer", "guardrail")
    g.add_edge("guardrail", END)
    g.add_edge("refuse", END)
    return g.compile()


def ask(question: str, llm: LLM, **deps) -> State:
    return build(llm, **deps).invoke({"question": question})
