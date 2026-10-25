"""Streamlit UI (D16): search with an editable parsed intent, a side-by-side comparison with naive RAG,
check-a-model, constraint tables, Try it / Build on it, tooltips and the legal disclaimer.

Streamlit reruns this whole script on every click, so the graph state lives in st.session_state and heavy
objects in st.cache_resource; otherwise the clarifying loop would lose its place and the models would reload
on every interaction.
"""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from src.checker import check_model
from src.config import CFG
from src.guide import EXAMPLE_QUERIES, LANG_NAMES, TASK_OPTIONS, TOOLTIPS
from src.replay import MissingRecording, ReplayGraph, mode_from_env
from src.verify import ICON, SIZE_WORDS_MB

DISCLAIMER = ("Rights are read from each model's *declared* license. This is not legal "
              "advice, and a card can be wrong.")
ROW_LABELS = {"task": "Task", "languages": "Language", "direction": "Direction", "size": "Size",
              "commercial": "Commercial use", "modifiable": "Modifiable"}
HELP = {"commercial": TOOLTIPS["commercial"], "modifiable": TOOLTIPS["modifiable"], "size": TOOLTIPS["size"]}
ICON_DISPLAY = {"pass": "pass", "fail": "❌ fail", "unknown": "⚠️ unknown"}
LEGEND = "pass · ❌ fails · ⚠️ unknown (the card or metadata doesn't say; we don't guess)"


@st.cache_resource(show_spinner=False)
def _live_graph(variant: str = "ours"):
    """The real pipeline for `variant`, built once per process (needs the vector index, keys and models)."""
    from src.pipeline import build_pipeline

    return build_pipeline(variant)


def get_graph(variant: str = "ours") -> ReplayGraph:
    """The graph, wrapped for recording / replay (D21). REPLAY=1 serves recorded runs and needs no network;
    RECORD=1 runs live and saves each result for later replay."""
    mode = mode_from_env()
    if mode == "replay":
        return ReplayGraph(mode="replay", variant=variant)
    return ReplayGraph(_live_graph(variant), mode, variant=variant)


@st.cache_resource(show_spinner=False)
def _records():
    """Snapshot records for check-a-model (the cached corpus; RAW_DIR overrides the location)."""
    from src import ingest
    from src.snapshot import collect_records

    return collect_records(Path(os.getenv("RAW_DIR") or ingest.RAW_DIR))


def _follow_up(override: dict) -> None:
    """The user answered a clarifying question, accepted a relaxation or edited the intent: re-run the same
    query with that override and the loop counters carried over (D15 caps)."""
    st.session_state["overrides"] = {**st.session_state.get("overrides", {}), **override}
    st.session_state["action"] = "followup"
    st.rerun()


def _fresh(query: str | None = None) -> None:
    """A new search: forget overrides, counters and the previous result."""
    if query is not None:
        st.session_state["query"] = query
    st.session_state["overrides"] = {}
    for k in ("state", "naive_state"):
        st.session_state.pop(k, None)
    st.session_state["action"] = "fresh"
    st.rerun()


def render_table(result: dict) -> None:
    rows = {ROW_LABELS[k]: ICON_DISPLAY.get(v, v) for k, v in result["table"].items()}
    st.table(rows)
    for note in result["notes"]:
        st.caption(f"⚠️ {note}")


def render_intent_editor(constraints: dict) -> None:
    """D13: the parsed request, editable. An extraction miss silently drops a constraint, so the user can see
    and fix it here; edits are sent back as overrides (validated like the LLM's own output)."""
    with st.expander("Edit what we understood"):
        tasks = [None, *TASK_OPTIONS]
        task = st.selectbox("What should the model do?", tasks, index=tasks.index(constraints.get("task")) if constraints.get("task") in tasks else 0,
                            format_func=lambda t: "(not specified)" if t is None else TASK_OPTIONS[t], key="edit-task")
        langs = st.multiselect("Languages", list(LANG_NAMES), default=[c for c in constraints.get("langs") or [] if c in LANG_NAMES],
                               format_func=LANG_NAMES.get, key="edit-langs")
        col1, col2 = st.columns(2)
        size_mb = col1.number_input("Max size (MB, 0 = no limit)", min_value=0.0, value=float(constraints.get("max_size_mb") or 0), step=50.0,
                                    help=HELP["size"], key="edit-size")
        words = [None, *SIZE_WORDS_MB]
        word = col2.selectbox("…or a size word", words, index=words.index(constraints.get("size_word")) if constraints.get("size_word") in words else 0,
                              format_func=lambda w: "(none)" if w is None else f"{w} (≤ {SIZE_WORDS_MB[w]:g} MB)", key="edit-word")
        commercial = st.checkbox("Must allow commercial use", value=bool(constraints.get("commercial")), help=HELP["commercial"], key="edit-comm")
        modifiable = st.checkbox("Must allow modification / fine-tuning", value=bool(constraints.get("modifiable")), help=HELP["modifiable"], key="edit-mod")
        if st.button("Search again with these", key="edit-go"):
            _follow_up({"task": task, "langs": langs, "max_size_mb": size_mb or None, "size_word": word,
                        "commercial": True if commercial else None, "modifiable": True if modifiable else None})


