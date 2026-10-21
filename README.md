# HF Model Finder

Constraint-verified RAG for finding Hugging Face models. Ask in natural language
("a Marathi NER model under 500 MB, usable commercially, good on noisy social-media
text") and get back models that **provably** meet the hard constraints, with an
honest ✅ / ❌ / ⚠️ table for each one.

- **What & how:** [PROJECT.md](PROJECT.md)
- **Why:** [decisions.md](decisions.md)

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in the keys
```

## Layout

```
├── PROJECT.md          # what & how
├── decisions.md        # why (D1-D24)
├── config.yaml         # embedding model, chunk size, k, size words, loop caps (D21)
├── data/               # raw/ (cached API responses) + snapshot-<date>/ (gitignored)
├── eval/               # queries.jsonl (not yet written, see eval/README.md), labels/, baselines/, metrics.py, run_eval.py
├── src/
│   ├── ingest.py       # resumable fetch of Hub metadata + cards (D21)
│   ├── clean.py        # card cleaning, doc_quality, metadata fallback chunk (D20)
│   ├── normalize.py    # size rule, license rights, languages, multilingual map, lineage fields
│   ├── index.py        # chunking, local embeddings, Pinecone upsert
│   ├── llm.py          # extract_constraints(), explain(), provider switch, cache, D17 delimiters
│   ├── retrieve.py     # Pinecone filters (D12), chunk -> model grouping (D18)
│   ├── verify.py       # pass / fail / unknown, size-word table
│   ├── guide.py        # intent text, clarifying questions, Try-it templates, tooltips (D13)
│   ├── adapt.py        # rights notes, lineage, memory estimate, reported metrics (D14, D24)
│   └── graph.py        # LangGraph pipeline with loop caps (D15)
├── tests/
└── app.py              # Streamlit UI (graph state in st.session_state)
```

## Status

Built and unit-tested offline: license/rights map, size rule, `verify`, Pinecone filters,
grouping, cleaning, chunking, guidance, build-on estimates, prompt-injection delimiters,
the LangGraph pipeline (with stub dependencies), eval metrics, and the UI renderer.

Not yet built or never run against live services: Hub ingestion (`python -m src.ingest counts`
is the day-1 check), the index build `main()`, `get_graph()` wiring in `app.py`
(embedder, Pinecone, reranker), check-a-model lookup, baselines, and `eval/queries.jsonl`.

## Tests

```bash
pytest
```
