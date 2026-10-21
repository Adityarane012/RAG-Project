# Implementation plan (phase-wise)

Status as of **2026-10-21 (day 6 of 14)**. This replaces the earlier work-package plan. It covers
everything left to take the project from "offline core, tested" to "recorded demo, evaluated,
written up", with owners, hours, gates, budgets, risks and fallbacks.

Companion docs: [PROJECT.md](PROJECT.md) (what), [decisions.md](decisions.md) (why),
[architecture.md](architecture.md) (how), [testing-strategy.md](testing-strategy.md) (edge cases,
cited here as `E-...`), [evaluation-plan.md](evaluation-plan.md), [data-pipeline.md](data-pipeline.md),
[demo-runbook.md](demo-runbook.md), [development.md](development.md).

## 0. Assumptions (change these and the plan changes)

| # | Assumption | If wrong |
|---|---|---|
| 1 | Day 1 was 16 Oct, so day 14 is **29 Oct** ("16 Oct + 14 days" is 30 Oct, giving a day of slack; confirm which the course means) | Shift every date |
| 2 | Capacity is 6 h/day per person; **today (21 Oct) counts as 3 h**. Total: 153 h across three people | Re-run the capacity table in section 5 |
| 3 | The AI assistant drafts code and tests; the hours here are for a human to review, run live, debug and decide. Code that needs live services (Hub, Pinecone, Groq, Ollama) can only be *run* by the team or after the cloud environment's network allowlist is changed | Hours for coding tasks roughly double |
| 4 | Free tiers only: Groq (`gpt-oss-20b`: 30 requests/min, 8,000 tokens/min, 200,000 tokens/day), Pinecone Starter (1M read units and 2M write units per month), Hub free quotas. Figures are from the docs and third-party summaries, not yet confirmed against your accounts (task 1.9, 1.10) | Re-budget in section 6 |
| 5 | Roles: **A** Data, **B** Pipeline, **C** Evaluation and UI. C writes the evaluation queries and must not build retrieval (D11). Names are still to be filled in | Re-assign tasks, keep the independence rule |
| 6 | The report's format is deferred. Write-up tasks (8.1 to 8.3) produce content, not a formatted report | Add formatting time |

## 1. Where we are: Phase 0 is complete

**Built and unit-tested offline (157 tests, no network).** Licence/rights map, D20 size rule, language and
direction normalisation, multilingual-map seed, `verify`, Pinecone filters, chunk-to-model grouping,
cleaning and chunking, vector building, guidance layer, build-on estimates, prompt-injection delimiters,
the LangGraph pipeline (stub dependencies), eval metrics, resumable ingest, snapshot builder and
quality report, local reranker (fake scorer), record/replay, LLM cache, token throttle and retry
handling, budgeted explanation evidence (4 passages per model), Streamlit renderer, `.env` setup and
checker. All decisions D1 to D24 are Accepted; the keys are in `.env`.

**Not proven against anything real.** Every item here is an assumption until Phase 1 checks it:

| Assumption in the code | Checked by |
|---|---|
| The Hub response has `siblings[].size`, `safetensors.total`, `cardData.*` as `normalize_record` expects | 1.5 |
| The Hub API returns the *current* id for a legacy id (`xlm-roberta-base`) | 1.5 |
| Pinecone `$or` with a missing field, `$in` on a list field and `$and` of `$or`s behave as D12 assumes | 1.9 |
| `gpt-oss-20b` accepts `response_format=json_object`; Groq 429s carry `retry-after`; the 8K/200K limits match your account | 1.10 |
| The e5 tokenizer stays near our token estimate on Devanagari | 1.7 |
| `bge-reranker-v2-m3` loads and runs on a team laptop | 1.7 |

**Not built yet.** Index build (`index.main`), live graph wiring (`_live_graph`), baseline flags, the real
`run_eval.py`, the side-by-side and check-a-model UI, the poisoned-card script, the extraction test
set and runner, the query set, the demo recorder script, CI. Known gaps from the edge-case
catalogue are scheduled as tasks below.

## 2. Phases at a glance

| Phase | Dates | Goal | Lead | Gate at exit |
|---|---|---|---|---|
| 1 Unblock and verify | Oct 21 to Oct 22 | Turn assumptions into observed facts | B, A | **G0** live access |
| 2 Data | Oct 22 to Oct 24 | Raw cache to checksummed snapshot, maps extended | A | **G2** snapshot cut |
| 3 Evaluation assets | Oct 21 to Oct 24 | Query set written before tuning | C | **G1** queries committed |
| 4 Index and live pipeline | Oct 22 to Oct 25 | Index built, graph live, UI features | A, B, C | **G3** `prod` live |
| 5 Baselines and harness | Oct 24 to Oct 26 | Four systems, one command | B, C | all four systems return top-5 |
| 6 Evaluation | Oct 26 to Oct 29 | Results, labels, faithfulness, ablation | C, A, B | **G4** outputs frozen (before labelling) |
| 7 Hardening and freeze | Oct 26 to Oct 29 | Recorded demo, reproducibility, tag | B | **G5** code freeze |
| 8 Write-up and rehearsal | Oct 28 to Oct 29 | Content and two rehearsals | all | **G6** rehearsed |

```
1 verify ──► 2 data ──► 4 index ──► 5 baselines ──► 6 evaluate ──► 7 freeze ──► 8 rehearse
   │            │          ▲  ▲                          ▲
   │            └──► 3 queries (C, parallel, G1 before any tuning)
   └─ G0 ── needs the network (or laptops)
```

The critical path is **1.9 and 1.10, then 2.1 to 2.4, then 4.4 to 4.9, then 6.1 to 6.4**. A slip on
that chain moves the demo; a slip elsewhere usually does not.

## 3. Gates and working rules

