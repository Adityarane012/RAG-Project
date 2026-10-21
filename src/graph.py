"""The query pipeline as a LangGraph graph (D15).

    extract -> [clarify -> END] | retrieve -> rerank -> verify
        verify -> enrich -> explain -> END
               | relax -> END        (offer one relaxation; the UI re-invokes if accepted)
               | abstain -> END

The two loops close through the UI, not inside one run: `clarify` and `relax` end the
run with a question in the state, and the UI calls `invoke` again with the user's answer
in `overrides` and the counters carried over. That keeps the graph stateless between
turns (the UI holds the state in st.session_state, D16) and the caps explicit:
at most `graph.max_clarifying_questions` questions and `graph.max_relax_retries` retries.

Nodes are thin: constraint checks are plain functions in verify.py (D2), and everything
that touches the network is injected via `Deps`, so the graph runs in tests with stubs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, TypedDict

from langgraph.graph import END, START, StateGraph

from src.adapt import model_report
from src.config import CFG
from src.guide import clarifying_question, describe_intent, relaxation_offer, try_it_snippet
from src.retrieve import fetch_chunks, group_by_model
from src.verify import FAIL, notes, overall, rank_key, verify

MAX_CLARIFY = CFG["graph"]["max_clarifying_questions"]
MAX_RELAX = CFG["graph"]["max_relax_retries"]


class State(TypedDict, total=False):
    # Input / carried between turns
    query: str
    overrides: dict           # user edits and answers, applied over the LLM's extraction
    clarifications_asked: int
    relax_count: int
    # Produced
    constraints: dict
    intent: str
    matches: list
    candidates: list
    results: list
    closest: list
    question: dict | None
    relax_offer: dict | None
    reports: list
    explanations: list
    explain_error: str | None
    outcome: str              # answer | clarify | relax | abstain


@dataclass
class Deps:
    """Everything the graph needs from outside."""
    extract: Callable[[str], dict]                  # llm.extract_constraints
    fetch: Callable[[dict, int], list]              # (filter, top_k) -> chunk matches
    rerank: Callable[[str, list], list]             # (soft_query, matches) -> matches, reordered
    explain: Callable[[dict, list], list]           # llm.explain
    lineage_index: dict = field(default_factory=dict)
    card_data: Callable[[str], dict | None] = lambda model_id: None


def viable(result: dict) -> bool:
    """A model worth showing: nothing failed (unknowns are shown, flagged ⚠️)."""
    return result["overall"] != FAIL


def route_after_extract(state: State) -> str:
    if clarifying_question(state["constraints"]) and state.get("clarifications_asked", 0) < MAX_CLARIFY:
        return "clarify"
    return "retrieve"


def route_after_verify(state: State) -> str:
    if any(viable(r) for r in state["results"]):
        return "enrich"
    if state.get("relax_count", 0) < MAX_RELAX and relaxation_offer(state["constraints"]):
        return "relax"
    return "abstain"


def build_graph(deps: Deps):
    def extract(state: State) -> State:
        constraints = deps.extract(state["query"])
        constraints.update(state.get("overrides") or {})  # key presence, so None can clear
        return {"constraints": constraints, "intent": describe_intent(constraints)}

    def clarify(state: State) -> State:
        return {"outcome": "clarify", "question": clarifying_question(state["constraints"]),
                "clarifications_asked": state.get("clarifications_asked", 0) + 1}

    def retrieve(state: State) -> State:
        return {"matches": fetch_chunks(deps.fetch, state["constraints"])}

    def rerank(state: State) -> State:
        matches = deps.rerank(state["constraints"].get("soft_query") or state["query"], state["matches"])
        return {"candidates": group_by_model(matches, CFG["retrieval"]["top_models"])}

    def verify_node(state: State) -> State:
        c = state["constraints"]
        results = []
        for cand in state["candidates"]:
            table = verify(cand["meta"], c)
            results.append({"model_id": cand["model_id"], "meta": cand["meta"], "chunks": cand["chunks"],
                            "table": table, "overall": overall(table), "notes": notes(cand["meta"], c)})
        results.sort(key=lambda r: rank_key(r["table"]))  # stable: reranker order within a group
        return {"results": results, "closest": results[:3]}

    def relax(state: State) -> State:
        return {"outcome": "relax", "relax_offer": relaxation_offer(state["constraints"]),
                "relax_count": state.get("relax_count", 0) + 1}

    def abstain(state: State) -> State:
        return {"outcome": "abstain"}

    def enrich(state: State) -> State:
        c = state["constraints"]
        reports = []
        for r in filter(viable, state["results"]):
            report = model_report(r["meta"], deps.lineage_index, c.get("langs"), deps.card_data(r["model_id"]))
            report["try_it"] = try_it_snippet(r["model_id"], r["meta"]["task"]) if r["meta"].get("task") else None
            reports.append(report)
        return {"reports": reports}

    def explain(state: State) -> State:
        shown = [r for r in state["results"] if viable(r)]
        try:
            explanations, error = deps.explain(state["constraints"], shown), None
        except Exception as e:  # LLM down or bad JSON: the verified table must still render
            explanations, error = [], f"{type(e).__name__}: {e}"
        return {"outcome": "answer", "explanations": explanations, "explain_error": error}

    g = StateGraph(State)
    for name, fn in (("extract", extract), ("clarify", clarify), ("retrieve", retrieve),
                     ("rerank", rerank), ("verify", verify_node), ("relax", relax),
                     ("abstain", abstain), ("enrich", enrich), ("explain", explain)):
        g.add_node(name, fn)
    g.add_edge(START, "extract")
    g.add_conditional_edges("extract", route_after_extract, {"clarify": "clarify", "retrieve": "retrieve"})
    g.add_edge("clarify", END)
    g.add_edge("retrieve", "rerank")
    g.add_edge("rerank", "verify")
    g.add_conditional_edges("verify", route_after_verify,
                            {"enrich": "enrich", "relax": "relax", "abstain": "abstain"})
    g.add_edge("relax", END)
    g.add_edge("abstain", END)
    g.add_edge("enrich", "explain")
    g.add_edge("explain", END)
    return g.compile()