def render_plain(state: dict, limit: int = 5) -> None:
    """A baseline's output: whatever retrieval returned, with every verdict shown (including ❌)."""
    for i, r in enumerate(state.get("results", [])[:limit]):
        if i > 0:
            st.divider()
        st.markdown(f"**[{r['model_id']}](https://huggingface.co/{r['model_id']})**")
        render_table(r)


def render_state(state: dict) -> None:
    """Render one graph run's output. Handles every outcome."""
    outcome = state["outcome"]
    if outcome == "out_of_scope":
        st.warning(state.get("message") or "This request is outside what this tool searches.")
        return
    st.info(state["intent"])  # D13: parsed intent in plain words
    if state.get("rerank_skipped"):
        st.caption("Reranking was unavailable for this search (the hosted reranker's monthly quota is used up), so results are ordered "
                   "by text similarity only. The pass / fail / unknown checks are not affected.")

    if outcome == "clarify":
        q = state["question"]
        st.subheader(q["question"])
        for value, label in q["options"].items():
            if st.button(label, key=f"clarify-{value}"):
                _follow_up({q["field"]: value})
        if not q["options"]:  # free-form question (translation languages): offer a picker
            codes = st.multiselect("Languages", list(LANG_NAMES), format_func=LANG_NAMES.get, key="clarify-langs")
            if st.button("Continue", disabled=len(codes) < 2):
                _follow_up({"langs": codes})
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
    if not state.get("fully_verified", True):
        st.warning("No model fully verified: every result below has at least one ⚠️ unknown.")
    if state.get("explain_error"):
        st.warning("Explanations are unavailable right now; the verified table below is unaffected.")
    st.caption(LEGEND)
    models_to_show = [r for r in state["results"] if r["overall"] != "fail"]
    for i, result in enumerate(models_to_show):
        if i > 0:
            st.divider()
        mid = result["model_id"]
        st.markdown(f"### [{mid}](https://huggingface.co/{mid})")
        if mid in explanations:
            col_table, col_desc = st.columns([1, 1], gap="large")
            with col_table:
                render_table(result)
            with col_desc:
                st.markdown("##### 📝 Card Summary & Evidence")
                st.write(explanations[mid]["text"])
        else:
            render_table(result)
        report = reports.get(mid)
        if report:
            with st.expander("Try it"):
                st.code(report["try_it"] or "", language="python")
                st.caption("A standard template, not tested on this model. It suits ordinary Hugging Face weights with a recent transformers "
                           "(image models also need timm or torchvision); MLX, GGUF, quantized or custom-code models need their own "
                           "runtime. The model page says which.")
                st.markdown(f"[Open the model page]({report['model_page']})")
            with st.expander("Build on it"):
                render_build_on(report)


def render_build_on(report: dict) -> None:
    st.markdown(f"**Modifiable:** {report['rights']['modifiable']}", help=HELP["modifiable"])
    for note in report["rights"]["notes"]:
        st.caption(note)
    lin = report["lineage"]
    st.write(f"Fine-tune of `{lin['base_model']}`; {lin['other_finetunes']} other fine-tunes in our snapshot."
             if lin["status"] == "pass" else "⚠️ Lineage unknown.")
    mem = report["memory"]
    if mem["status"] == "pass":
        for name, m in mem["methods"].items():
            fit_icon = "" if m["fits"] == "pass" else f"{ICON[m['fits']]} "
            st.write(f"{name}: ≥ {m['gb']} GB {fit_icon}on a {mem['reference_gpu_gb']} GB GPU")
        st.caption("Lower bound; excludes activations.")
    else:
        st.write("⚠️ Parameter count unknown, so no memory estimate.")
    if report["task_guide"]:
        st.markdown(f"[How to fine-tune for this task]({report['task_guide']})")


def render_compare(ours: dict, naive: dict) -> None:
    """D16: the same request through the full system and through naive RAG (no filters, no verification)."""
    left, right = st.columns(2)
    with left:
        st.markdown("#### Ours (filters + verification)")
        if ours["outcome"] == "answer":
            shown = [r for r in ours["results"] if r["overall"] != "fail"]
            render_plain({"results": shown})
            if not shown:
                st.caption("Nothing to recommend.")
        else:
            st.caption(f"Outcome: {ours['outcome']} (asked a question, offered to relax, or the request is out of scope)")
    with right:
        st.markdown("#### Naive RAG (same index, no filters, no checks)")
        render_plain(naive)
    n_bad = sum(r["overall"] == "fail" for r in naive.get("results", [])[:5])
    st.caption(f"Naive RAG recommended {n_bad} model(s) that fail at least one requirement.")