| Gate | When | What must be true | If it is missed |
|---|---|---|---|
| **G0** | Oct 22 noon | `check_env` live-ready and a live call to each service works from a machine we can run on | Run live steps on laptops; the cloud session only drafts code |
| **G1** | Oct 23 | `eval/queries.jsonl` committed and valid, before any retrieval or prompt experiment (git history is the evidence) | Nobody tunes anything until it is |
| **G2** | Oct 23 | Raw cache complete except logged failures (<= 2% of candidates, proposed); snapshot built; quality report in `data-notes.md` | By Oct 24 noon continue with a partial corpus (all Indic-tagged plus the top-N fetched per task) and document the coverage |
| **G3** | Oct 25 | `prod` populated, counts equal the experiment build, one filtered query per constraint type correct | See cut ladder (section 8) |
| **G4** | Oct 27 | Evaluation outputs frozen (results v2 committed) **before any labelling** | Freeze anyway; list unfixed failures as limitations |
| **G5** | Oct 28 | Demo recorded against `prod`; tag `v1.0-demo` | Any later change to index or config means re-recording |
| **G6** | Oct 29 | Two rehearsals done (live, and `REPLAY=1` with Wi-Fi off) | Rehearse the replay path first |

**Tuning policy (protects the evaluation).**
- *Before G1:* no experiment may look at results on evaluation queries.
- *G1 to G4:* allowed changes are (a) the extraction prompt, judged **only** on the separate 20-query
  extraction set, (b) the documented ablation (chunking, reranker on/off, `k`), (c) bug fixes found in
  failure analysis. Every evaluation query used to debug is recorded as "seen" for the write-up.
- *After G4:* no change to retrieval, ranking, prompts, models or config values. Labels depend on
  frozen outputs; a change would invalidate them.
- *After recording (7.1):* any change to the index or config requires re-recording.

**Engineering rules.** Feature branch plus PR for everything; every PR gets one review from a
different member; `pytest` green; docs updated in the same PR; no secrets in git. Changes to
`verify.py`, `normalize.py` or the licence map need A and B to look at them (silent errors there
corrupt every metric, D21). Tags: `v0.1-data` (after 2.8), `v0.2-index` (after 4.9),
`v0.3-eval` (after 6.4), `v1.0-demo` (after 7.7).

## 4. Phases in detail

### Phase 1: Unblock and verify assumptions (Oct 21 to Oct 22; 14 h)

**Objective.** Replace documentation-based assumptions with observed behaviour, and make the
decisions that depend on them, before building on them.

**Entry.** Keys are in `.env`; `pytest` is green; D2, D3 and D8 to D11 are Accepted (done).

| ID | Task | Owner | Day | Hours | Needs | Done when |
|---|---|---|---|---|---|---|
| 1.2 | Machine setup: venv, `pip install -r requirements.txt`, own `.env` (Groq + HF keys) | A | Oct 21 | 0.5 | - | `pytest` green; `check_env` green |
| 1.1 | Live access: allow `api.groq.com`, `huggingface.co`, `api.pinecone.io` in the cloud environment, or run live steps on laptops; Ollama installed, `qwen2.5:7b-instruct` pulled | B | Oct 21 | 1 | - | `python -m src.check_env` is live-ready on B's machine; `ollama run` answers |
| 1.8 | Write the 20-query extraction test set with gold constraints (`eval/extraction_test.jsonl`) | B | Oct 21 | 1.5 | - | 20 labelled queries covering every category in testing-strategy section 6 |
| 1.3 | Machine setup (same as 1.2) | C | Oct 21 | 0.5 | - | `pytest` green; `check_env` green |
| 1.11 | NLLB-200 license on its card; open the five `TASK_GUIDES` URLs | C | Oct 21 | 0.5 | - | Demo query 2 premise confirmed; broken links fixed |
| 1.4 | Model counts: `python -m src.ingest counts` | A | Oct 22 | 0.5 | 1.2 | Per-task and total counts in `data-notes.md`; compared with the ~5-8k estimate |
| 1.5 | Hub fixtures: save live responses for 5 varied models (ASR, translation, gated, no card, multilingual) plus 3 `opus-mt-*`; add fixture-based tests of `normalize_record`; check the canonical id of `xlm-roberta-base` | A | Oct 22 | 1.5 | 1.2 | Fixtures in `tests/fixtures/`; field names confirmed or `normalize_record` fixed; canonical-id assumption confirmed or replaced |
| 1.6 | Bulk-listing experiment: `list_models(expand=[...])` for 20 models; are `siblings` sizes present? does `safetensors` give a size within 1% of the blobs rule? | A | Oct 22 | 1 | 1.5 | Decision recorded: keep per-model fetch, or switch part of ingestion to bulk listing |
| 1.7 | Embedding throughput (200 real cards, CPU and Colab GPU) and the real e5 tokenizer on 50 Indic cards vs `approx_tokens`; load the real `bge-reranker-v2-m3` | A | Oct 22 | 1.5 | 1.2 | Chunks/s known -> decision where the index is built; token estimate adjusted if sections exceed ~507; reranker returns finite scores |
| 1.9 | Pinecone: create the index (dim 1024, cosine, serverless), run the 10-vector semantics test (E-RET-9..12), read the plan limits, measure write units on 100 real-shaped vectors | B | Oct 22 | 2.5 | 1.1 | Filters behave as D12 assumes (or the filter code is fixed); hosted-rerank availability known; write units per vector measured |
| 1.10 | Run the D7 extraction test on `gpt-oss-20b`, the fallback model and Ollama; confirm JSON mode and the retry-after header | B | Oct 22 | 2.5 | 1.1, 1.8 | Parse rate and per-field accuracy per provider in `data-notes.md`; final model per role decided |
| 1.12 | Inventory the Hub's own filters (task, language, license, size?) | C | Oct 22 | 0.5 | - | Filter list recorded; defines what the HF baseline can and cannot do |

**Exit criteria (G0).** Every row of `data-notes.md` "Live checks" is filled with a date, a result and
the command used. Decisions recorded: final Groq and Ollama models and which role each plays (D7);
reranker (D9: local unless hosted proves available and better); corpus size; per-model fetch
versus bulk listing; index built on CPU or Colab.

**Risks and fallbacks.**
- *Network blocked in the cloud environment.* Add the three hosts to its allowlist, or run every live
  task on laptops (G0 fallback). The checks themselves are small scripts either way.
- *`$or` or `$in` behave differently on Pinecone.* Retrieval filters become coarser (task only) and
  `verify` stays the authority (it already is), at the cost of recall and more `k` widening; log the
  recall cost.
