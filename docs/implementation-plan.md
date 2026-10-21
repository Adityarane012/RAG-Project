# Implementation plan (single person, to Oct 30)

Status as of **2026-10-21**. One person (the project owner) completes the whole project; the AI
assistant writes and runs everything that can be run from the cloud session. Work is split into
**machine work** (the assistant does it in-session) and **human work** (only the owner can do it:
labelling, hand-scoring, rehearsal, GitHub/environment settings, key rotation).

Companion docs: [PROJECT.md](PROJECT.md) (what), [decisions.md](decisions.md) (why),
[architecture.md](architecture.md) (how), [testing-strategy.md](testing-strategy.md) (edge cases, `E-...`),
[evaluation-plan.md](evaluation-plan.md), [data-pipeline.md](data-pipeline.md),
[demo-runbook.md](demo-runbook.md), [development.md](development.md).

## 0. Assumptions

| # | Assumption | If wrong |
|---|---|---|
| 1 | Deadline is **Oct 30**; today is Oct 21 (9 days) | Shift the dates in section 4 |
| 2 | One person; no work is divided. There are no teammates, so there is no second labeller (see section 3) | n/a |
| 3 | Free tiers only. Groq `gpt-oss-20b`/`120b`: 8,000 tokens/min, 1,000 requests/day, 200,000 tokens/day (confirmed from response headers). Pinecone Starter: 1M read / 2M write units per month. Hub: 1,000 API requests / 300 s, 5,000 resolver requests / 300 s | Re-budget (section 6) |
| 4 | 40 queries are labelled for relevance (not 50) | The labelling sheet is built from the first 40 queries by id in `eval/queries.jsonl` order |
| 5 | The report's format is deferred; write-up tasks produce content, not a formatted report | Add formatting time |
| 6 | The cloud sandbox blocks two host groups (section 5). Everything that needs them has a documented local substitute | Allow the hosts; re-run the listed steps |

## 1. Done (machine work)

All code is committed on `claude/wonderful-hypatia-gmeus3` and `main`; 279 offline tests pass.

| Area | State |
|---|---|
| Verification core | `normalize`, `verify`, `retrieve.build_filter` (D12 `$or`), license rights map, D20 size rule, language/direction handling, multilingual map seed |
| Ingest | Resumable Hub fetch (READMEs via `/resolve/`), canonical base-model ids, snapshot builder and data-quality report. Fetched 9,763 of 9,764 candidates (1 logged failure) |
| LLM layer | Groq (`gpt-oss-20b`, fallback `gpt-oss-120b`, `reasoning_effort=low`), Ollama option, cache, token throttle settled against real usage, retry-after handling, deterministic extraction backstop |
| Retrieval | Hosted embeddings (Pinecone inference, content-hash cache), exact `LocalIndex` with Pinecone filter semantics, hosted reranker with cache, evidence selection (<= 4 passages/model, 5,000-token budget) |
| Graph and UI | LangGraph pipeline with variants (ours / naive / keyword), clarify and relax caps, editable intent, side-by-side compare, check-a-model, build-on estimates, glossary, replay mode |
| Baselines and harness | Naive RAG, keyword (BM25), HF Hub (basic and licensed), `eval/run_eval.py`, metrics, blind relevance sheet export, kappa |
| Evaluation assets | 100 queries committed before tuning (G1), 20-case extraction set and runner, parse check of all 100 queries (0 failures; q045 no task extracted, reported only), poisoned-card test (0/5 explanations repeated injected claims) |
| Demo | Scripted recorder `scripts/record_demo.py` + `demo/plan.json` |

## 2. Remaining machine work (assistant, in order)

