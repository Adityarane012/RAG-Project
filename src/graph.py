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
from src.llm import clean_constraints
from src.guide import clarifying_question, describe_intent, out_of_scope_message, relaxation_offer, try_it_snippet
from src.retrieve import fetch_chunks, group_by_model
from src.verify import FAIL, PASS, notes, overall, rank_key, verify

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
    fully_verified: bool      # False => the answer holds only models with ⚠️; the UI shows a banner
    explanations: list
    explain_error: str | None
    outcome: str              # answer | clarify | relax | abstain | out_of_scope
    message: str | None       # why, for out_of_scope
    rerank_skipped: bool      # True when the reranker's quota was exhausted and results keep vector order


@dataclass
class Deps:
    """Everything the graph needs from outside."""
    extract: Callable[[str], dict]                  # llm.extract_constraints
    fetch: Callable[[str, dict, int], list]         # (query text, filter, top_k) -> chunk matches
    rerank: Callable[[str, list], list]             # (soft_query, matches) -> matches, reordered
    explain: Callable[[dict, list], list] | None    # llm.explain; None skips explanations (evaluation, rate limits)
    lineage_index: dict = field(default_factory=dict)
    card_data: Callable[[str], dict | None] = lambda model_id: None


def viable(result: dict) -> bool:
    """A model worth showing: nothing failed (unknowns are shown, flagged ⚠️)."""
    return result["overall"] != FAIL


def route_after_extract(state: State) -> str:
    if state.get("outcome") == "out_of_scope":
        return "out_of_scope"
    if clarifying_question(state["constraints"]) and state.get("clarifications_asked", 0) < MAX_CLARIFY:
        return "clarify"
    return "retrieve"


def route_after_verify(state: State) -> str:
    if any(viable(r) for r in state["results"]):
        return "enrich"
    if state.get("relax_count", 0) < MAX_RELAX and relaxation_offer(state["constraints"]):
        return "relax"
    return "abstain"


VARIANTS = ("ours", "naive", "keyword")


def build_graph(deps: Deps, variant: str = "ours"):
    """Compile the pipeline. `variant` selects what the evaluation compares (D19):

    * ours    : the full graph.
    * naive   : naive RAG. Same index, embeddings, reranker and LLM, but NO metadata filters (not even the
                task) and NO verification-driven behaviour: no clarifying, relaxing, abstaining, re-ranking
                by verdict or explanations. Verdict tables are still computed so the harness can judge it
                with the same rules as every other system.
    * keyword : like naive, but retrieval is whatever `deps.fetch` does (BM25 + the same metadata filters in
                the harness) and the reranker is skipped.
    """
    if variant not in VARIANTS:
        raise ValueError(f"variant must be one of {VARIANTS}, got {variant!r}")
    plain = variant != "ours"
    # The full system verifies a wider pool than it shows, so a verified model ranked 6th by the reranker can
    # still outrank an unknown one (D12); the baselines keep retrieval order and show exactly the top models.
    pool_size = CFG["retrieval"]["top_models"] if plain else CFG["retrieval"]["verify_pool"]

    def extract(state: State) -> State:
        scope_message = out_of_scope_message(state["query"])
        if scope_message:        # image / vision / OCR requests: say so, and do not spend an LLM call or show wrong models
            return {"constraints": clean_constraints({}, state["query"]), "intent": "", "outcome": "out_of_scope", "message": scope_message}
        # User edits go through the same validator as the LLM's output: an override is untrusted input too
        # (a bad task or size would otherwise make every model fail silently). Key presence counts, so None clears.
        constraints = clean_constraints({**deps.extract(state["query"]), **(state.get("overrides") or {})}, state["query"])
        return {"constraints": constraints, "intent": describe_intent(constraints)}

    def clarify(state: State) -> State:
        return {"outcome": "clarify", "question": clarifying_question(state["constraints"]),
                "clarifications_asked": state.get("clarifications_asked", 0) + 1}

    def retrieve(state: State) -> State:
        # naive RAG searches with no filter at all; keyword relies on deps.fetch applying the filter itself
        # Every system searches with the user's own words. The extractor's `soft_query` is a fragile LLM field: on
        # "small Gujarati classifier with a permissive license" it came back as "permissive license" and retrieval
        # returned only licence sections. It is still used to pick explanation evidence.
        text = state["query"]
        return {"matches": fetch_chunks(lambda flt, k: deps.fetch(text, flt, k),
                                        {} if variant == "naive" else state["constraints"], top_n=pool_size)}

    def rerank(state: State) -> State:
        matches, skipped = state["matches"], False
        if variant != "keyword":
            try:
                matches = deps.rerank(state["query"], matches)
            except Exception as e:
                from src.rerank import RerankQuotaExceeded

                if not isinstance(e, RerankQuotaExceeded):
                    raise
                skipped = True        # the hosted reranker's monthly quota is used up: keep vector order, and say so
        return {"candidates": group_by_model(matches, pool_size), "rerank_skipped": skipped}

    def verify_node(state: State) -> State:
        c = state["constraints"]
        results = []
        for cand in state["candidates"]:
            table = verify(cand["meta"], c)
            results.append({"model_id": cand["model_id"], "meta": cand["meta"], "chunks": cand["chunks"],
                            "table": table, "overall": overall(table), "notes": notes(cand["meta"], c)})
        if not plain:   # the full system ranks passes above unknowns above fails; the baselines keep retrieval order
            results.sort(key=lambda r: rank_key(r["table"]))  # stable: reranker order within a group
        results = results[:CFG["retrieval"]["top_models"]]
        return {"results": results, "closest": results[:3]}

    def relax(state: State) -> State:
        return {"outcome": "relax", "relax_offer": relaxation_offer(state["constraints"]),
                "relax_count": state.get("relax_count", 0) + 1}

    def finish(state: State) -> State:     # baselines: whatever retrieval returned, unfiltered by verdict
        return {"outcome": "answer", "fully_verified": any(r["overall"] == PASS for r in state["results"])}

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
            # the explanation relates each card to what the user asked, in the user's own words (soft_query can lose the topic)
            explanations, error = (deps.explain({**state["constraints"], "soft_query": state["query"]}, shown) if deps.explain else []), None
        except Exception as e:  # LLM down or bad JSON: the verified table must still render
            explanations, error = [], f"{type(e).__name__}: {e}"
        return {"outcome": "answer", "explanations": explanations, "explain_error": error,
                "fully_verified": any(r["overall"] == PASS for r in shown)}

    g = StateGraph(State)
    for name, fn in (("extract", extract), ("clarify", clarify), ("retrieve", retrieve),
                     ("rerank", rerank), ("verify", verify_node), ("relax", relax), ("finish", finish),
                     ("abstain", abstain), ("enrich", enrich), ("explain", explain)):
        g.add_node(name, fn)
    g.add_edge(START, "extract")
    g.add_conditional_edges("extract", ((lambda st: "out_of_scope" if st.get("outcome") == "out_of_scope" else "retrieve") if plain
                                        else route_after_extract),
                            {"clarify": "clarify", "retrieve": "retrieve", "out_of_scope": END})
    g.add_edge("clarify", END)
    g.add_edge("retrieve", "rerank")
    g.add_edge("rerank", "verify")
    g.add_conditional_edges("verify", (lambda st: "finish") if plain else route_after_verify,
                            {"enrich": "enrich", "relax": "relax", "abstain": "abstain", "finish": "finish"})
    g.add_edge("finish", END)
    g.add_edge("relax", END)
    g.add_edge("abstain", END)
    g.add_edge("enrich", "explain")
    g.add_edge("explain", END)
    return g.compile()