- *Canonical-id assumption false.* Drop `canonicalize`; accept split lineage counts or keep a
  small alias map for the few most common bases.
- *`gpt-oss-20b` rejects JSON mode.* Use `llama-3.1-8b-instant` for extraction and keep `gpt-oss`
  for explanations, or tolerant JSON extraction.
- *An 8 GB laptop cannot run `qwen2.5:7b-instruct`.* Use `qwen2.5:3b` (D7).

**Edge cases closed here.** E-RET-9..12, E-NORM-16, E-IDX-4, E-IDX-13, E-LLM-7, 8, 13, 21, E-RER-2.

### Phase 2: Data (Oct 22 to Oct 24; 10 h)

**Objective.** A complete raw cache and a checksummed snapshot, with the licence, language,
multilingual and size rules corrected by what the data actually contains.

**Entry.** 1.4 (counts) and 1.5 (fixtures) done.

| ID | Task | Owner | Day | Hours | Needs | Done when |
|---|---|---|---|---|---|---|
| 2.1 | Launch `python -m src.ingest fetch` (overnight-safe, resumable) | A | Oct 22 | 1 | 1.4, 1.5 | Fetch running; progress visible |
| 2.2 | Monitor and resume the fetch; read `failed.jsonl` | A | Oct 23 | 0.5 | 2.1 | Raw cache complete except logged failures |
| 2.3 | Triage failures; retry or drop with a reason | A | Oct 23 | 1 | 2.2 | Failures <= 2% of candidates (proposed threshold), each with a reason |
| 2.4 | Cut the snapshot and the data-quality report; fill `data-notes.md` | A | Oct 23 | 1.5 | 2.3 | `records.jsonl.gz` built; report written; gate G2 decided |
| 2.5 | Size-rule decision from the by-reason counts; widen the weight-name rule if `weights_with_other_name` is large; update tests | A | Oct 23 | 1 | 2.4 | Rule documented in data-pipeline 4.1; tests updated |
| 2.6 | Extend the license map and language aliases from the histograms | A | Oct 23 | 2 | 2.4 | Top unmapped licenses and non-2-letter tokens handled; tests added |
| 2.7 | Multilingual map to ~20 entries, each with a cited source | A | Oct 24 | 2.5 | 2.4 | Entries added with `source`; `checked` set only after comparing the list |
| 2.8 | GitHub Release with the snapshot; `snapshot_date`, `snapshot_sha256`, `snapshot_url` in `config.yaml`; B and C load it | A | Oct 24 | 0.5 | 2.4 | `load_snapshot(path, sha)` works on all three machines |

**Exit criteria (G2).** Cache complete except logged failures; `snapshot_date`, `snapshot_sha256`
and `snapshot_url` in `config.yaml`; all three machines load the snapshot with the checksum; the
quality report answers: unknown-size share and reasons, unmapped licences, unknown-language share,
`base_model` and `param_count` coverage, minimal-documentation share, models per task. **Decisions
from the report:** drop lineage from the demo if `base_model` coverage is low; widen the size-rule
name pattern if `weights_with_other_name` is large.

**Risks and fallbacks.**
- *Fetch slower than hoped.* The free quota is roughly 1,000 API calls per 5 minutes (assumption), so
  ~6k models need at least ~30 minutes of API calls; start it early (2.1 on Oct 22) and let it run
  overnight. If incomplete at the G2 deadline, use the partial-corpus rule.
- *Disk.* The raw cache is large; keep it local and out of git (estimate unmeasured).
- *High unknown rates.* That is a finding, not a failure: ⚠️ is designed for it. Only act if the
  size rule is clearly too narrow.

**Edge cases closed here.** E-NORM-1..18, E-ING-3, 8, 9, E-SNP-5.

### Phase 3: Evaluation assets (Oct 21 to Oct 24; 11 h)

**Objective.** The query set exists, committed, written blind, before anyone tunes.

**Entry.** None (runs in parallel from today).

| ID | Task | Owner | Day | Hours | Needs | Done when |
|---|---|---|---|---|---|---|
| 3.1 | Write queries, batch 1 (normal, spread over the 5 tasks and 6+ Indic languages) | C | Oct 21 | 1.5 | - | ~25 queries in `eval/queries.jsonl` format |
| 3.2 | Write queries, batch 2: rest of the normal set, ~15 vague, ~10 impossible drafts, some no-constraint and non-English | C | Oct 22 | 4.5 | 3.1 | ~100 queries written without looking at any system output |
| 3.3 | Ask classmates for ~20 queries (async) | C | Oct 22 | 0.5 | - | Requests sent |
| 3.4 | Merge classmate queries, validate with `load_queries`, commit (gate G1) | C | Oct 23 | 1.5 | 3.2, 3.3 | `eval/queries.jsonl` committed BEFORE any retrieval experiment |
| 3.5 | Spec the labelling sheets (relevance 0/1/2 on the union of top-5 across systems, blind; faithfulness claim sheet) | C | Oct 23 | 1.5 | - | Sheet formats and instructions in `eval/labels/README.md` |
| 3.6 | Check the impossible queries with `verifiably_impossible` against the snapshot; rewrite any that are not | C | Oct 24 | 1.5 | 2.4, 3.4 | Every impossible query has a known failure for every model (a changed query is logged) |

**Exit criteria (G1).** `eval/queries.jsonl` has about 120 valid records (about 75 normal, 15 vague,
10 impossible, 20 from classmates, plus some no-constraint and Hindi/Marathi queries); committed
before any retrieval experiment; every impossible query passes `verifiably_impossible` against the
snapshot (rewritten and logged otherwise).

**Risks and fallbacks.**
- *Classmates are slow.* Commit with the teammate's ~100 and add the classmate batch as a
  separate commit, labelled as such in the write-up.
- *Author bias.* The author must not look at any system output while writing (D11).
- *C is the most loaded person (see section 5).* If queries slip, A writes the vague batch.

**Edge cases closed here.** E-MET-3 (queries whose constraints parse to nothing are counted and
reported separately).

### Phase 4: Index and live pipeline (Oct 22 to Oct 25; 25 h)

**Objective.** A built index, a live graph, and the UI features the demo needs.

