# Development guide

## 1. Setup

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # then fill it in
pytest                                                 # offline, ~3 s
```

Python 3.10+ (the code uses `X | None` annotations). Windows is fine: all file I/O is
explicit UTF-8.

## 2. Environment variables (`.env`)

| Variable | Used by | Notes |
|---|---|---|
| `HF_TOKEN` | `ingest` | optional; raises Hub rate limits |
| `PINECONE_API_KEY` | indexing / retrieval | required for live runs |
| `LLM_PROVIDER` | `llm` | `groq` (default) or `ollama` |
| `GROQ_API_KEY`, `GROQ_MODEL` | `llm` | required when `LLM_PROVIDER=groq` |
| `OLLAMA_HOST`, `OLLAMA_MODEL` | `llm` | host defaults to `http://localhost:11434` |
| `LLM_CACHE_DIR` | `llm` | defaults to `.cache/llm` |

A missing variable currently raises a bare `KeyError` (E-LLM-10): improve this message if it bites.

## 3. Common commands

```bash
python -m src.ingest counts          # models per task: the day-1 sizing check
python -m src.ingest fetch           # resumable fetch into data/raw/
streamlit run app.py                 # the UI
pytest -k graph -q                   # a subset
```

## 4. Repository conventions

- **Branches:** work on a feature branch; do not push to `main` directly.
- **Commits:** imperative subject, body says *why*. One logical change per commit.
- **The D2 rule:** nothing from `llm.py` or card text may flow into `verify.py`. If a
  change needs that, raise it as a design change first.
- **Unknown handling (D12):** a field that can be missing must have a `*_status` or
  `unknown` state, be omitted (not sentinel-filled) when unknown, and be filtered with an
  explicit `$or`.
- **Config over constants:** thresholds live in `config.yaml`; modules read `CFG`.
- **File I/O:** always pass `encoding="utf-8"`.
- **Docs:** if you change behaviour listed in [architecture.md §11](architecture.md), update
  that table; if you change a decision, update [decisions.md](decisions.md) with a dated entry.

## 5. Pinecone namespaces

| Namespace | Purpose | Rule |
|---|---|---|
| `prod` | demo data | change only deliberately, after a rehearsal |
| `exp-<yourname>` | your experiments | free to rebuild; create a fresh namespace per rebuild rather than upserting over an old one (orphan chunks, E-IDX-12) |

Set the namespace in `config.yaml: pinecone.namespace` (do not commit a personal `exp-*` value).

## 6. How to…

| Task | Steps |
|---|---|
| Add a license | `normalize.LICENSE_RIGHTS`; add the id to a test in `tests/test_normalize.py` |
| Add a multilingual model | `normalize.MULTILINGUAL_MODELS` after checking the card's language list |
| Change a size threshold | `config.yaml: size_words_mb`; update the tests that assert the numbers |
| Add a constraint | extraction key and `clean_constraints`; a `verify` check; a `build_filter` clause; a `guide.describe_intent` phrase; tests for each; update [architecture.md §5](architecture.md#5-filter-vs-verify-two-layers-one-truth) |
| Change the embedding model | `config.yaml: embedding.*`; **re-index everything** into a fresh namespace |
| Debug a wrong ✅/❌ | print `meta` for the model and `verify.verify(meta, constraints)`; the cause is almost always metadata, not logic |
| Replay an LLM response | it is already in `.cache/llm/`; delete the file to force a new call |

## 7. Troubleshooting

| Symptom | Likely cause |
|---|---|
| `ModuleNotFoundError: src` | run from the repo root (tests and `python -m src.ingest` rely on it) |
| Streamlit shows "Search isn't wired up" | `app.get_graph()` is still a stub (WP5) |
| Every model fails the task check | an override carried a bad task value (E-GRAPH-12) |
| Hindi models missing from results | check `language_status`/`languages` in the raw record; the card may spell the language unusually |
| Ingest keeps retrying | Hub rate limit; set `HF_TOKEN`, or rerun later (it resumes) |
