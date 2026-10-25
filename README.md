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
├── config.yaml         # models, embedding, retrieval (verify_pool), size words, loop caps, snapshot checksum (D21)
├── data/               # raw/ (cached API responses), snapshot-<date>/, embeddings/, localindex/ (gitignored)
├── demo/               # plan.json (what the demo shows) and cache/ (recorded runs for REPLAY=1)
├── eval/               # queries.jsonl, extraction_test.jsonl, run_eval.py, metrics.py, labels/ (blind sheets),
│                       #   label_app.py + relevance_report.py, faithfulness_app.py + faithfulness_report.py,
│                       #   results/ (v1, v2, ablation, Pinecone run), seen.md
├── scripts/            # record_demo, poison_test, parse_queries, pinecone_semantics_check, tryit_smoke, make_faithfulness_set
├── src/
│   ├── ingest.py       # resumable fetch of Hub metadata + cards, canonical base-model ids
│   ├── clean.py        # card cleaning, doc_quality, metadata fallback chunk (D20)
│   ├── normalize.py    # size rule, license rights, languages, multilingual map, lineage fields
│   ├── index.py        # chunking, embedding (hosted, cached), upsert to Pinecone or the local index
│   ├── embedder.py     # hosted / local embeddings with a content-hash cache
│   ├── localindex.py   # exact vector search with Pinecone filter semantics (default store, verified equal)
│   ├── llm.py          # extract_constraints() + deterministic backstop, explain(), provider switch, cache, throttle
│   ├── retrieve.py     # Pinecone filters (D12), chunk -> model grouping (D18)
│   ├── evidence.py     # which card passages the explanation sees, trimmed to a token budget
│   ├── rerank.py       # hosted bge-reranker-v2-m3 (cached) or local (D9)
│   ├── baselines.py    # naive RAG, keyword (BM25), HF Hub filters (D19)
│   ├── pipeline.py     # build_pipeline(variant): wires the real dependencies into the graph
│   ├── checker.py      # check-a-model
│   ├── replay.py       # record / replay demo runs (REPLAY=1, RECORD=1)
│   ├── snapshot.py     # deterministic metadata snapshot + data-quality report
│   ├── verify.py       # pass / fail / unknown, size-word table
│   ├── guide.py        # intent text, clarifying questions, Try-it templates, tooltips (D13)
│   ├── adapt.py        # rights notes, lineage, memory estimate (D14)
│   └── graph.py        # LangGraph pipeline with loop caps (D15)
├── tests/
└── app.py              # Streamlit UI
```

## Status (2026-10-21)

Built, run against the live services, and evaluated. 15,991 models fetched over **11 tasks** (the original 9,764 over five, plus image classification, object detection, image segmentation, text generation, summarization and question answering added on 2026-10-25), 48,179 chunks embedded and
upserted to Pinecone (and an exact local index), 100 evaluation queries run through five systems on the original five-task corpus (reproducible, see docs/evaluation-plan.md §9), outputs frozen.
On the 75 normal queries the full system recommends no model that fails a constraint, 83% of its
recommendations are fully verified (naive RAG: 29%), and the Hub's own filters violate a constraint on 26 to 33%.
Numbers: [eval/results/results-v2.md](eval/results/results-v2.md). Data notes and live checks:
[docs/data-notes.md](docs/data-notes.md).

Relevance and faithfulness were graded by independent Claude agents (LLM judges, not humans): ours has the highest mean relevance grade
(1.28, against 1.06 keyword, 0.87 naive and 0.69 for the Hub filters) and 81.6% of explanation claims are supported by the cited card text
([eval/results/relevance.md](eval/results/relevance.md), [eval/results/faithfulness.md](eval/results/faithfulness.md),
[eval/labels/PROVENANCE.md](eval/labels/PROVENANCE.md)). Still to do (yours): rehearse the demo, finish the write-up
([docs/writeup.md](docs/writeup.md)), attach the snapshot to a Release, rotate the keys. See [docs/implementation-plan.md](docs/implementation-plan.md).

## Run

```bash
streamlit run app.py                          # the UI (live)
REPLAY=1 streamlit run app.py                 # recorded demo runs, no network needed
python -m eval.run_eval --tag v3 --label 40   # all five systems on the 100 queries
```

## Tests

```bash
pytest        # about 300 tests, no network, under a minute
```