**Entry.** 1.9 (Pinecone semantics, write units), 1.7 (embedding speed), 2.4 (snapshot).

| ID | Task | Owner | Day | Hours | Needs | Done when |
|---|---|---|---|---|---|---|
| 4.1 | Skeleton of `_live_graph()`: embedder via `st.cache_resource`, Pinecone client, `pinecone_fetch` | B | Oct 22 | 1 | 1.9 | Compiles and runs against the 10-vector test index |
| 4.2 | Wire `_live_graph()` fully: query embedding, real reranker, lineage index from the snapshot, `llm.explain`, error paths | B | Oct 23 | 4 | 4.1, 2.4 | One query runs end to end on the test index |
| 4.3 | Fix known gaps: validate overrides through `clean_constraints` (E-GRAPH-12); no-constraint query -> clarify (E-GRAPH-11); E-VER-8/11; E-RET-5/7 | B | Oct 23 | 2 | - | Tests added for each; `pytest` green |
| 4.11 | UI: editable parsed intent (writes `overrides`), tooltips wired in | C | Oct 23 | 3 | - | AppTest covers edit -> rerun (E-APP-5/6) |
| 4.4 | `index.main()` + `ensure_index()`: batching, progress, resumable, writes to `exp-<name>`; start the build | A | Oct 24 | 3 | 1.7, 1.9, 2.4 | Build running into `exp-A` |
| 4.7 | Real reranker and explain path under the token budget; confirm `llm.tpm` against the Groq console | B | Oct 24 | 3 | 4.2 | A full query (extract + retrieve + rerank + verify + explain) stays under 8,000 tokens per minute |
| 4.5 | Index spot checks: vector count = chunk count, identical metadata per model, one filtered query per constraint type; E-IDX-3/5/6/10/11 tests | A | Oct 25 | 2 | 4.4 | Checks pass; failures fixed and the namespace rebuilt |
| 4.6 | Cleaning edge cases (unclosed fence E-CLN-2, unterminated front matter, comments/details) | A | Oct 25 | 1 | - | Tests added; index rebuilt if cleaning changed |
| 4.9 | Run the `prod` build with B; verify counts match `exp-A` | A | Oct 25 | 1 | 4.8 | Counts equal |
| 4.12 | UI: check-a-model tab (snapshot lookup, `adapt.model_report`) | A | Oct 25 | 2 | 2.8 | Pasting a snapshot id shows the rights table; unknown id gives a clear message |
| 4.8 | Promote: fresh `prod` namespace from the final build code (gate G3) | B | Oct 25 | 1 | 4.5 | `prod` populated; `config.yaml: pinecone.namespace: prod` |
| 4.10 | Poisoned-card test: 3 synthetic cards in `exp-poison`, script + assertions, 5 repeats each | B | Oct 25 | 2 | 4.2 | Table identical to metadata-derived; injected claims counted; result in `data-notes.md` |

**Exit criteria (G3).** `prod` namespace populated with a count equal to the experiment build;
spot checks pass; a full query stays under 8,000 tokens per minute (extraction plus explanation);
the poisoned-card test passes (table identical to the metadata-derived one in every repeat; injected
claims counted and reported, not hidden); overrides are validated; the UI has editable intent,
tooltips and a working check-a-model tab.

**Risks and fallbacks.**
- *Build too slow on CPU.* Use a Colab GPU for the embedding step (decision from 1.7); only the
  upsert needs the Pinecone key.
- *Write-unit budget.* Measured per vector in 1.9; builds planned: `exp-A`, `prod`, `exp-fixed`,
  `exp-poison` and one spare (section 6). Build into a **fresh** namespace each time (orphan chunks).
- *Poor Indic retrieval.* Check with the multilingual-map models and a few Indic queries *on the
  extraction set's queries, not the evaluation set*; the fallback chunk helps minimal cards.
- *Reranker latency or memory on a laptop.* Measure in 1.7; fallback is reranker off (still
  verified), documented as a variant.
- *Streamlit state bugs.* E-APP-4 to 7 tests (task 7.8).

**Edge cases closed here.** E-IDX-1..13, E-CLN-1..8, E-GRAPH-11..13, E-VER-8, 11, E-RET-5, 7, E-APP-4..7.

### Phase 5: Baselines and harness (Oct 24 to Oct 26; 15.5 h)

**Objective.** Four systems return top-5 for any query, and one command produces the table.

**Entry.** 4.2 (live graph); 3.4 (queries committed).

| ID | Task | Owner | Day | Hours | Needs | Done when |
|---|---|---|---|---|---|---|
| 5.1 | Naive-RAG flag: no filters, no verification, same index/embeddings/reranker/LLM | B | Oct 24 | 1 | 4.2 | `variant=naive` returns top-5 for a query |
| 5.3 | `eval/run_eval.py` skeleton: loop queries x systems, re-verify top-5, metrics, latency, count of no-constraint queries (E-MET-3) | C | Oct 24 | 2.5 | 3.4 | Runs on 5 queries with stub systems |
| 5.2 | Keyword + filters flag: BM25 over cleaned card text (`rank_bm25`) with the same filters | B | Oct 25 | 2 | 2.4 | `variant=keyword` returns top-5; tests with a toy corpus |
| 5.4 | UI: side-by-side naive vs ours (`st.columns`) | C | Oct 25 | 3 | 5.1 | Both columns render for one query; replay mode supports it |
| 5.5 | HF Hub baseline: script the Hub's own filters via `HfApi.list_models` for every query, save to `eval/baselines/`; spot-check 5 queries in the website | C | Oct 25 | 2.5 | 1.12, 3.4 | Results file saved once and committed (changed from 'by hand'; see section 9) |
| 5.6 | Run extraction for all queries once (cached); review silent drops. Do NOT change prompts on the evaluation queries (only on the 20-query extraction set) | B | Oct 26 | 1.5 | 3.4, 1.10 | Silent-drop rate measured; prompt changes, if any, justified from the extraction set |
| 5.7 | `run_eval.py` complete: four systems, results markdown, config hash + git commit, labelling-sheet and faithfulness-sample exports | C | Oct 26 | 3 | 5.3 | One command regenerates the table |