def render_check_tab() -> None:
    st.text_input("Paste a Hugging Face model ID", key="check_id", placeholder="openai/whisper-tiny")
    with st.expander("Optionally check it against requirements", expanded=False):
        c1, c2 = st.columns(2)
        commercial = c1.checkbox("Must allow commercial use", help=HELP["commercial"], key="check-comm")
        modifiable = c2.checkbox("Must allow modification", help=HELP["modifiable"], key="check-mod")
        size = st.number_input("Max size (MB, 0 = no limit)", min_value=0.0, step=50.0, help=HELP["size"], key="check-size")
    if not st.session_state.get("check_id"):
        return
    reqs = {"commercial": True if commercial else None, "modifiable": True if modifiable else None, "max_size_mb": size or None}
    result = check_model(st.session_state["check_id"], _records(), reqs)
    if not result["found"]:
        st.warning(result["message"])
        return
    st.markdown(f"### [{result['meta']['model_id']}](https://huggingface.co/{result['meta']['model_id']})")
    st.table(result["facts"])
    if result["table"]:
        st.caption(LEGEND)
        st.table({ROW_LABELS[k]: ICON_DISPLAY.get(v, v) for k, v in result["table"].items()})
    st.caption(DISCLAIMER)
    with st.expander("Build on it", expanded=True):
        render_build_on(result["report"])


EXAMPLE_CATEGORIES = {
    "🎙️ Automatic Speech Recognition (ASR)": [
        ("Fast English speech recognition under 500 MB", "Lightweight English Whisper models suitable for laptops"),
        ("Speech recognition for Tamil under 1 GB", "Tamil regional Whisper fine-tune with sub-1GB constraint"),
        ("Kannada speech recognition trained on noisy real-world recordings", "Acoustically robust ASR for real-world audio"),
        ("Speech to text for Gujarati, commercial use allowed, under 1 GB", "Commercial license + size constraint for Gujarati"),
    ],
    "💬 Text Classification & Sentiment Analysis": [
        ("English sentiment analysis for product reviews that I can use commercially", "E-commerce customer review sentiment with commercial rights"),
        ("Twitter emotion detection model for commercial use", "Social media multi-class emotion classification"),
        ("Small sentiment model for Hindi I can use in a commercial app", "Lightweight Hindi sentiment classifier with Apache-2.0"),
        ("Bengali text classification for customer reviews", "Customer support sentiment in Bengali"),
    ],
    "🔍 Sentence Similarity & Semantic Search": [
        ("Fast English sentence embeddings under 200 MB for semantic search", "Sub-200 MB embedding models for fast document search"),
        ("Sentence embeddings for Bengali that I can modify and sell", "Commercial and modifiable embeddings for Bengali"),
        ("Hindi sentence similarity model under 500 MB", "Compact Hindi semantic search model"),
        ("Multilingual Indic sentence similarity covering 10+ languages", "Cross-lingual similarity across Indic scripts"),
    ],
    "🌐 Machine Translation": [
        ("English to French translation under 500 MB", "Lightweight European translation model"),
        ("Commercial Hindi to Marathi translation", "Directionally verified cross-lingual Indic translation"),
        ("English to Hindi machine translation under 500 MB", "English-to-Hindi localization under 500 MB"),
        ("Urdu to English translation I can use in a product", "Commercial product translation for customer support"),
    ],
    "🏷️ Named Entity Recognition (NER)": [
        ("English named entity recognition model with permissive license", "Standard English CoNLL-03 NER with Apache/MIT license"),
        ("Marathi NER model under 500 MB for noisy social-media text", "Social media token classification under 500 MB"),
        ("Tamil token classification model for news articles", "Regional token classification for news corpora"),
        ("Telugu named entity recognition I can deploy commercially", "Production-ready commercial NER"),
    ],
    "⚡ Edge & Low-Resource Deployment (< 300 MB)": [
        ("Tiny English speech-to-text model under 150 MB for mobile", "Edge Whisper Tiny on-device model"),
        ("Lightweight Hindi sentiment analysis under 200 MB", "On-device classification for edge devices"),
        ("Tamil speech-to-text under 500 MB that handles phone call audio", "Embedded telephony speech recognition"),
    ],
    "🖼️ Vision (images)": [
        ("Image classification model for plant diseases", "Sort photos into categories"),
        ("I need an image classifier I can use commercially", "Image classification with a commercial license"),
        ("Object detection for traffic cameras, small", "Find and locate objects in images, small size"),
        ("Image segmentation model for medical scans", "Outline regions of images"),
        ("Segment satellite images, I can fine-tune it", "Segmentation you are allowed to modify"),
    ],
    "✍️ Text Generation, Summarization & Question Answering": [
        ("Small language model for text generation I can fine-tune", "A compact model you can build on"),
        ("Summarization model for news articles, commercial use", "Summarize long text with commercial rights"),
        ("Question answering model over a passage, under 500 MB", "Answer questions from a given text"),
    ],
    "🔄 Interactive & Constraint Demos": [
        ("I want a Hindi model", "Tests Ambiguity Clarification: asks user to pick a task"),
        ("Hindi to Marathi translation under 1 MB", "An impossible request: nothing can be verified, so every result is ⚠️ with a banner"),
        ("Tamil NER model I can fine-tune", "Tests Modifiability & 'Build on it' adaptation guide"),
    ],
}


