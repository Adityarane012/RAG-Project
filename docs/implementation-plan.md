# Implementation plan (single person, to Oct 30)

Status as of **2026-10-21 (evening)**. One person (the project owner) completes the project; the AI assistant wrote and ran
everything that can run from the cloud session. What is left is **human work**: rehearsal, the write-up, a release asset and key rotation (relevance and faithfulness were graded by LLM judges, see §3). This file says what is done, what remains, in what order, and what to cut if time runs short.

Companion docs: [PROJECT.md](PROJECT.md) (what), [decisions.md](decisions.md) (why), [architecture.md](architecture.md) (how),
[testing-strategy.md](testing-strategy.md), [evaluation-plan.md](evaluation-plan.md), [data-pipeline.md](data-pipeline.md),
[data-notes.md](data-notes.md) (every live measurement), [demo-runbook.md](demo-runbook.md), [development.md](development.md).

## 1. Done

| Area | State |
|---|---|
| Verification core | `normalize`, `verify`, `retrieve.build_filter` (D12), license map (extended from the real data), D20 size rule, languages, directions, multilingual map |
| Data | 15,991 models over 11 tasks (9,764 over the original five, plus six tasks added 2026-10-25), canonical base ids, snapshot cut (sha256 in `config.yaml`), data-quality report in [data-notes.md](data-notes.md) |
| Index | 48,179 chunks over 11 tasks (hosted `multilingual-e5-large`, 4.05M tokens, cached) upserted to Pinecone `prod`; the same corpus in an exact local index. The five-task corpus is reproducible as namespace `eval5` (`docs/evaluation-plan.md` §9) |
| Live checks | Pinecone filter semantics E-RET-9..12 pass; hosted rerank works (truncation fix); Groq limits measured; poisoned-card test passes |
| Pipeline | LangGraph with variants ours / naive / keyword; verifies a pool of 100 models before showing 5; retrieval and explanation use the user's own words; deterministic extraction backstop |
| UI | Editable intent, side-by-side comparison, check-a-model, glossary, build-on, Try-it with an honest caveat |
| Evaluation | 100 queries (committed before tuning), 23-case extraction set, five systems, harness, **outputs frozen as v2 (G4)**, ablation without reranker, run on live Pinecone, blind relevance sheet (40 queries, 686 pairs), faithfulness sheet (28 explanations), labelling and scoring tools with reports |
| Demo | Recorded against Pinecone (`demo/cache/`), replay verified with the network broken |
| Tests | About 300, offline |

## 2. Headline results so far (v2, 75 normal queries; full tables in `eval/results/results-v2.md`)

| System | Violation % | Unknown % | Fully verified % |
|---|---|---|---|
| ours | 0.0 | 16.7 | 83.3 |
| naive RAG | 50.4 | 20.5 | 29.1 |
| keyword + filters | 0.0 | 62.0 | 38.0 |
| HF Hub, basic filters | 32.8 | 13.6 | 53.6 |
| HF Hub, licensed filters | 25.9 | 14.7 | 59.5 |

Ours never recommends a failing model by construction (D2), so the comparison that matters is *fully verified* and, once
labelled, *relevance*: the keyword baseline also never violates but is ⚠️ on 62% of what it returns. Clarification: ours asked
on 100% of the 15 vague queries. "Impossible" queries cannot be proved impossible (unknown-size and unknown-language models
never fail), so the abstention metric is defined on the 12 queries where no model in the corpus fully passes: ours shows the
no-verified-model banner on all 12 and never claims verification, while the baselines recommend violators on 63 to 75% of
their results. The abstain and relax paths exist and are tested, but are not reachable on this corpus (see §6).

## 3. Remaining work (you), in order

Relevance grading, the repeat pass and faithfulness scoring were done on 2026-10-25 by **independent Claude agents (LLM judges), not
humans**: see `eval/labels/PROVENANCE.md`, `eval/results/relevance.md` and `eval/results/faithfulness.md`. That is weaker evidence than
human labelling and the write-up says so. What is left:

| # | Task | Time | How | When |
|---|---|---|---|---|
| H1 | Rehearse twice: live, and `REPLAY=1` with Wi-Fi off; take screenshots | about 2 h | [demo-runbook.md](demo-runbook.md); `python -m scripts.rehearse_demo` is only the automated check | Oct 27 to Oct 29 |
| H2 | Read and finish the write-up (format not decided yet) | your time | `docs/writeup.md`; sources: `eval/results/*.md`, [data-notes.md](data-notes.md), [security-and-limitations.md](security-and-limitations.md), [eval/seen.md](../eval/seen.md) | Oct 26 to Oct 29 |
| H3 | Attach `data/snapshot-2026-10-21/records.jsonl.gz` to a GitHub Release and put its URL in `config.yaml: snapshot_url` | 15 min | GitHub web UI | any time |
| H4 | **Rotate the Groq, Hugging Face and Pinecone keys** after Oct 30 (they were pasted into the chat) | 10 min | provider dashboards | after the project |
| Optional | **Human spot-check of the LLM grades** (for example one query per task, about 40 pairs) | about 30 min | copy `relevance_sheet.csv` to another folder and run `LABEL_DIR=<folder> streamlit run eval/label_app.py`; compare with `labels_pass1.csv`. Do not overwrite the LLM files | any time |

**Caveat (say it in the write-up).** The judges share the builder's model family, one person wrote the queries, and no human has checked the
grades. The agreement figure (kappa 0.874 / 0.945) is between two LLM passes, not between humans.

## 4. Gates and rules

| Gate | State |
|---|---|
| G1 queries committed before tuning | met |
| G2 snapshot cut, report written | met |
| G3 `prod` live, one filtered query per constraint type correct | met (Pinecone semantics check, 4 of 4) |
| G4 evaluation outputs frozen before labelling | met: commit `6881683` (results v2); later commits add tools and a Pinecone re-run, not changes to the labelled outputs |
| G5 demo recorded | met (`demo/cache/`). Re-record if the index or config changes |
| G6 two rehearsals | open (H5) |

**After G4 do not change** retrieval, ranking, prompts, models or config values: the labels depend on the frozen outputs. If you
must, re-run `python -m eval.run_eval --tag v3 --label 40`, which makes a new blind sheet and **invalidates labels already given**.
Every evaluation query used for debugging is listed in [eval/seen.md](../eval/seen.md).

## 5. Budgets (measured)

| Resource | Limit | Used so far |
|---|---|---|
| Groq tokens per day (`gpt-oss-20b`) | 200,000 | extraction about 500 per call; explanation 1,345 to 2,778; about 3,300 per explained query. The 28-item faithfulness set and the demo are cached |
| Groq tokens per minute | 8,000 | the throttle settles against real usage |
| Pinecone hosted embedding | not published | 2.49M tokens for the whole corpus; rebuilds are free (cache) |
| Pinecone storage/reads | Starter | 48,179 vectors; the evaluation and demo used a few thousand read units |
| Pinecone hosted rerank | 500 requests a month | **Used up on 2026-10-25.** Uncached queries are not reranked (the UI says so); `RERANKER=local` is the fallback; resets next month |

## 6. Findings that shape the write-up

- **Verified models are invisible to semantic search** (direction, size, license are not in the card text). Verifying a pool of 100 and then cutting to 5 raised fully verified answers from 72% to 83% (v1 to v2) and fixed the translation queries.
- **The extractor's `soft_query` is fragile** ("permissive license" replaced the topic), so every system searches with the user's own words.
- **27% of models have unknown size** (GGUF-only, ONNX-only, no standard weights): ⚠️ by design, not guessed.
- **Direction is known for only 380 models** (`opus-mt-*` names); most translation answers show direction ⚠️.
- **Abstain/relax are unreachable here**: unknown-size (27%) and unknown-language (13%) models always remain, so an impossible request ends as an all-⚠️ answer with the banner (the behaviour you chose).
- **Try-it**: 10 of 18 small models ran the template; MLX, quantized, corrupt or custom-code models need other tooling (the UI says so).
- **A named permissive license** (Apache/MIT/BSD/"permissive") is read as commercial + modifiable, an approximation shown in "We understood".

## 7. Risks

| Risk | Mitigation |
|---|---|
| LLM-judged grades are challenged | Say so in the write-up; offer the optional human spot-check (§3); the reasons for every grade are in `eval/labels/llm_judge_reasons.csv` |
| Live demo fails (Wi-Fi, quota) | `REPLAY=1` with the recorded runs; Groq fallback model; local index (`INDEX_BACKEND=local`) |
| Config or index changed after G4/G5 | re-run and re-record; labels must be redone |

## 8. Cut ladder (in this order if time runs short)

1. Skip the optional human spot-check.
2. Skip the second rehearsal.

Already cut: D24 reported metrics and live fetch in check-a-model; the reranker ablation is reported on latency only (relevance
impact is not measured because the ablation outputs are not in the labelled sheet).

## 9. Definition of done

- Relevance pass 1 and the repeat pass done; `eval/results/relevance.md` and `faithfulness.md` generated.
- Demo rehearsed twice (live and replay).
- Write-up content assembled from the result files (format decided later).
- Keys rotated.