**Exit criteria.** `variant=naive` and `variant=keyword` run through the same harness as ours; the HF
Hub results are saved once; `run_eval.py` runs end to end on a handful of queries and records the
config hash, git commit, provider and reranker; extraction for all queries is cached.

**Risks and fallbacks.**
- *Unfair baselines.* Naive RAG differs from ours by exactly two switches (no filters, no
  verification); the keyword baseline uses the same filters. Anything else that differs is a bug.
- *Contamination.* 5.6 may reveal silent drops on evaluation queries. Fix the *prompt* only against
  the extraction set; otherwise report the drop rate as a limitation (E-MET-3).
- *Hub baseline.* See section 9 (scripted via the Hub API with 5 manual spot-checks).

**Edge cases closed here.** E-MET-3, E-GRAPH-14 (real reranker).

### Phase 6: Evaluation (Oct 26 to Oct 29; 27 h)

**Objective.** Numbers for the four systems, labelled relevance with an agreement figure,
faithfulness of the explanations, the one number-backed tuning choice, and a results table.

**Entry.** G3 passed, all four systems running, queries committed (G1).

| ID | Task | Owner | Day | Hours | Needs | Done when |
|---|---|---|---|---|---|---|
| 6.2 | Fixed-size chunking option in `index.py` (config flag) for the ablation, and its build into `exp-fixed` | A | Oct 26 | 1.5 | 4.4 | Second namespace built |
| 6.6 | 'Try it' smoke test on ~20 small models (script runs each snippet in a clean env) | B | Oct 26 | 2 | 4.8 | Pass/fail per model recorded |
| 6.1 | Run all four systems (explanations off) -> results v1; export failure list for B | C | Oct 26 | 1.5 | 5.7, 5.5, 5.6, 4.8 | Table v1 committed; failures listed |
| 6.8 | Relevance labelling (A), same 40 queries, blind | A | Oct 27 | 3.5 | 6.4 | Sheet complete; kappa computable |
| 6.9 | Ablation labelling (A) | A | Oct 27 | 1.5 | 6.5 | Sheet complete |
| 6.3 | Failure-case fixes from results v1 (every query used for debugging is listed as 'seen'). If not done by noon: freeze anyway and list the rest as limitations | B | Oct 27 | 3 | 6.1 | Fixes merged |
| 6.11 | Generate explanations for the 30 faithfulness answers, day 1 (15 answers, ~100K tokens) | B | Oct 27 | 1 | 6.4 | 15 generated |
| 6.4 | Re-run all four systems -> results v2; export the blind labelling sheets (gate G4: outputs frozen) | C | Oct 27 | 1 | 6.3 | Results v2 committed. After this, no change to retrieval, ranking or prompts |
| 6.5 | Ablation run: section chunking vs fixed-size on 25 queries; export its sheet | C | Oct 27 | 0.5 | 6.2, 6.4 | Ablation outputs exported |
| 6.7 | Relevance labelling (C), 40 queries, blind | C | Oct 27 | 3.5 | 6.4 | Sheet complete |
| 6.13 | Faithfulness hand-scoring, first 15 answers (claim by claim) | A | Oct 28 | 1.5 | 6.11 | Counts recorded |
| 6.12 | Explanations day 2 (the other 15) | B | Oct 28 | 1 | 6.11 | 30 generated |
| 6.10 | Ablation labelling (C) | C | Oct 28 | 1.5 | 6.5 | Sheet complete |
| 6.15 | Results table, Cohen's kappa, slices (task, Indic vs not), threats to validity | C | Oct 28 | 2.5 | 6.7, 6.8, 6.10 | `eval/results/<date>.md` committed |
| 6.14 | Faithfulness hand-scoring, last 15 answers | A | Oct 29 | 1 | 6.12 | Share supported + list of unsupported claims |
| 6.16 | Add the faithfulness numbers to the results table | C | Oct 29 | 0.5 | 6.14, 6.15 | Final table committed |

**Exit criteria.** `eval/results/<date>.md` committed with violation, unknown, relevance,
abstention, clarification, `modifiable` correctness, faithfulness, "Try it" pass rate and latency for
all four systems; Cohen's kappa reported (weighted and unweighted); slices by task and Indic vs
non-Indic; threats to validity; the chunking ablation (or the reranker on/off fallback).

**Why G4 sits before labelling.** Labels are judgements on specific outputs. If anything changes
ranking after labelling starts, those labels are stale. So failures are fixed on Oct 27 morning,
results v2 is frozen, and only then do A and C label.

**Workload check (the earlier "~250 judgements" covered one system).** Four systems share
many results; taking the union of each query's top-5 gives about 10 unique (query, model) pairs per
query. 40 queries is about 400 judgements per labeller, planned at 3.5 h each (about 25 s per
judgement plus reading and breaks). 50 queries would be about 5 h each, which this calendar cannot
absorb. Default: 40 (section 9).

**Risks and fallbacks.**
- *Token budget.* Explanations for 30 answers cost about 200K tokens (one full day on
  `gpt-oss-20b`); they are split over Oct 27 and 28 (6.11, 6.12). Use Ollama for the second half
  if the limit bites.
- *Labellers disagree.* Report the pre-resolution kappa; resolve by discussion afterwards.
- *Failures too many to fix by noon on Oct 27.* Freeze anyway (G4 fallback).
- *No time for the second index.* Use reranker on/off as the ablation (same index, no rebuild).

**Edge cases closed here.** E-LLM-7 (hostile query), E-APP-*, E-EVD-11 on real text.

### Phase 7: Hardening, recording and freeze (Oct 26 to Oct 29; 12.5 h)

**Objective.** A demo that survives bad Wi-Fi and a rate limit, a result that reproduces, and a
frozen tagged codebase.

**Entry.** G4 passed.

