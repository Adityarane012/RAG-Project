# Architecture

How the system is built and why each piece sits where it does. For *what* we are
building see [PROJECT.md](PROJECT.md); for *why* each choice was made see
[decisions.md](decisions.md) (cited below as D1, D2, …).

## 1. Principles

These three rules explain most of the design. If a change breaks one, stop and discuss.

1. **The LLM parses and explains; code verifies (D2).** Every yes/no fact about a model
   (size, license rights, language, task) is computed in `src/verify.py` from metadata.
   No LLM output and no card text is ever an input to a verification result.
2. **Unknown is a first-class answer (D3, D12).** Every field that can be missing has an
   explicit `unknown` state, is filtered with an explicit `$or`, and is shown as ⚠️.
   Never write a sentinel (`0`, `-1`, `1e9`) and never silently drop a model.
3. **Every number shown to the user comes from code or metadata.** Thresholds from the
   size-word table, memory from `adapt.py`, rights from the license map.

Plus one invariant: **queries and documents are embedded with the same model** (D8).
Changing `embedding.model` in `config.yaml` means re-indexing everything.

## 2. System overview

```
                OFFLINE (run once per snapshot)                          ONLINE (per query)
 ┌───────────────────────────────────────────────────┐   ┌────────────────────────────────────────────────┐
 │ HF Hub API                                         │   │ user query ─► [extract] ─► clarify? ─► END     │
 │   │ list_models (5 tasks × (top-1000 ∪ Indic))     │   │                  │ (≤2 questions, UI re-invokes)│
 │   ▼                                                │   │                  ▼                              │
 │ ingest.py ──► data/raw/<id>.json + .md (cached)    │   │            [retrieve] Pinecone filter + ANN     │
 │   ▼                                                │   │                  ▼  ~50 chunks (widen to ≥5 models)
 │ normalize.py  (metadata, unknowns marked)          │   │            [rerank]  reorder, group → top 5     │
 │ clean.py      (card text, doc_quality)             │   │                  ▼                              │
 │   ▼                                                │   │            [verify]  pass / fail / unknown      │
 │ index.py: chunk by section ─► e5 embeddings ───────┼──►│ Pinecone     ├─ none viable ─► relax? / abstain │
 │            (local, 1024-d)      upsert, namespaced │   │ (prod/exp-*) └─ ≥1 viable ─► [enrich] ─► [explain]│
 └───────────────────────────────────────────────────┘   │                         ▼                        │
                                                          │     Streamlit: ranked models + ✅/❌/⚠️ table +  │
                                                          │     Try it + Build on it + disclaimer            │
                                                          └────────────────────────────────────────────────┘
```

Check-a-model (D23) is a second entry point that skips retrieval: it feeds one model's
metadata to `verify.verify` and `adapt.model_report`.

## 3. Modules

| Module | Responsibility | Key functions | Imports |
|---|---|---|---|
| `config.py` | Load `config.yaml` once | `CFG` | – |
| `ingest.py` | Resumable fetch of Hub JSON + README into `data/raw/` | `candidate_ids`, `fetch_raw`, `load_raw`, `log_failure` | config |
| `clean.py` | Strip card noise, judge doc quality, build fallback chunk | `clean_card`, `doc_quality`, `fallback_chunk` | config |
| `normalize.py` | Raw Hub record → metadata; license map; size rule; multilingual map | `normalize_record`, `license_rights`, `size_mb`, `normalize_languages` | config |
| `index.py` | Section chunking, e5 embeddings, vector building, upsert | `chunk_card`, `build_vectors`, `embed_query`, `upsert` | clean, normalize |
| `rerank.py` | Local cross-encoder reranker (`bge-reranker-v2-m3`); replaces chunk scores | `LocalReranker` | config |
| `replay.py` | Record / replay final graph states for the demo (`RECORD=1` / `REPLAY=1`) | `ReplayGraph`, `run_key` | config |
| `snapshot.py` | Cut a deterministic, checksummed metadata snapshot; data-quality report | `build`, `load_snapshot`, `data_quality_report` | ingest, clean, normalize |
| `verify.py` | The only place a ✅/❌/⚠️ is decided; size-word table; ranking key | `verify`, `overall`, `rank_key`, `notes`, `resolve_max_size_mb` | config |
| `retrieve.py` | Pinecone filter from constraints; k-widening; chunk → model grouping | `build_filter`, `fetch_chunks`, `group_by_model`, `pinecone_fetch` | config, verify |
| `llm.py` | Provider switch + cache; constraint extraction; delimiters; explanations | `complete`, `extract_constraints`, `clean_constraints`, `wrap_card_section`, `explain` | verify |
| `guide.py` | Beginner layer: intent text, clarifying question, relax offer, Try-it | `describe_intent`, `clarifying_question`, `relaxation_offer`, `try_it_snippet` | verify |
| `adapt.py` | Rights notes, lineage, memory estimate, reported metrics, per-model report | `model_report`, `memory_estimate`, `lineage`, `reported_metrics` | guide, verify |
| `graph.py` | LangGraph wiring, routing, loop caps; all I/O injected via `Deps` | `build_graph`, `Deps`, `route_after_*` | adapt, guide, retrieve, verify |
| `app.py` | Streamlit UI and result renderer | `render_state`, `main` | graph (via `get_graph`) |
| `eval/metrics.py` | Automatic metrics shared by every system under test | `violation_rate_at_k`, … | verify, normalize |

