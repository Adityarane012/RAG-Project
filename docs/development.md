# Development guide

## 1. Setup

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m src.check_env --init                         # creates .env from .env.example (never overwrites)
# open .env and fill in the keys (comments say where to get each one)
python -m src.check_env                                # reports set/missing; never prints a value
pytest                                                 # offline, ~3 s
```

Python 3.10+ (the code uses `X | None` annotations). Windows is fine: all file I/O is
explicit UTF-8, paths use `pathlib`, and `PYTHONUTF8=1` makes the console and any third-party
code agree. Ollama and Streamlit both run on Windows.

## 2. Environment variables (`.env`)

| Variable | Used by | Notes |
|---|---|---|
| `HF_TOKEN` | `ingest` | optional; raises Hub rate limits |
| `PINECONE_API_KEY` | indexing / retrieval | required for live runs |
| `LLM_PROVIDER` | `llm` | `groq` (default) or `ollama` |
| `GROQ_API_KEY` | `llm` | required when `LLM_PROVIDER=groq` |
| `GROQ_MODEL`, `OLLAMA_MODEL` | `llm` | **optional overrides**; the models are pinned in `config.yaml` (`llm.*`: `openai/gpt-oss-20b`, `qwen2.5:7b-instruct`) |
| `OLLAMA_HOST` | `llm` | defaults to `http://localhost:11434` |
| `REPLAY`, `RECORD`, `REPLAY_DIR` | `replay` | `REPLAY=1` serves recorded demo runs (wins over `RECORD`); `RECORD=1` saves live runs; dir defaults to `demo/cache` |
| `PYTHONUTF8` | Python | set to `1` on Windows |
| `LLM_CACHE_DIR` | `llm` | defaults to `.cache/llm` |

Tuning knobs for the free-tier token limits are in `config.yaml`: `llm.tpm` (per-model per-minute
budget), `llm.output_reserve_tokens`, `explain.chunks_per_model` and `explain.max_prompt_tokens`.
After changing a model, check the TPM/TPD your account actually has in the Groq console and update `llm.tpm`.

`.env` is loaded automatically by `src/config.py` (real environment variables win). A missing
`GROQ_API_KEY` raises a `RuntimeError` that names it.

## 3. Common commands

```bash
python -m src.ingest counts          # models per task: the day-1 sizing check
python -m src.ingest fetch           # resumable fetch into data/raw/, then canonical base-model ids
python -m src.snapshot build         # snapshot + data-quality report + the lines for config.yaml
RECORD=1 streamlit run app.py        # record demo runs  (REPLAY=1 to play them back)
streamlit run app.py                 # the UI
pytest -k graph -q                   # a subset
```

## 4. Repository conventions

- **Branches:** `main` is protected (set this in GitHub: require a PR, no direct pushes). Every change goes on a feature branch and through a PR; the history is part of the portfolio.
- **Keys:** each member creates their own free Groq key (this also multiplies the rate limit) and a read-only HF token. One person (B) creates the single Pinecone index and shares its key privately; everyone else writes only to their own `exp-<name>` namespace.
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
| Add a multilingual model | `normalize.MULTILINGUAL_MODELS`: a `MultilingualEntry` with the language list **and the source it came from**; leave `checked=False` until the list has been compared with that source (data lead owns this) |
| Change a size threshold | `config.yaml: size_words_mb`; update the tests that assert the numbers |
| Add a constraint | extraction key and `clean_constraints`; a `verify` check; a `build_filter` clause; a `guide.describe_intent` phrase; tests for each; update [architecture.md §5](architecture.md#5-filter-vs-verify-two-layers-one-truth) |
| Change the embedding model | `config.yaml: embedding.*`; **re-index everything** into a fresh namespace |
| Cut and share a snapshot | `python -m src.snapshot build`; attach `records.jsonl.gz` to a GitHub Release; paste `snapshot_date`, `snapshot_sha256`, `snapshot_url` into `config.yaml`; teammates load it with `snapshot.load_snapshot(path, CFG["snapshot_sha256"])` |
| Record the demo | see [demo-runbook.md](demo-runbook.md) §1 |
| Debug a wrong ✅/❌ | print `meta` for the model and `verify.verify(meta, constraints)`; the cause is almost always metadata, not logic |
| Replay an LLM response | it is already in `.cache/llm/`; delete the file to force a new call |

## 7. Troubleshooting

| Symptom | Likely cause |
|---|---|
| `ModuleNotFoundError: src` | run from the repo root (tests and `python -m src.ingest` rely on it) |
| Streamlit shows "Search isn't wired up" | `app._live_graph()` is still a stub (task 4.2 in the implementation plan) |
| Every model fails the task check | an override carried a bad task value (E-GRAPH-12) |
| Hindi models missing from results | check `language_status`/`languages` in the raw record; the card may spell the language unusually |
| Ingest keeps retrying | Hub rate limit; set `HF_TOKEN`, or rerun later (it resumes) |