| # | Task | Output | Needs |
|---|---|---|---|
| M1 | Finish canonicalization; retry the failed model; **cut snapshot**, read the data-quality report | `data/`, numbers into `data-notes.md`; `snapshot_*` lines for `config.yaml` | nothing |
| M2 | Extend license map / aliases / size rule from the report; extend the multilingual map to about 20 entries (each with a source) | code + tests | M1 |
| M3 | Embed the whole corpus (hosted embeddings), build the local index | `data/embeddings`, `data/localindex` | Pinecone control plane (works) |
| M4 | Smoke-test `build_pipeline("ours")` on real queries; calibrate the explain token budget and the two-calls-per-query total (< 8K tokens/min) | measured numbers into `data-notes.md` | M3 |
| M5 | Run `python -m eval.run_eval --tag v1 --label 40` (ours, naive, keyword, hf_basic, hf_licensed); failure analysis; bug fixes (every query used to debug is listed as "seen"); re-run as v2 and **freeze (G4)** | `eval/results/v1`, `v2` | M4 |
| M6 | Resolve the abstention metric from real feasibility counts (section 3) | `evaluation-plan.md` change | M5 |
| M7 | Export the blind relevance sheet (40 queries) and the faithfulness set (about 30 answers) | files for the owner | G4 |
| M8 | Record the demo (`python -m scripts.record_demo`), commit `demo/cache/`, verify `REPLAY=1` | `demo/cache/` | G4 |
| M9 | Update docs with live findings (D8 hosted embeddings note, fallback model, reasoning effort, chunk cap, LocalIndex, blocked hosts, counts) | docs | M1-M8 |
| M10 | Compute final metrics, tables and the content of the write-up (no formatting) | `docs/results.md` | labels |

## 3. Human work (owner)

| # | Task | Estimate | When |
|---|---|---|---|
| H1 | Allow the blocked hosts (section 5); say when done so the assistant can run the live Pinecone and Try-it checks | 5 min | any time |
| H2 | Attach `records.jsonl.gz` to a GitHub Release; confirm the `snapshot_*` lines in `config.yaml` | 15 min | after M1 |
| H3 | **Label relevance 0/1/2** for 40 queries on the blind sheet (about 40 x 5-15 models) | about 4 h | after M7 |
| H4 | **Repeat pass**: re-label a random 15 queries at least 24 h later without looking at the first labels (test-retest agreement, reported as kappa) | about 1.5 h | 1+ day after H3 |
| H5 | **Faithfulness**: hand-score about 30 explanations (claims supported by the cited card text) | about 2 h | after M7 |
| H6 | Rehearse the demo twice (live, and `REPLAY=1` with Wi-Fi off); screenshots | about 2 h | after M8 |
| H7 | Report: decide format when the course says; content comes from M10 | n/a | deferred |
| H8 | Rotate the Groq, HF and Pinecone keys after the project (they were pasted in chat) | 10 min | after Oct 30 |

**Single-labeller caveat (state it in the write-up).** One person writes the queries, labels the
results and reads the outputs, so labels may be biased toward the system's behaviour. Mitigations:
labels are blind (system names hidden, rows shuffled); the sheet is built from the union of all
systems' top 5; outputs are frozen before labelling (G4); and H4 measures self-consistency. Kappa
here is **test-retest agreement of one labeller, not inter-annotator agreement**, and is reported
as such.

**Abstention metric.** Because a model with unknown size or language never *fails* a constraint
(D12), a query cannot always be proven impossible. M5 measures, per "impossible" query, how many
candidates fail with a definite reason. M6 then defines correct non-recommendation as: the system
abstains or relaxes, **or** answers with the all-unknown banner and no verified-violating model.
The violation rate on the impossible slice is reported alongside.

## 4. Calendar to Oct 30

| Day | Machine work | Human work |
|---|---|---|
| Oct 21 (Wed) | M1 (fetch finishing), snapshot, M3 started | H1 |
| Oct 22 | M2, M3 done, M4 | H2 |
| Oct 23 | M5 v1, failure analysis | |
| Oct 24 | fixes, M5 v2, M6; **G4 freeze** | |
| Oct 25 | M7, M8 | H3 (first half) |
| Oct 26 | M9 | H3 (second half), H5 |
| Oct 27 | M10 first numbers | H4 (24 h+ after H3 pass) |
| Oct 28 | M10 final, docs tidy | H6 rehearsal 1 |
| Oct 29 | buffer, re-record only if frozen state changed | H6 rehearsal 2 |
| Oct 30 | deliver | |

## 5. Gates and rules