Dependency direction is strictly downward: `verify` imports nothing from the pipeline,
so it can be tested and trusted in isolation. `llm` may import `verify` (for the size-word
list) but `verify` must never import `llm`.

## 4. Data model

### 4.1 Pinecone vector

- **id:** `<model_id>::<chunk index>`
- **values:** 1024-d `multilingual-e5-large` embedding, normalised; passages are prefixed
  `passage: `, queries `query: `.
- **namespace:** `prod` (demo data, changed only deliberately) or `exp-<name>` (D21).
- **metadata:** identical on every chunk of a model, plus per-chunk `section` and `text`.

| Field | Type | Written when | Source | Filter | Verify |
|---|---|---|---|---|---|
| `model_id` | str | always | Hub | – | – |
| `task` | str | when the Hub has a `pipeline_tag` | Hub | `$eq` | `check_task` |
| `downloads` | int | always | Hub | – | – (sampling only, never ranking, D6) |
| `languages` | list[str] | when known (else `[]`) | `cardData.language` ∪ multilingual map | `$in` | `check_languages` |
| `language_status` | `known`/`unknown` | always | derived | `$eq unknown` branch of `$or` | `check_languages` |
| `multilingual` | bool | always | map, or card says "multilingual" | – | note only |
| `size_mb` | float | **only when known** | D20 size rule | `$lte` | `check_size` |
| `size_status` | `known`/`unknown` | always | derived | `$eq unknown` branch of `$or` | `check_size` |
| `param_count` | int | only when known | `safetensors.total` | – | memory estimate |
| `commercial` | `yes`/`no`/`conditional`/`unknown` | always | license map | `$in [yes,conditional,unknown]` | `check_right` |
| `modifiable` | same | always | license map | same | `check_right` |
| `base_model` | str | only when declared | `cardData.base_model` | – | lineage |
| `lineage_status` | `known`/`unknown` | always | derived | – | lineage |
| `doc_quality` | `full`/`minimal` | always | `clean.doc_quality` | – | note only |
| `directions` | list[str] `"hi-mr"` | only when stated | the `opus-mt-<src>-<tgt>` model id (D18) | – | `check_direction` |
| `direction_source` | str | with `directions` | `"model_name"` | – | note "direction from model name" |
| `section`, `text` | str | per chunk | chunker | – | `text` feeds `explain` |

Pinecone rejects `null` metadata, so `build_vectors` drops `None` values.

### 4.2 Constraints (output of `llm.extract_constraints`, editable in the UI)

```python
{"task": str | None,            # one of the five task tags, else None
 "langs": [str],                # 2-letter codes; a stated direction adds both
 "direction": [src, tgt] | None,
 "max_size_mb": float | None,   # only if the user gave an explicit number
 "size_word": str | None,       # key of config.yaml size_words_mb
 "commercial": True | None,
 "modifiable": True | None,
 "soft_query": str}             # what the embedding search is run on
```

`clean_constraints` validates the LLM's JSON: anything off-schema becomes `None`/`[]`.
Size words stay words until `verify.resolve_max_size_mb` turns them into numbers.

## 5. Filter vs verify: two layers, one truth

Retrieval *filters* are a coarse, recall-preserving pre-selection. `verify` is the
authoritative check, run on every returned model. A filter must therefore never be
*stricter* than verify; it may be looser.

| Constraint | Filter keeps | Verify result | Why the filter is loose |
|---|---|---|---|
| size | `size_mb ≤ limit` **or** `size_status = unknown` | pass / fail / **unknown** | a missing field never matches `$lte`; D12 |
| commercial / modifiable | everything except definite `no` | `yes`→pass, `no`→fail, `conditional`/`unknown`→**unknown** | conditional needs a human to read the terms |
| language | `language ∈ languages` **or** `language_status = unknown` | pass / fail / unknown | multilingual-map models already have languages merged in |
| task | `task = value` | pass / fail | – |
| direction | *(not filtered)* | pass only if stated (today: an `opus-mt-<src>-<tgt>` id in the requested direction), else **unknown**; never fail | a language list can't tell hi→mr from mr→hi (D18) |

## 6. Online pipeline (LangGraph, D15)

