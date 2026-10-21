# HF Model Finder

Constraint-verified RAG for finding Hugging Face models. Ask in natural language
("a Marathi NER model under 500 MB, usable commercially, good on noisy social-media
text") and get back models that **provably** meet the hard constraints, with an
honest ✅ / ❌ / ⚠️ table for each one.

- **Docs index:** [docs/README.md](docs/README.md)
- **What & how:** [docs/PROJECT.md](docs/PROJECT.md) · **Why:** [docs/decisions.md](docs/decisions.md)
- **Architecture:** [docs/architecture.md](docs/architecture.md) · **Plan:** [docs/implementation-plan.md](docs/implementation-plan.md) · **Tests & edge cases:** [docs/testing-strategy.md](docs/testing-strategy.md)

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m src.check_env --init   # creates .env; then fill in the keys it lists
python -m src.check_env          # verifies the setup without printing any secret
```

## Layout

```
├── docs/               # PROJECT, decisions, architecture, plan, testing, data, evaluation, demo, security, dev
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
│   ├── evidence.py     # which card passages the explanation sees, trimmed to a token budget
│   ├── tokens.py       # shared token estimator
│   ├── rerank.py       # local bge-reranker-v2-m3 (D9)
│   ├── replay.py       # record / replay demo runs (REPLAY=1, RECORD=1)
│   ├── snapshot.py     # deterministic metadata snapshot + data-quality report
│   ├── verify.py       # pass / fail / unknown, size-word table
│   ├── guide.py        # intent text, clarifying questions, Try-it templates, tooltips (D13)
│   ├── adapt.py        # rights notes, lineage, memory estimate, reported metrics (D14, D24)
│   └── graph.py        # LangGraph pipeline with loop caps (D15)
├── tests/
└── app.py              # Streamlit UI (graph state in st.session_state)
```

## Status

Built and unit-tested offline (157 tests): license/rights map, size rule, `verify`, Pinecone
filters, grouping, cleaning, chunking, guidance, build-on estimates, prompt-injection delimiters,
the LangGraph pipeline (with stub dependencies), eval metrics, snapshot and replay, the local
reranker (with a fake scorer), and the UI renderer.

Not yet built, or never run against live services: Hub ingestion (`python -m src.ingest counts`
is the day-1 check), the index build `main()`, `_live_graph()` wiring in `app.py`
(embedder, Pinecone, reranker), the check-a-model lookup, the baselines flags, and
`eval/queries.jsonl`. See [docs/implementation-plan.md](docs/implementation-plan.md).

## Tests

```bash
pytest
```
