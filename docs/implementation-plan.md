# Detailed implementation plan

Status as of **2026-10-21 (day 6 of 14)**. The original schedule in
[PROJECT.md §8](PROJECT.md) started on 2026-10-16, so the code-complete date is
**2026-10-29** (counting 16 Oct as day 1; "16 Oct + 14 days" is Oct 30, so that is one day of slack; confirm which the course means). That leaves **8 full days after today**. Edge cases for every work package are catalogued in
[testing-strategy.md](testing-strategy.md); IDs like `E-NORM-3` refer to it.

## 1. Where we are

### Built and unit-tested offline (127 tests, no network)

License/rights map · D20 size rule · language normalisation · multilingual-map seed ·
`verify` (incl. direction, notes, size words) · Pinecone filters · chunk→model grouping ·
card cleaning · section chunking · vector building · guidance layer · build-on estimates ·
D17 delimiters + citation filter · LLM validation + cache · LangGraph pipeline (stub deps) ·
eval metrics (incl. verifiably-impossible check, Cohen's kappa) · resumable ingest (mocked HTTP) ·
canonical base-model ids · deterministic checksummed snapshot + data-quality report ·
opus-mt direction parsing · local reranker (fake scorer) · record/replay of graph runs ·
Groq→fallback model on rate limit · Streamlit renderer incl. the "not fully verified" banner.

### Not built, or never run against a live service

| Gap | Blocks |
|---|---|
| `ingest` has never touched the real Hub; field names in `normalize_record` are from documentation, not a live response | everything downstream |
| Nothing is in Pinecone yet (`index.main()` is a stub) | retrieval, demo |
| `app.get_graph()` is not wired (embedder, Pinecone, reranker, `llm.explain`) | the demo |
| `rerank.LocalReranker` is written and contract-tested with a fake scorer, but has never loaded the real `bge-reranker-v2-m3`; Pinecone-hosted not evaluated | retrieval quality |
| Check-a-model lookup (D23) is a placeholder | demo item 5 |
| `eval/queries.jsonl` not written; baselines not built (naive RAG and keyword search are to be config flags on the pipeline) | all of evaluation |
| Groq/Ollama never called; JSON-mode and accuracy unmeasured (D7) | extraction trust |
| Record/replay is built, but **no demo query has been recorded** (needs the live pipeline first); WP9 | demo resilience |
| Snapshot builder exists but has never run on real data; GitHub Release not created | reproducibility |

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

## 3. Roles

D11 forces one constraint: the person who writes the evaluation queries must not be
building the pipeline. Names to be filled in by the team.

| Role | Who | Owns | Work packages |
|---|---|---|---|
| **A: Data** | `[TEAM: name]` | Hub access, metadata, multilingual map (every entry cites a source), index, snapshot Release | WP1 (HF/Pinecone checks), WP2, WP3; second relevance labeller |
| **B: Pipeline** | `[TEAM: name]` | LLM, retrieval, graph, **and the baselines that are pipeline variants** (naive RAG and keyword + filters as config flags). Creates the Pinecone index and holds its key | WP1 (Groq/Ollama), WP5, WP6 (naive, keyword), WP9 wiring and recording |
| **C: Evaluation & UI** *(writes queries; does **not** build retrieval or label as B)* | `[TEAM: name]` | Query set, relevance labels, running the HF Hub baseline **by hand**, `run_eval.py`, the Streamlit UI | WP4, WP6 (HF Hub only), WP7, WP8, UI part of WP5/WP9; first relevance labeller |

Why baselines belong to B: naive RAG and keyword search reuse the pipeline's index,
embeddings, reranker and LLM, and differ only by switches, so the person who owns the
pipeline can build them without drift and C stays independent of the system under test.
Relevance labellers are A and C (not B) so the person who tuned the system does not judge it.
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
| Direction parsing | Fetch 3 real `Helsinki-NLP/opus-mt-*` ids (incl. one `tc-big`) and a user fine-tune | `directions_from_name` agrees with what the cards say; note any fine-tune whose direction differs |
| Canonical ids | Query the Hub API for the legacy id `xlm-roberta-base` | The returned `id` is `FacebookAI/xlm-roberta-base`; if not, `ingest.canonicalize` needs another resolution method (assumption in D18) |
| Groq JSON mode | 20 queries on `openai/gpt-oss-20b` (then the fallback model) | `response_format=json_object` is accepted and parses; record the rate-limit headers |
| Task-guide links | Open the five URLs in `guide.TASK_GUIDES` | All resolve, or fix them |
| Embedding speed | Embed 200 real cards with `multilingual-e5-large` on CPU and on Colab GPU | Chunks/sec known → decides where WP3 runs |
| Token budget | Tokenise 50 Indic cards with the real e5 tokenizer | Compare with `index.approx_tokens`; adjust the estimate if sections exceed ~507 tokens (**E-IDX-4**) |

### WP2: Ingestion run · day 7–8 (Oct 22–23) · A

**Goal:** a complete raw cache of ~5–8k models.

- Run `python -m src.ingest fetch` (resumable; safe to interrupt and restart).
- Inspect `data/raw/failed.jsonl`; decide per model whether to retry or drop.
- Resolve canonical base-model ids (`ingest fetch` does this at the end, cached in
  `data/raw/_canonical_ids.json`).
- Cut the snapshot: `python -m src.snapshot build` writes
  `data/snapshot-<date>/records.jsonl.gz` (deterministic bytes), prints the data-quality
  report and the `snapshot_date` / `snapshot_sha256` to paste into `config.yaml`. Attach the
  file to a **GitHub Release** and put its URL in `snapshot_url`. The raw cache stays local.
- Log **how many models have unknown size, and why** (`size_unknown.by_reason` in the
  report). This is the data the size-rule decision (open question 11) rests on.
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
- Wire the reranker: `rerank.LocalReranker` is the default (D9); try Pinecone-hosted only if the plan check allows it and time remains.
- Build with `exp-<name>`; only B promotes to `prod`.
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
- Check-a-model lookup (D23): **snapshot only**. The live-fetch *Should* is cut (see §6).
- Poisoned-card test (D17): 3 synthetic cards in a **separate** index, assert table and
  explanation unaffected (spec: testing-strategy §7).

**Acceptance:** all five demo queries run end to end from the UI; clarify and relax loops
work with the caps; every edge case in **E-GRAPH-\*** and **E-APP-\*** has a test.

### WP6: Baselines · day 9–11 (Oct 24–26) · B (naive RAG, keyword), C (HF Hub)

Definitions in [evaluation-plan.md §4](evaluation-plan.md#4-baselines-d19).
**B** builds *naive RAG* (same index, embeddings, reranker and LLM, but no metadata
filters and no verification) and *keyword + filters* (BM25 over card text with the same
filters) as **configuration flags on the pipeline**, so they cannot drift from it.
**C** runs the *HF Hub filters* baseline by hand, **once**, and saves the results to
`eval/baselines/` because the Hub changes.

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
- **Record the demo (decided: replay).** The recorder/player is built (`src/replay.py`,
  `REPLAY=1` / `RECORD=1`). What is left is running every planned demo query **and its
  follow-ups** (clarify answer, relax accept) once with `RECORD=1` against live services,
  committing `demo/cache/`, and re-recording after any index change. The demo says
  it is replaying a recorded run.
- Rehearse the Ollama switch end to end ([demo-runbook.md](demo-runbook.md)).

**Acceptance:** two full rehearsals, one with `REPLAY=1` and Wi-Fi off.

## 5. Calendar (re-baselined)

| Day | Date | A: Data | B: Pipeline | C: Eval & UI |
|---|---|---|---|---|
| 6 | Oct 21 | WP1 Hub + Pinecone checks | WP1 Groq/Ollama checks; create the Pinecone index | **WP4 start writing queries**; **ask the professor about the report format** |
| 7 | Oct 22 | WP2 ingest run | WP5 `get_graph` skeleton | WP4; **20-minute team meeting: read D2, D3, D8–D11 and mark them Accepted** |
| 8 | Oct 23 | WP2 snapshot, report, Release | WP5 | WP4 done, **committed before any tuning** |
| 9 | Oct 24 | WP3 index build (`exp-`) | WP5 wire reranker; WP6 naive + keyword flags | UI: editable intent, tooltips |
| 10 | Oct 25 | WP3 `prod` promote (with B) | WP5 poisoned-card test; WP6 done | WP6 HF Hub baseline by hand (once) |
| 11 | Oct 26 | Extend maps from the report | Fix failure cases; record demo runs | WP7 labels (A + C label) |
| 12 | Oct 27 | WP7 labels (A) | Relax/lineage polish | WP7 run `run_eval.py`, results table, kappa |
| 13 | Oct 28 | WP8 | WP9 re-record, code freeze | WP8, WP9 |
| 14 | Oct 29 | Rehearse | Rehearse (incl. Ollama and `REPLAY=1`) | Rehearse |

## 6. Scope cuts

**Applied 2026-10-21** (8 days left): reported metrics (D24) and the live-fetch part of
check-a-model (D23) are cut. The code for reported metrics stays but is not shown in the UI.

**Next, if we fall further behind** (order from PROJECT §8): memory estimate → lineage →
relax-and-retry → tooltips.
**Never cut:** constraint verification, `modifiable`, shown intent, the clarifying loop,
Try it, the naive-RAG baseline, the faithfulness check, evaluation.

## 7. Definition of done (whole project)

- [ ] All five demo queries work from the UI with live services **and** in replay mode (`demo/cache/` recorded against the final index)
- [ ] `pytest` green; live-service checks (WP1) recorded in `docs/data-notes.md`
- [ ] Results table regenerates from snapshot + `config.yaml` + one command
- [ ] Constraint violation rate @5 reported for all four systems on the same queries
- [ ] Poisoned-card test passes
- [ ] Ollama switch rehearsed
- [ ] `docs/` matches the code (architecture §11 deviations list reviewed)
- [ ] Decisions still marked *Proposed* (D2, D3, D8, D9, D10, D11) confirmed by the team (meeting on Oct 22)
- [ ] Report format confirmed with the professor
- [ ] Windows teammates: `PYTHONUTF8=1` set, Ollama and Streamlit run
- [ ] Snapshot attached to a GitHub Release; its sha256 is in `config.yaml`
