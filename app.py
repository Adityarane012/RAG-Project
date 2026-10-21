"""Streamlit UI (D16): search, check-a-model, constraint table, Try it / Build on it.

Streamlit reruns this whole script on every click, so the graph state lives in
st.session_state and heavy objects in st.cache_resource, otherwise the clarifying
loop would lose its place and the embedding model would reload on every interaction.
"""

from __future__ import annotations

import streamlit as st

from src.config import CFG
from src.guide import EXAMPLE_QUERIES, TOOLTIPS
from src.verify import ICON

DISCLAIMER = ("Rights are read from each model's *declared* license. This is not legal "
              "advice, and a card can be wrong.")
ROW_LABELS = {"task": "Task", "languages": "Language", "direction": "Direction", "size": "Size",
              "commercial": "Commercial use", "modifiable": "Modifiable"}


@st.cache_resource
def get_graph():
    """Build the LangGraph pipeline once per process.

    TODO: wire real deps (local embedder, Pinecone index + namespace, reranker, llm.explain)
    into graph.Deps. Until then the UI renders but cannot search.
    """
    raise NotImplementedError("pipeline deps not wired yet")


def _follow_up(override: dict) -> None:
    """The user answered a clarifying question or accepted a relaxation: re-run the
    same query with that override and the loop counters carried over (D15 caps)."""
    st.session_state["overrides"] = {**st.session_state.get("overrides", {}), **override}
    st.session_state["action"] = "followup"
    st.rerun()


def _fresh(query: str | None = None) -> None:
    """A new search: forget overrides, counters and the previous result."""
    if query is not None:
        st.session_state["query"] = query
    st.session_state["overrides"] = {}
    st.session_state.pop("state", None)
    st.session_state["action"] = "fresh"
    st.rerun()


def render_table(result: dict) -> None:
    rows = {ROW_LABELS[k]: f"{ICON[v]} {v}" for k, v in result["table"].items()}
    st.table(rows)
    for note in result["notes"]:
        st.caption(f"⚠️ {note}")


def render_state(state: dict) -> None:
    """Render one graph run's output. Handles every outcome."""
    st.info(state["intent"])  # D13: parsed intent in plain words (editing: TODO)
    outcome = state["outcome"]

    if outcome == "clarify":
        q = state["question"]
        st.subheader(q["question"])
        for value, label in q["options"].items():
            if st.button(label, key=f"clarify-{value}"):
                _follow_up({q["field"]: value})
        return

    if outcome in ("relax", "abstain"):
        offer = state.get("relax_offer")
        st.warning(offer["message"] if offer else "No model meets all constraints.")
        if offer and st.button("Yes, relax it"):
            _follow_up({offer["field"]: offer["new_value"]})
        if state.get("closest"):
            st.caption("Closest matches (they fail at least one constraint):")
            for r in state["closest"]:
                st.markdown(f"**{r['model_id']}**")
                render_table(r)
        return

    reports = {r["model_id"]: r for r in state.get("reports", [])}
    explanations = {e["model_id"]: e for e in state.get("explanations", [])}
    if state.get("explain_error"):
        st.warning("Explanations are unavailable right now; the verified table below is unaffected.")
    for result in (r for r in state["results"] if r["overall"] != "fail"):
        mid = result["model_id"]
        st.markdown(f"### [{mid}](https://huggingface.co/{mid})")
        render_table(result)
        if mid in explanations:
            st.write(explanations[mid]["text"])
        report = reports.get(mid)
        if report:
            with st.expander("Try it"):
                st.code(report["try_it"] or "", language="python")
                st.markdown(f"[Open the model page]({report['model_page']})")
            with st.expander("Build on it"):
                st.markdown(f"**Modifiable:** {report['rights']['modifiable']}")
                for note in report["rights"]["notes"]:
                    st.caption(note)
                lin = report["lineage"]
                st.write(f"Fine-tune of `{lin['base_model']}`; {lin['other_finetunes']} other fine-tunes "
                         "in our snapshot." if lin["status"] == "pass" else "⚠️ Lineage unknown.")
                mem = report["memory"]
                if mem["status"] == "pass":
                    for name, m in mem["methods"].items():
                        st.write(f"{name}: ≥ {m['gb']} GB {ICON[m['fits']]} on a {mem['reference_gpu_gb']} GB GPU")
                    st.caption("Lower bound; excludes activations.")
                else:
                    st.write("⚠️ Parameter count unknown, so no memory estimate.")
                if report["task_guide"]:
                    st.markdown(f"[How to fine-tune for this task]({report['task_guide']})")


def main() -> None:
    st.set_page_config(page_title="HF Model Finder", page_icon="🔎")
    st.title("HF Model Finder")
    st.caption(DISCLAIMER)
    if CFG.get("snapshot_date"):
        st.caption(f"Data snapshot: {CFG['snapshot_date']}")

    search_tab, check_tab = st.tabs(["Search", "Check a model"])

    with search_tab:
        st.write("Try an example:")
        for example in EXAMPLE_QUERIES:
            if st.button(example, key=f"ex-{example}"):
                _fresh(example)
        query = st.text_input("Describe the model you need", key="query")

        action = st.session_state.pop("action", None)
        if query and st.button("Search"):
            _fresh()
        if query and action:
            try:
                graph = get_graph()
            except NotImplementedError:
                st.info("Search isn't wired up yet. See `get_graph()` in app.py.")
            else:
                carried = {}
                if action == "followup" and "state" in st.session_state:
                    prev = st.session_state["state"]
                    carried = {k: prev[k] for k in ("clarifications_asked", "relax_count") if k in prev}
                st.session_state["state"] = graph.invoke({
                    "query": query, "overrides": st.session_state.get("overrides", {}), **carried})
        if "state" in st.session_state:
            render_state(st.session_state["state"])

    with check_tab:
        st.text_input("Paste a Hugging Face model ID", key="check_id", help=TOOLTIPS["license"])
        st.info("Check-a-model reuses verify.py and adapt.model_report (D23); the lookup "
                "against the snapshot isn't wired up yet.")


if __name__ == "__main__":
    main()