### 6.1 Nodes

| Node | Reads | Writes | Notes |
|---|---|---|---|
| `extract` | `query`, `overrides` | `constraints`, `intent` | `constraints.update(overrides)`: key *presence* counts, so `{"commercial": None}` clears a constraint |
| `clarify` | `constraints` | `question`, `clarifications_asked+1`, `outcome=clarify` | ends the run (waits for the user) |
| `retrieve` | `constraints` | `matches` | `fetch_chunks`: doubles `k` until ≥5 distinct models, `k_max`, or the index is exhausted |
| `rerank` | `matches`, `soft_query` | `candidates` | `deps.rerank` reorders chunks; `group_by_model` keeps each model's best chunk, top 5 |
| `verify` | `candidates`, `constraints` | `results`, `closest` | each result: `table`, `overall`, `notes`; stable sort by `rank_key` |
| `relax` | `constraints` | `relax_offer`, `relax_count+1`, `outcome=relax` | ends the run |
| `abstain` | – | `outcome=abstain` | ends the run; UI shows `closest` |
| `enrich` | viable `results` | `reports` | `adapt.model_report` + templated Try-it snippet |
| `explain` | viable `results` | `explanations`, `explain_error`, `fully_verified`, `outcome=answer` | LLM failure is caught: the verified table must still render |

### 6.2 Routing

```
START → extract ─┬─ task/key constraint missing AND asked < 2 → clarify → END
                 └─ otherwise ───────────────────────────────→ retrieve → rerank → verify
verify ─┬─ any result with overall ≠ fail ─────────────────────→ enrich → explain → END
        ├─ none viable AND relax_count < 1 AND an offer exists → relax → END
        └─ otherwise ─────────────────────────────────────────→ abstain → END
```

"Key constraint missing" (`guide.clarifying_question`): no task, or a translation request
naming fewer than two languages (a stated `direction` counts as two).

### 6.3 How the loops close

`clarify` and `relax` **end the run** with a question in the state. The UI shows it, then
calls `graph.invoke` again with the user's answer in `overrides` and the counters
(`clarifications_asked`, `relax_count`) copied over. The graph therefore holds no hidden
state between turns, the UI owns it (`st.session_state`, D16), and the caps are plain
integers that cannot be reset by a rerun. A brand-new search must **not** carry counters
or overrides: `app._fresh` clears them.

Caps (config): 2 clarifying questions, 1 relax-and-retry. After the cap the graph
proceeds with what it has (clarify) or abstains (relax).

### 6.4 "Viable" and abstention

A result is *viable* if `overall ≠ fail`. If every candidate is only ⚠️ the answer is shown
with flags rather than abstaining, because "unknown" is information, not a violation.
The state carries `fully_verified` (false when no result is a full pass) and the UI shows the banner "No model fully verified". Abstention therefore means *every* candidate fails with a known ❌, which is why the impossible evaluation queries must be verifiably impossible (`eval.metrics.verifiably_impossible`, [evaluation-plan.md](evaluation-plan.md)). Decided 2026-10-21.

### 6.5 Injected dependencies (`graph.Deps`)

| Dependency | Contract |
|---|---|
| `extract(query) -> constraints` | `llm.extract_constraints`; raises `ValueError` on bad JSON |
| `fetch(filter, top_k) -> [match]` | each match `{"id", "score", "metadata": {...}}`; `retrieve.pinecone_fetch` builds it |
| `rerank(soft_query, matches) -> matches` | `rerank.LocalReranker` implements it. **Must return the same match dicts with `score` replaced by the reranker's score**: `group_by_model` ranks by `score` |
| `explain(constraints, results) -> [ {model_id, text, ...} ]` | `llm.explain`; output is filtered to candidate ids |
| `lineage_index` | `adapt.build_lineage_index(snapshot records)` |
| `card_data(model_id) -> dict \| None` | for `model-index` metrics; optional |

Nothing in `graph.py` touches the network, so the whole graph runs in tests with stubs.

## 7. LLM layer

- **One interface, two providers.** `complete(prompt, system)` dispatches on
  `LLM_PROVIDER` (`groq` | `ollama`). Switching is an environment variable (D7).
- **Cache.** Every response is stored in `.cache/llm/<sha256>.json`, keyed by
  `(provider, model, system, prompt)`. Temperature is 0. The cache makes runs
  reproducible and protects against rate limits.
- **Output is untrusted.** `clean_constraints` validates extraction; `filter_citations`
  restricts explanations to candidate ids; neither output reaches `verify`.
- **Card text is data (D17).** `wrap_card_section` wraps each chunk in
  `<card_section model_id=… section=…>`, HTML-escapes the attributes, and neutralises any
  literal `<card_section` / `</card_section` in the text (case- and whitespace-tolerant).
  The system prompt tells the model never to follow instructions inside the tags.