def render_examples_tab() -> None:
    st.markdown("### 💡 Browse Example Queries by Task & Capability")
    st.caption("Click **'Use query ↗️'** next to any example to populate the search bar and run constraint verification immediately in the **Search** tab.")

    selected = st.session_state.get("query", "")
    if selected:
        st.info(f"Currently loaded: **{selected}** — *switch to the **Search** tab to see verified results.*")

    for cat_name, queries in EXAMPLE_CATEGORIES.items():
        st.markdown(f"#### {cat_name}")
        for q, desc in queries:
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"**{q}**  \n*{desc}*")
            if c2.button("Use query ↗️", key=f"cat-ex-{q}"):
                _fresh(q)
                st.rerun()
        st.divider()


def main() -> None:
    st.set_page_config(page_title="HF Model Finder", page_icon="🔎")
    st.title("HF Model Finder")
    st.caption(DISCLAIMER)
    if CFG.get("snapshot_date"):
        st.caption(f"Data snapshot: {CFG['snapshot_date']}")
    if mode_from_env() == "replay":
        st.caption("Replay mode: showing recorded runs, no live services.")

    search_tab, examples_tab, check_tab = st.tabs(["Search", "Examples", "Check a model"])

    with search_tab:
        st.write("Try an example:")
        for example in EXAMPLE_QUERIES:
            if st.button(example, key=f"ex-{example}"):
                _fresh(example)
        st.caption("💡 Looking for more tasks and categories? Browse 25+ diverse queries in the **Examples** tab above.")
        query = st.text_input("Describe the model you need", key="query")
        compare = st.checkbox("Compare with naive RAG", key="compare",
                              help="Runs the same request with no filters and no verification, to show what the checks change.")

        action = st.session_state.pop("action", None)
        if query and st.button("Search"):
            _fresh()
        if query and action:
            import time

            t0 = time.time()
            est_time = "~5–8s" if compare else "~3–5s"
            with st.spinner(f"⏳ Searching & verifying models against constraints... (Estimated time: {est_time})"):
                try:
                    graph = get_graph()
                except Exception as e:  # no index built yet, missing keys, ...: say what is missing instead of a traceback
                    st.error(f"Search is unavailable: {e}")
                    graph = None
                if graph is not None:
                    carried = {}
                    if action == "followup" and "state" in st.session_state:
                        prev = st.session_state["state"]
                        carried = {k: prev[k] for k in ("clarifications_asked", "relax_count") if k in prev}
                    request = {"query": query, "overrides": st.session_state.get("overrides", {}), **carried}
                    try:
                        st.session_state["state"] = graph.invoke(request)
                        if compare:
                            st.session_state["naive_state"] = get_graph("naive").invoke(request)
                        st.session_state["elapsed"] = time.time() - t0
                    except MissingRecording as e:
                        st.warning(str(e))
                    except Exception as e:
                        st.error(f"Search failed: {e}")
        if "state" in st.session_state:
            state = st.session_state["state"]
            elapsed = st.session_state.get("elapsed")
            if elapsed is not None:
                st.caption(f"⏱️ Search completed in **{elapsed:.1f}s** (estimated ~{'5–8s' if compare else '3–5s'})")
            if compare and "naive_state" in st.session_state:
                st.info(state["intent"])
                render_compare(state, st.session_state["naive_state"])
            else:
                render_state(state)
            if state.get("outcome") != "out_of_scope":      # nothing was understood, so there is nothing to edit
                st.divider()
                render_intent_editor(state.get("constraints") or {})

    with examples_tab:
        render_examples_tab()

    with check_tab:
        render_check_tab()

    with st.expander("Glossary"):
        for term, text in TOOLTIPS.items():
            st.markdown(f"**{term}**: {text}")


if __name__ == "__main__":
    main()