| ID | Task | Owner | Day | Hours | Needs | Done when |
|---|---|---|---|---|---|---|
| 7.5 | Pin `requirements.txt` versions; add a GitHub Actions workflow that runs `pytest` | A | Oct 26 | 1.5 | - | CI green on a PR |
| 7.6 | Docs sync pass; fill `data-notes.md` | A | Oct 26 | 1 | - | Architecture section 11 deviations list reviewed |
| 7.2 | Ollama switch rehearsal end to end (extraction + explanations) | B | Oct 26 | 1 | 1.10 | Switch works on a laptop; quality noted |
| 7.8 | UI tests for E-APP-4..7 (fresh search resets counters, answering a question, editing mid-loop, explain error) | C | Oct 26 | 1.5 | 4.11 | Tests green |
| 7.4 | Reproducibility run from a clean clone: snapshot load, `run_eval.py` regenerates the table | A | Oct 28 | 2 | 6.15 | Same table (within LLM-cache determinism) |
| 7.1 | Scripted demo recorder (`scripts/record_demo.py`): every planned query plus follow-ups through `ReplayGraph` in record mode, against `prod` | B | Oct 28 | 3 | 4.8, 6.4 | `demo/cache/` committed; replay shows all planned queries |
| 7.7 | Code freeze and tag `v1.0-demo` (gate G5) | B | Oct 28 | 0.5 | 7.1 | Tag pushed; no feature changes after |
| 7.3 | Replay check with Wi-Fi off; screenshots of a good run; final UI polish | C | Oct 29 | 2 | 7.1 | All demo queries replay; screenshots saved |

**Exit criteria (G5).** `demo/cache/` holds every planned query and its follow-ups (clarify answer,
relax accept), recorded against the final `prod`; `REPLAY=1` with Wi-Fi off shows them all; a clean
clone reproduces the results table from snapshot, `config.yaml` and one command; CI is green;
`v1.0-demo` is tagged.

**Risks and fallbacks.**
- *Stale recordings.* Any index or config change after 7.1 means re-recording (E-RPL-6); the freeze
  tag is what prevents it.
- *Groq limit during recording.* Recording uses about 70K tokens (10 queries at ~6.6K); do it on a
  day without evaluation explanations, or use a teammate's key.
- *Reproducibility differs.* Differences must be explained by the LLM cache; if not, it is a bug.

### Phase 8: Write-up and rehearsal (Oct 28 to Oct 29; 9 h)

**Objective.** Content ready for the report (format to be confirmed later) and a team that can run
and defend the demo.

| ID | Task | Owner | Day | Hours | Needs | Done when |
|---|---|---|---|---|---|---|
| 8.2 | Write-up: architecture and design choices | B | Oct 28 | 1.5 | - | Draft sections ready |
| 8.1 | Write-up: results and limitations (format to be confirmed later) | C | Oct 28 | 1.5 | 6.15 | Draft sections ready |
| 8.3 | Write-up: data pipeline and evaluation method | A | Oct 29 | 1.5 | - | Draft sections ready |
| 8.5 | Rehearsal and viva Q&A run-through (everyone defends D2) | A | Oct 29 | 1.5 | - | Each member answers the 11 viva questions |
| 8.4 | Rehearsal 1 (live) and rehearsal 2 (`REPLAY=1`, Wi-Fi off) | B | Oct 29 | 1.5 | 7.1 | Both run clean; the right-hand column of the demo script is filled |
| 8.6 | Rehearsal and viva Q&A run-through | C | Oct 29 | 1.5 | - | Same |

**Exit criteria (G6).** Two rehearsals run clean (live; `REPLAY=1` with Wi-Fi off); the "Observed in
rehearsal" column of the demo script is filled; each member answers the 11 viva questions in
PROJECT.md section 10 without notes, and can defend D2.

**Risks and fallbacks.** Rehearse the replay path first; if live search misbehaves, say so and use
the recording (it must be described as a recording).

## 5. Capacity and calendar

Planned **124 h of 153 h** (81%), leaving about 29 h (about 19%) of
buffer for review, debugging and the unexpected. C is the most loaded; if anything slips, move
UI items (4.12 already sits with A) to A, who has slack on Oct 26 and 28.

| Person | Oct 21 | Oct 22 | Oct 23 | Oct 24 | Oct 25 | Oct 26 | Oct 27 | Oct 28 | Oct 29 | Total |
|---|---|---|---|---|---|---|---|---|---|---|
| A | 0.5 | 5.5 | 6 | 6 | 6 | 4 | 5 | 3.5 | 4 | 40.5 |
| B | 2.5 | 6 | 6 | 4 | 5 | 4.5 | 4 | 6 | 1.5 | 39.5 |
| C | 2.5 | 5.5 | 6 | 4 | 5.5 | 6 | 5 | 5.5 | 4 | 44 |
| capacity | 3 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 51 each |

### Day by day