### 7.1 Recording and replay (D21)

Retrieval needs Pinecone and query embedding, so only the LLM can be cached for real.
For the demo, `replay.ReplayGraph` wraps the compiled graph with the same `.invoke`:

| Mode | Set by | Behaviour |
|---|---|---|
| live | default | pass-through |
| record | `RECORD=1` | run live, save the final state to `demo/cache/<key>.json` |
| replay | `REPLAY=1` | serve the saved state, never touch a service; a missing recording raises `MissingRecording` with instructions. Wins over `RECORD` |

The key hashes the query, the overrides and the carried loop counters, so a
clarify → answer → relax sequence replays step by step. Replay shows what the system *did*
on the recorded run; it is evidence of a rehearsed run, not a live computation, and the
demo should say so.

## 8. Failure and degradation

| Failure | Behaviour |
|---|---|
| Groq rate-limited | One retry on `llm.groq_fallback_model`; the cache file records which model answered |
| Groq down / still limited | Switch `LLM_PROVIDER=ollama` (rehearsed, D7); cached responses still serve |
| LLM returns invalid JSON at extraction | `ValueError` surfaces to the UI (extraction cannot be skipped) |
| LLM fails or returns junk at explanation | Caught in `explain` node: table and Try-it still render, UI shows a warning |
| Planned demo query, no network | `REPLAY=1` serves the recorded run (see §7.1) |
| Pinecone returns nothing | `verify` sees no candidates → relax offer (if one exists) → abstain |
| Card missing / empty | Single metadata fallback chunk, `doc_quality: minimal`, UI note |
| Hub fetch fails for one model | Logged to `data/raw/failed.jsonl`, run continues |
| Crash during ingestion | Atomic writes + per-file cache: resume continues where it stopped |
| Metadata field missing | `unknown` state, ⚠️ in the table, ranked below full passes |

## 9. Configuration

Everything tunable is in [`config.yaml`](../config.yaml): embedding model and dimension,
chunk token limit, corpus tasks and Indic languages, Pinecone index/namespace,
retrieval `k` and top-N, reranker choice, size-word thresholds, cleaning thresholds,
memory-estimate constants, loop caps. Secrets live only in `.env` (see
[development.md](development.md)).

## 10. Extension points

| To add… | Change |
|---|---|
| A license | `normalize.LICENSE_RIGHTS` + a case in `tests/test_normalize.py` |
| A multilingual model | `normalize.MULTILINGUAL_MODELS`, after checking its card's language list |
| A size word | `config.yaml: size_words_mb` (the extraction prompt lists the keys automatically) |
| A task | `config.yaml: corpus.tasks`, `guide.TASK_LABELS/TASK_OPTIONS/TASK_GUIDES`, `try_it_snippet` template, `llm` tests. **Scope is frozen (D5)**: discuss first |
| An LLM provider | A `_call_<name>(prompt, system, model)` in `llm.py` and an entry in `_PROVIDERS` |
| A constraint | Extraction key + `clean_constraints`, a `verify` check, a `build_filter` clause, a `guide` phrase, tests for all four |

## 11. Where the implementation deliberately differs from the decision docs

| Item | What we did | Why |
|---|---|---|
| `language_status` field | Added to the D10 schema | Pinecone can't filter on "list is empty" |
| `directions`, `text`, `section` fields | Added to metadata | D18 direction rule; explanation needs chunk text |
| `conditional` rights | Count as ⚠️ unknown, not ✅ | A human must read the terms |
| Size unit | 1 MB = 1,000,000 bytes | Matches the Hub's displayed sizes |
| "Main weight files" (D20) | Top-level files named `model*` / `pytorch_model*` | Nested folders hold alternative copies; other names become *unknown* (honest, but measure how many) |
| `viable` | `overall ≠ fail` | See §6.4 |
| Models | Pinned in `config.yaml` (`llm.*`); env vars only override | One place to change, reproducible runs |
| Reranker default | Local `bge-reranker-v2-m3` | Safe default until the Pinecone plan check (D9) |
| Copyleft rights | GPL / CC-BY-SA: `conditional` for both rights | Share-alike applies to derivatives |
| Direction | Passes only from an `opus-mt-<src>-<tgt>` name, labelled as such | Deterministic and covers a large family; everything else ⚠️ |
| `base_model` ids | Canonicalised through the Hub API at ingestion | Merge legacy/current ids; assumption to verify on one model |
| Multilingual map | Each entry cites a source and has a `checked` flag | Owned by the data lead; verification feeds on it |
| Demo | Replay of recorded runs, not "offline" | Retrieval needs the network |
| Loop closing | Via UI re-invocation, not a graph edge back to `extract`/`retrieve` | Keeps the graph stateless; same behaviour, testable caps |
