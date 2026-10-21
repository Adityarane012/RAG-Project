# Detailed implementation plan

Status as of **2026-10-21 (day 6 of 14)**. The original schedule in
[PROJECT.md §8](PROJECT.md) started on 2026-10-16, so the code-complete date is
**2026-10-29**. Edge cases for every work package are catalogued in
[testing-strategy.md](testing-strategy.md); IDs like `E-NORM-3` refer to it.

## 1. Where we are

### Built and unit-tested offline (95 tests, no network)

License/rights map · D20 size rule · language normalisation · multilingual-map seed ·
`verify` (incl. direction, notes, size words) · Pinecone filters · chunk→model grouping ·
card cleaning · section chunking · vector building · guidance layer · build-on estimates ·
D17 delimiters + citation filter · LLM validation + cache · LangGraph pipeline (stub deps) ·
eval metrics · resumable ingest (mocked HTTP) · Streamlit renderer.

### Not built, or never run against a live service

| Gap | Blocks |
|---|---|
| `ingest` has never touched the real Hub; field names in `normalize_record` are from documentation, not a live response | everything downstream |
| Nothing is in Pinecone yet (`index.main()` is a stub) | retrieval, demo |
| `app.get_graph()` is not wired (embedder, Pinecone, reranker, `llm.explain`) | the demo |
| Reranker choice (D9) not made; neither Pinecone-hosted nor `bge-reranker-v2-m3` integrated | retrieval quality |
| Check-a-model lookup (D23) is a placeholder | demo item 5 |
| `eval/queries.jsonl` not written; baselines not built | all of evaluation |
| Groq/Ollama never called; JSON-mode and accuracy unmeasured (D7) | extraction trust |
| Demo "offline mode" (D21) not designed: see WP9 | demo resilience |

### Verification checklist from decisions.md (all still open)

Model counts per task · Pinecone Starter limits and reranking · Groq rate limits ·
NLLB-200 license · Ollama on a laptop · `$or` filter on a 10-vector index ·
`base_model` coverage · `param_count` availability · HF Hub UI filters ·
`model-index` coverage.

## 2. Critical path

```
WP1 live checks ─► WP2 ingest run ─► WP3 index build ─► WP5 wire graph ─► WP9 demo
                                        │                  ▲
WP4 query set (write BEFORE tuning) ────┴─► WP6 baselines ─► WP7 eval run ─► WP8 write-up
```

Two items are urgent regardless of who owns what:

1. **Write the query set (WP4) before any retrieval experiment.** D11 requires it to exist
   before tuning. The first time someone adjusts `k`, a threshold, or a prompt while
   looking at results, the set is contaminated. The author must be the teammate *not*
   building the pipeline.