| Gate | What must be true |
|---|---|
| **G1** (met) | `eval/queries.jsonl` committed before any experiment |
| **G2** | Snapshot cut, report in `data-notes.md`; failed fetches <= 2% |
| **G3** | Index built; one filtered query per constraint type is correct |
| **G4** | Evaluation outputs frozen (results v2 committed) **before any labelling** |
| **G5** | Demo recorded against the frozen index; tag `v1.0-demo` |
| **G6** | Two rehearsals done |

**Tuning policy.** Before G1: no experiments on eval queries (met). G1 to G4: the extraction prompt
and backstop are tuned only on the 20-case extraction set; documented ablations; bug fixes from
failure analysis, with every eval query used for debugging listed as "seen". After G4: no change
to retrieval, ranking, prompts, models or config; any change to the index or config after
recording means re-recording.

**Blocked hosts.** The cloud sandbox allows the Hub API, Groq and the Pinecone control plane and
inference endpoints. It blocks:

| Host | Blocks | Substitute used now |
|---|---|---|
| Pinecone data plane (`hf-model-finder-cactjug.svc.aped-4627-b74a.pinecone.io`, or `*.pinecone.io`) | live Pinecone upsert/query, live check of `$or`/`$in` semantics (E-RET-9 to 12) | `LocalIndex` (exact, same filter semantics, unit-tested) |
| Hugging Face weight CDN (`us.aws.cdn.hf.co`, probably `*.hf.co`) | local reranker and e5 weights, Try-it smoke test on small models | hosted Pinecone reranker; Try-it snippets covered by template tests only |

To allow them: cloud environment menu, Edit, Network access, Allowed domains
(<https://code.claude.com/docs/en/cloud-environments#network-access>). Once allowed, the assistant
runs the live Pinecone semantics check, upserts `prod`, and runs the Try-it smoke test. Nothing in
the deliverable depends on this: the evaluation runs on the local index and the report states that.

## 6. Budgets (measured where stated)

| Resource | Limit | Plan |
|---|---|---|
| Groq tokens per day | 200,000 | Extraction about 650 tokens per call (measured, `reasoning_effort=low`); explanation about 5,000-token prompts. Evaluation: 5 systems x 40 labelled queries share cached extraction; explanations only for the faithfulness set (about 30) and the demo. Spread across days; fallback model has its own daily budget |
| Groq tokens per minute | 8,000 | Throttle settles against real usage; no more than two calls per query inside a minute |
| Pinecone hosted embedding | quota unknown (about 5M tokens historically) | One embedding pass of about 2.5M tokens expected; usage logged in `data/embeddings/usage.jsonl`; the content-hash cache means a rebuild costs nothing |
| Pinecone rerank | small | 1 rerank unit per call; results cached in `data/rerank_cache` |
| Hub | 1,000 API requests / 300 s | Fetch is resumable; done |

## 7. Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Groq daily token limit hit during evaluation | medium | cache; split runs across days; fallback model; `LLM_PROVIDER=ollama` if a laptop is available |
| Hosted embedding quota runs out mid-build | low-medium | cache keeps finished work; the build resumes; fallback is the local e5 model once the CDN is allowed |
| Labelling takes longer than 4 h | medium | labels are on 40 queries, not 50; the sheet is sorted by query so partial labelling still gives complete queries |
| Single-labeller bias | certain | stated limitation, blind sheet, test-retest |
| Everything-unknown results on impossible queries | high | handled by the M6 metric definition |
| Index or config changes after G4 | low | G4 rule; re-record if it happens |

## 8. Cut ladder (in this order if time runs out)

1. Faithfulness set 30 -> 20 answers.
2. Test-retest 15 -> 10 queries.
3. Drop the ablation (reranker on/off, k).
4. Drop the Try-it smoke test (templates stay covered by unit tests).
5. Relevance labelling 40 -> 30 queries.

Already cut: D24 reported metrics and live-fetch in check-a-model.

## 9. Definition of done

- Snapshot cut with date and checksum in `config.yaml`; quality report in `data-notes.md`.
- Index built; evaluation run for all five systems; results v2 committed before labelling.
- 40 queries labelled; 15 re-labelled; about 30 explanations hand-scored.
- Demo recorded and replayable with `REPLAY=1`; two rehearsals done.
- Docs match behaviour (architecture section 11 table updated).
- Write-up content ready (results tables and limitations); format decided later.
- Keys rotated.