**Oct 21 (D6)**
- **A** (0.5 h): 1.2 Machine setup: venv, `pip install -r requirements.txt`, own `.env`... (0.5)
- **B** (2.5 h): 1.1 Live access: allow `api.groq.com`, `huggingface.co`, `api.pinecone.io`... (1); 1.8 Write the 20-query extraction test set with gold constraints... (1.5)
- **C** (2.5 h): 1.3 Machine setup (same as 1.2) (0.5); 1.11 NLLB-200 license on its card; open the five `TASK_GUIDES` URLs (0.5); 3.1 Write queries, batch 1 (normal, spread over the 5 tasks and 6+ Indic... (1.5)

**Oct 22 (D7)**
- **A** (5.5 h): 1.4 Model counts: `python -m src.ingest counts` (0.5); 1.5 Hub fixtures: save live responses for 5 varied models (ASR... (1.5); 1.6 Bulk-listing experiment: `list_models(expand=[...])` for 20 models; are... (1); 1.7 Embedding throughput (200 real cards, CPU and Colab GPU) and the real... (1.5); 2.1 Launch `python -m src.ingest fetch` (overnight-safe, resumable) (1)
- **B** (6 h): 1.9 Pinecone: create the index (dim 1024, cosine, serverless), run the... (2.5); 1.10 Run the D7 extraction test on `gpt-oss-20b`, the fallback model and... (2.5); 4.1 Skeleton of `_live_graph()`: embedder via `st.cache_resource`, Pinecone... (1)
- **C** (5.5 h): 1.12 Inventory the Hub's own filters (task, language, license, size?) (0.5); 3.2 Write queries, batch 2: rest of the normal set, ~15 vague, ~10... (4.5); 3.3 Ask classmates for ~20 queries (async) (0.5)

**Oct 23 (D8)**
- **A** (6 h): 2.2 Monitor and resume the fetch; read `failed.jsonl` (0.5); 2.3 Triage failures; retry or drop with a reason (1); 2.4 Cut the snapshot and the data-quality report; fill `data-notes.md` (1.5); 2.5 Size-rule decision from the by-reason counts; widen the weight-name... (1); 2.6 Extend the license map and language aliases from the histograms (2)
- **B** (6 h): 4.2 Wire `_live_graph()` fully: query embedding, real reranker, lineage... (4); 4.3 Fix known gaps: validate overrides through `clean_constraints`... (2)
- **C** (6 h): 3.4 Merge classmate queries, validate with `load_queries`, commit (gate G1) (1.5); 3.5 Spec the labelling sheets (relevance 0/1/2 on the union of top-5 across... (1.5); 4.11 UI: editable parsed intent (writes `overrides`), tooltips wired in (3)

**Oct 24 (D9)**
- **A** (6 h): 2.7 Multilingual map to ~20 entries, each with a cited source (2.5); 2.8 GitHub Release with the snapshot; `snapshot_date`, `snapshot_sha256`... (0.5); 4.4 `index.main()` + `ensure_index()`: batching, progress, resumable... (3)
- **B** (4 h): 4.7 Real reranker and explain path under the token budget; confirm... (3); 5.1 Naive-RAG flag: no filters, no verification, same... (1)
- **C** (4 h): 3.6 Check the impossible queries with `verifiably_impossible` against the... (1.5); 5.3 `eval/run_eval.py` skeleton: loop queries x systems, re-verify top-5... (2.5)

**Oct 25 (D10)**
- **A** (6 h): 4.5 Index spot checks: vector count = chunk count, identical metadata per... (2); 4.6 Cleaning edge cases (unclosed fence E-CLN-2, unterminated front matter... (1); 4.9 Run the `prod` build with B; verify counts match `exp-A` (1); 4.12 UI: check-a-model tab (snapshot lookup, `adapt.model_report`) (2)
- **B** (5 h): 4.8 Promote: fresh `prod` namespace from the final build code (gate G3) (1); 4.10 Poisoned-card test: 3 synthetic cards in `exp-poison`, script +... (2); 5.2 Keyword + filters flag: BM25 over cleaned card text (`rank_bm25`) with... (2)
- **C** (5.5 h): 5.4 UI: side-by-side naive vs ours (`st.columns`) (3); 5.5 HF Hub baseline: script the Hub's own filters via `HfApi.list_models`... (2.5)

**Oct 26 (D11)**
- **A** (4 h): 6.2 Fixed-size chunking option in `index.py` (config flag) for the... (1.5); 7.5 Pin `requirements.txt` versions; add a GitHub Actions workflow that... (1.5); 7.6 Docs sync pass; fill `data-notes.md` (1)
- **B** (4.5 h): 5.6 Run extraction for all queries once (cached); review silent drops. Do... (1.5); 6.6 'Try it' smoke test on ~20 small models (script runs each snippet in a... (2); 7.2 Ollama switch rehearsal end to end (extraction + explanations) (1)
- **C** (6 h): 5.7 `run_eval.py` complete: four systems, results markdown, config hash +... (3); 6.1 Run all four systems (explanations off) -> results v1; export failure... (1.5); 7.8 UI tests for E-APP-4..7 (fresh search resets counters, answering a... (1.5)

**Oct 27 (D12)**
- **A** (5 h): 6.8 Relevance labelling (A), same 40 queries, blind (3.5); 6.9 Ablation labelling (A) (1.5)
- **B** (4 h): 6.3 Failure-case fixes from results v1 (every query used for debugging is... (3); 6.11 Generate explanations for the 30 faithfulness answers, day 1 (15... (1)
- **C** (5 h): 6.4 Re-run all four systems -> results v2; export the blind labelling... (1); 6.5 Ablation run: section chunking vs fixed-size on 25 queries; export its... (0.5); 6.7 Relevance labelling (C), 40 queries, blind (3.5)

**Oct 28 (D13)**
- **A** (3.5 h): 6.13 Faithfulness hand-scoring, first 15 answers (claim by claim) (1.5); 7.4 Reproducibility run from a clean clone: snapshot load, `run_eval.py`... (2)
- **B** (6 h): 6.12 Explanations day 2 (the other 15) (1); 7.1 Scripted demo recorder (`scripts/record_demo.py`): every planned query... (3); 7.7 Code freeze and tag `v1.0-demo` (gate G5) (0.5); 8.2 Write-up: architecture and design choices (1.5)
- **C** (5.5 h): 6.10 Ablation labelling (C) (1.5); 6.15 Results table, Cohen's kappa, slices (task, Indic vs not), threats to... (2.5); 8.1 Write-up: results and limitations (format to be confirmed later) (1.5)

**Oct 29 (D14)**
- **A** (4 h): 6.14 Faithfulness hand-scoring, last 15 answers (1); 8.3 Write-up: data pipeline and evaluation method (1.5); 8.5 Rehearsal and viva Q&A run-through (everyone defends D2) (1.5)
- **B** (1.5 h): 8.4 Rehearsal 1 (live) and rehearsal 2 (`REPLAY=1`, Wi-Fi off) (1.5)
- **C** (4 h): 6.16 Add the faithfulness numbers to the results table (0.5); 7.3 Replay check with Wi-Fi off; screenshots of a good run; final UI polish (2); 8.6 Rehearsal and viva Q&A run-through (1.5)

## 6. Budgets (estimates unless marked measured)

These numbers are what the plan is sized against. Tasks 1.9, 1.10 and 1.7 replace them with
measurements; update this section when they land.

| Resource | Limit | Planned use | Where it goes |
|---|---|---|---|
| Groq `gpt-oss-20b` tokens/day | 200,000 | Oct 22: D7 test about 40K; Oct 26: extraction for ~120 queries about 65K; Oct 27 and 28: 15 explanations each about 100K; Oct 28: demo recording about 70K | Each day stays under the limit with margin; the response cache means reruns are free |
| Groq tokens/minute | 8,000 | One query's two calls count about 7,300 (measured on the code, estimated tokens) | The throttle waits instead of failing |
| Pinecone write units | 2M/month | About 18-24k vectors per build x ~7 write units (to be measured in 1.9) is about 130-170K per build; 5 builds is about 0.65-0.85M | Fresh namespace per build; no overwriting |
| Pinecone read units | 1M/month | Evaluation: ~120 queries x 4 systems x a few fetches, well under 10K | Not a constraint |
| Hub API | ~1,000 calls / 5 min (assumed) | ~6k models x 2 requests | Start 2.1 on Oct 22, resumable |
| Embedding time | unmeasured | CPU: hours; Colab GPU: minutes (1.7 measures it) | Decides where 4.4 runs |
| Labelling | people-hours | 40 queries x ~10 unique pairs = ~400 judgements per labeller (about 3.5 h); ablation 25 queries (about 1.5 h) | A and C only |
| Explanations for faithfulness | ~200K tokens | 30 answers x ~6.6K | Two days, or Ollama |

## 7. Risk register

| # | Risk | Trigger / date | Impact | Mitigation | Owner |
|---|---|---|---|---|---|
| R1 | Network to Hub, Pinecone, Groq blocked in the cloud session | G0, Oct 22 noon | No live runs from the session | Allow the three hosts, or run on laptops | B |
| R2 | Query set contaminated | Anyone tunes before G1 | Evaluation not credible | Gate G1 and the tuning policy in section 3 | C |
| R3 | Ingestion incomplete | Oct 24 noon | Smaller corpus | Partial-corpus rule (G2) | A |
| R4 | Pinecone filter semantics differ | 1.9 | Lower recall | `verify` stays authoritative; widen `k` | B |
| R5 | Groq daily/minute limits hit | Any day | Failed or slow calls | Throttle, fallback model, Ollama, per-person keys, explanations only where needed | B |
| R6 | Pinecone write budget exhausted | Total builds > ~10 | Index frozen until next month | Measure in 1.9; fresh namespace per build, no re-runs "to see" | A |
| R7 | Poor Indic retrieval | Spot checks in 4.5 | Weak demo query 1 | Fallback chunk, multilingual map, hybrid `k` | A, B |
| R8 | Labels invalidated | A change after G4 | Wasted 8+ labelling hours | Freeze rule; re-label only affected queries | C |
| R9 | C overloaded | Any C task slips > 1 day | Evaluation late | Move UI items to A; cut ladder | all |
| R10 | Stale demo recording | Index/config change after 7.1 | Replay shows old behaviour | Tag at G5; re-record on any change | B |
| R11 | `base_model` coverage low | 2.4 report | Lineage shows mostly ⚠️ | Drop lineage from the demo | A |
| R12 | Wrong claims about licences | NLLB-200 not CC-BY-NC | Demo query 2 premise fails | Check in 1.11; choose another model if so | C |
| R13 | Reranker too slow or large | 1.7 | Slow queries | Reranker off as a documented variant | B |
| R14 | Streamlit state bugs lose the clarify loop | Any rehearsal | Embarrassing demo | E-APP tests (7.8); replay as fallback | C |
| R15 | Key or secret leaks | Any commit | Account abuse | Gitignored `.env`; secret scan in CI; rotate keys after the project | all |

## 8. Cut ladder (date-triggered)

| Trigger | Cut, in this order |
|---|---|
| Any gate slips by one day | Relevance labelling 40 to 30 queries; chunking ablation to reranker on/off (no second index, saves 6.2 and 6.9, 6.10) |
| G3 later than Oct 26, or two gates slip | Memory estimate, then lineage, then relax-and-retry, then tooltips (PROJECT.md order); hide the panels in the UI |
| G4 not reached by Oct 28 | Freeze with what exists; drop the keyword baseline from the table (documented); keep naive RAG and the HF Hub baseline |
| Recording cannot finish | Demo live with the Ollama fallback rehearsed, and screenshots as backup |

**Never cut:** constraint verification, `modifiable`, shown intent, the clarifying loop, "Try it",
the naive-RAG baseline, the faithfulness check, the evaluation itself.

## 9. Decisions needed (with the default if you don't answer)

| # | Decision | Default | Note |
|---|---|---|---|
| 1 | Queries labelled for relevance | **40** | 50 needs ~5 h per labeller, which the calendar cannot absorb |
| 2 | HF Hub baseline | **Script the Hub's own filters through `HfApi.list_models` for every query, save once, and spot-check 5 in the website** | Changes the earlier "by hand": 120 manual runs is about 3 h, scripted about 1 h and reproducible |
| 3 | Allow `api.groq.com`, `huggingface.co`, `api.pinecone.io` in the cloud environment | **Yes** | Lets the assistant run the live checks; otherwise laptops (G0) |
| 4 | Final deadline: Oct 29 or Oct 30 | **Oct 29** | One day of slack if Oct 30 |
| 5 | Fetch failure threshold for G2 | **2%** | Proposed; adjust after seeing the real failure reasons |
| 6 | Build the index on CPU or Colab | **Decide from 1.7** | |
| 7 | Add CI (GitHub Actions running `pytest`) | **Yes** | Cheap, and PR review expects it |
| 8 | Ablation | **Section vs fixed-size chunking** (needs `exp-fixed`) | Fallback: reranker on/off |

## 10. Definition of done

- [ ] G0 to G6 passed, or the cut ladder applied and written down
- [ ] All five demo queries work live **and** in `REPLAY=1` with Wi-Fi off (`demo/cache/` recorded against the final `prod`)
- [ ] `pytest` and CI green; live checks recorded in `data-notes.md`
- [ ] Results table regenerates from snapshot, `config.yaml` and one command, from a clean clone
- [ ] Violation rate @5 reported for all four systems on the same queries, unknown rate in its own column
- [ ] Relevance labels with kappa; faithfulness on 30 answers; "Try it" smoke test; latency
- [ ] Poisoned-card test passes and its repeat rate is reported
- [ ] Ollama switch rehearsed; Windows teammates run with `PYTHONUTF8=1`
- [ ] Snapshot on a GitHub Release with its sha256 in `config.yaml`
- [ ] `docs/` matches the code (architecture section 11 reviewed); decisions updated with dated notes
- [ ] Keys rotated after the project (they were shared in a chat during setup)