2. **Run the day-1 live checks (WP1).** Three of them can invalidate design assumptions
   (D12's `$or`, D8's token budget, D9's reranker availability).

## 3. Suggested roles

D11 forces one constraint: the person who writes the evaluation queries must not be
building the pipeline. A reasonable split for three people (adjust to taste):

| Role | Owns | Work packages |
|---|---|---|
| **A: Data** | Hub access, metadata, index | WP1 (HF/Pinecone checks), WP2, WP3 |
| **B: Pipeline** | LLM, retrieval, graph | WP1 (Groq/Ollama), WP5, WP6 (naive RAG), WP9 wiring |
| **C: Evaluation & UI** *(writes queries; does **not** build retrieval)* | Query set, labels, baselines, UI polish | WP4, WP6 (keyword + HF Hub), WP7, WP8, UI part of WP9 |

Everyone must be able to explain the whole graph and defend D2 in the viva.

## 4. Work packages

Each package lists goal, tasks, acceptance criteria and the edge cases that must be
covered before it is "done". Dates assume the 2026-10-29 code-complete target.

### WP1: Live checks · day 6–7 (Oct 21–22) · A + B

**Goal:** replace documentation-based assumptions with observed behaviour.

| Task | Command / action | Acceptance |
|---|---|---|
| Model counts per task | `python -m src.ingest counts` | Per-task and total counts printed; compare to the ~5–8k estimate; record in `docs/data-notes.md` |
| Live Hub response shape | `curl "https://huggingface.co/api/models/<id>?blobs=true&cardData=true"` for 5 varied models (ASR, translation, a gated model, a model with no card, a multilingual one) | Save as fixtures in `tests/fixtures/`; confirm `siblings[].size`, `safetensors.total`, `cardData.{language,license,base_model,model-index}` exist as `normalize_record` assumes |
| Pinecone `$or` semantics | 10-vector throw-away index: some vectors without `size_mb` | `{"$or":[{"size_mb":{"$lte":500}},{"size_status":{"$eq":"unknown"}}]}` returns exactly the small ones **plus** the unknowns; `$in` on a list field matches any element; `$and` of two `$or`s works (**E-RET-9..11**) |
| Pinecone plan | Console / list-models API | Record inference-token limit and whether hosted reranking is available → decides D9 |
| Groq | 20 extraction queries | JSON parse rate and constraint accuracy measured (spec: testing-strategy §6); rate limits recorded |
| Ollama | Same 20 queries on a team laptop | Passes the same test; latency recorded |
| NLLB-200 license | Model card | Confirm CC-BY-NC (demo item 2 depends on it) |
| Task-guide links | Open the five URLs in `guide.TASK_GUIDES` | All resolve, or fix them |
| Embedding speed | Embed 200 real cards with `multilingual-e5-large` on CPU and on Colab GPU | Chunks/sec known → decides where WP3 runs |
| Token budget | Tokenise 50 Indic cards with the real e5 tokenizer | Compare with `index.approx_tokens`; adjust the estimate if sections exceed ~507 tokens (**E-IDX-4**) |

### WP2: Ingestion run · day 7–8 (Oct 22–23) · A

**Goal:** a complete raw cache of ~5–8k models.

- Run `python -m src.ingest fetch` (resumable; safe to interrupt and restart).
- Inspect `data/raw/failed.jsonl`; decide per model whether to retry or drop.
- Cut a snapshot: `data/snapshot-<date>/records.jsonl` of `normalize_record` output, and
  set `snapshot_date` in `config.yaml`.
- Produce the **data-quality report** (counts, not prose): % `size_status=unknown`,
  % `commercial=unknown`, % `language_status=unknown`, % with `base_model`, % with
  `param_count`, % `doc_quality=minimal`, license-string histogram (top 30, to find
  unmapped licenses), `language` token histogram (to find spellings the normaliser misses).

**Acceptance:** raw cache complete except logged failures; report written to
`docs/data-notes.md`; the license and language histograms reviewed and the maps extended
(**E-NORM-1..14**). *Cut rule:* if `base_model` coverage is very low, drop lineage from the
demo (PROJECT §9).

### WP3: Index build · day 8–9 (Oct 23–24) · A

- Implement `index.main()`: iterate raw cache → `build_vectors` → batch embed → `upsert`
  into namespace `exp-<name>`; promote to `prod` deliberately.
- Choose and wire the reranker (D9).
- Re-run the Pinecone semantics checks (WP1) against the real index.

**Acceptance:** vector count = sum of chunks; a spot check of 10 models shows identical
non-chunk metadata on every chunk; a filtered query for each constraint type returns only
allowed rows plus unknowns; re-running `main()` is idempotent (same ids overwrite).
Edge cases: **E-IDX-1..13**.

### WP4: Query set · day 6–8 (start now) · C

**Goal:** `eval/queries.jsonl`, ~120 queries, before any tuning. Spec in
[evaluation-plan.md](evaluation-plan.md#2-query-set).

**Acceptance:** schema validates with `eval.metrics.load_queries`; the mix matches the spec
(≥10 impossible, ≥15 vague, ~20 from classmates); the file is committed **before** the
first retrieval experiment (git history is the evidence).

### WP5: Wire the graph · day 8–10 (Oct 23–25) · B

- `app.get_graph()`: build `Deps` — `fetch` via `retrieve.pinecone_fetch`, `rerank`,
  `explain=llm.explain`, `lineage_index` from the snapshot, `card_data` from the raw cache.
- Make the shown intent **editable** (D13): the UI writes edits into `overrides`.
- Check-a-model lookup (D23): snapshot first; live fetch + `normalize_record` as *Should*.
- Poisoned-card test (D17): 3 synthetic cards in a **separate** index, assert table and
  explanation unaffected (spec: testing-strategy §7).

**Acceptance:** all five demo queries run end to end from the UI; clarify and relax loops
work with the caps; every edge case in **E-GRAPH-\*** and **E-APP-\*** has a test.

### WP6: Baselines · day 9–11 (Oct 24–26) · B (naive RAG), C (keyword, HF Hub)

Definitions in [evaluation-plan.md §4](evaluation-plan.md#4-baselines-d19). The naive RAG
baseline reuses the same index, embeddings, reranker and LLM with filters and `verify`
disabled, so it is not a strawman. Run the HF Hub baseline **once** and save the results;
the Hub changes.

### WP7: Evaluation run · day 10–12 (Oct 25–27) · C (+ B for fixes)

Run everything with `eval/run_eval.py` (to be implemented once WP5/6 exist); relevance
labels (~50 queries), faithfulness check (~30 answers), "Try it" smoke test (~20 models),
latency log. Produce the results table and the one number-backed tuning choice
(section vs fixed-size chunking). **Acceptance:** the table regenerates from
snapshot + `config.yaml` + one command (D21).

### WP8: Write-up and viva prep · day 12–14 (Oct 27–29) · all

Results, limitations ([security-and-limitations.md](security-and-limitations.md)), the
viva Q&A (PROJECT §10). Verify the results reproduce from a clean checkout.

### WP9: Demo hardening · day 11–14 (Oct 26–29) · B + C

- Polish: tooltips wired into the UI, disclaimer, snapshot date, example queries.
- **Offline demo mode (decision needed).** D21 says the demo works offline, but retrieval
  needs Pinecone and query embedding. Caching only the LLM (already done) is not enough.
  Proposal: record the final graph `State` for each planned demo query to
  `demo/cache/<hash>.json` and add a "replay" switch in `get_graph()`. Costs about half a day.
- Rehearse the Ollama switch end to end ([demo-runbook.md](demo-runbook.md)).

**Acceptance:** two full rehearsals, one with Wi-Fi off.

## 5. Calendar (re-baselined)

| Day | Date | A: Data | B: Pipeline | C: Eval & UI |
|---|---|---|---|---|
| 6 | Oct 21 | WP1 Hub + Pinecone checks | WP1 Groq/Ollama checks | **WP4 start writing queries** |
| 7 | Oct 22 | WP2 ingest run | WP5 `get_graph` skeleton, reranker choice | WP4 |
| 8 | Oct 23 | WP2 snapshot + quality report | WP5 | WP4 done, committed |
| 9 | Oct 24 | WP3 index build | WP5 editable intent, check-a-model | WP6 keyword baseline |
| 10 | Oct 25 | WP3 `prod` promote | WP5 poisoned-card test; WP6 naive RAG | WP6 HF Hub baseline (run once) |
| 11 | Oct 26 | Map extensions from the report | Fix failure cases | WP7 labels |
| 12 | Oct 27 | – | Relax/lineage polish | WP7 run + results table |
| 13 | Oct 28 | WP8 | WP9 replay mode, code freeze | WP8, WP9 |
| 14 | Oct 29 | Rehearse | Rehearse (incl. Ollama) | Rehearse |

## 6. If we fall further behind

Cut in this order (from PROJECT §8): reported metrics (D24) → live fetch in check-a-model →
memory estimate → lineage → relax-and-retry → tooltips.
**Never cut:** constraint verification, `modifiable`, shown intent, the clarifying loop,
Try it, the naive-RAG baseline, the faithfulness check, evaluation.

## 7. Definition of done (whole project)

- [ ] All five demo queries work from the UI with live services **and** in replay mode
- [ ] `pytest` green; live-service checks (WP1) recorded in `docs/data-notes.md`
- [ ] Results table regenerates from snapshot + `config.yaml` + one command
- [ ] Constraint violation rate @5 reported for all four systems on the same queries
- [ ] Poisoned-card test passes
- [ ] Ollama switch rehearsed
- [ ] `docs/` matches the code (architecture §11 deviations list reviewed)
- [ ] Decisions still marked *Proposed* (D2, D3, D8, D9, D10, D11) confirmed by the team
