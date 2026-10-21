# Evaluation plan

Implements D11 (metrics) and D19 (baselines). Automatic metrics are in
[`eval/metrics.py`](../eval/metrics.py); testing of the code itself is in
[testing-strategy.md](testing-strategy.md).

## 1. Questions the evaluation must answer

1. Does constraint verification actually reduce rule violations? *(violation rate @5)*
2. Does it cost relevance? *(relevance @5)*
3. Does it say "no" when it should, and ask when it should? *(abstention, clarification)*
4. Are the generated explanations grounded in the cards? *(faithfulness)*
5. Is it better than just using Hugging Face's own filters? *(HF Hub baseline)*

## 2. Query set

~120 queries in `eval/queries.jsonl`, **written and committed before any tuning**.

```json
{"id": "q001", "query": "Small sentiment model for Hindi I can use commercially", "kind": "normal", "source": "teammate"}
```

| Slice | Count | Author | Notes |
|---|---|---|---|
| Normal | ~75 | teammate **not** building the pipeline | spread over the 5 tasks and ≥6 Indic languages; mix of size, rights, language, direction constraints |
| Impossible | ~10 | same | **verifiably** impossible: every model in the snapshot gets a known ❌ (e.g. Marathi ASR under 10 MB, commercial and modifiable). Check each with `eval.metrics.verifiably_impossible(records, constraints)`; if a model is only ⚠️ the query measures missing data, so rewrite it |
| Vague (beginner) | ~15 | same | missing task ("I want a Hindi model"), no constraints, jargon-free phrasing |
| Classmates | ~20 | classmates who have never seen the system | any kind; reduces author bias |

Rules:

- The author must not look at system output while writing.
- Each query records its `kind`; `eval.metrics.load_queries` rejects bad records.
- After the first tuning change, **do not edit the set**. If a query turns out to be broken
  (typo, contradictory), mark it and report results with and without it.
- Keep the set split-free: we tune on none of it, so there is no train/test separation to
  manage, but any query used to debug a failure must be listed as "seen" in the write-up.
- Include a few queries with no extractable constraint and a few non-English (Hindi/Marathi)
  queries; the first group makes violation rate trivially zero and must be reported
  separately (E-MET-3).

**Single-author note (2026-10-21).** The set was written by the person who also builds the system,
before any retrieval experiment, and committed first (gate G1). It has 100 queries (75 normal, 15
vague, 10 impossible), not ~120: there are no classmate queries. This is a bias the write-up must
state; the freeze and the "seen" list are the mitigations, not a cure.

## 3. Metrics

All computed by re-verifying each system's top-5 with `verify.verify` against the query's
parsed constraints, so one definition of "violation" is applied to every system.

| Metric | Definition | Computed by |
|---|---|---|
| **Violation rate @5** | recommended models (top 5/query) with ≥1 ❌ ÷ all recommended | `violation_rate_at_k` |
| **% unknown @5** | models with no ❌ but ≥1 ⚠️ ÷ all recommended | `unknown_rate_at_k` |
| **Relevance @5** | graded match to the soft preference (see §5) | manual, 40 queries by default (D11 says ~50; see the implementation plan, decision 1) |
| **Abstention accuracy** | on impossible queries, share where the outcome is `abstain` or `relax`. The system abstains only when **every** candidate has a known ❌; a result set of only ⚠️ is shown with the "No model fully verified" banner and is *not* an abstention | `abstention_accuracy` |
| **Clarification rate** | on vague queries, share where the outcome is `clarify` | `clarification_rate` |
| **`modifiable` correctness** | shown value equals the license map | `modifiable_correctness` |
| **Explanation faithfulness** | share of explanation claims supported by the cited card text | manual on ~30 answers, or RAGAS |
| **"Try it" smoke test** | snippet executes | script on ~20 models |
| **Latency** | median and worst case per query | logged per run |

Report violation and unknown rates **as separate columns**: an unknown is neither a pass
nor a violation (D12).

## 4. Baselines (D19)

| System | Definition |
|---|---|
| **Naive RAG** | same index, embeddings, reranker and LLM; **no metadata filters, no verification** (task-only filtering is not allowed either). Built by B as a configuration flag on the pipeline |
| **Keyword + filters** | BM25 over card text with the same metadata filters as ours. Built by B as a configuration flag |
| **HF Hub filters** | the Hub's own task / language / license filters plus its search; run **once by C** (scripted through the Hub API's own filters with 5 manual spot-checks in the website; see the implementation plan, decision 2), results saved to `eval/baselines/` because the Hub changes |
| **Ours** | the full graph |

For baselines, "the query's parsed constraints" come from the same `extract_constraints`
output so every system is judged against identical rules. The HF baseline filters on the
license *string*, so expect a measurable rights-violation rate from it, which is the point.

**Fairness checks:** same corpus snapshot; same top-5 cut; the baselines get the same
constraint parse for building their filters (where they have filters); no per-system
prompt tuning beyond what ours also received.

## 5. Manual labelling

**Relevance @5** (40 queries by default; D11 says ~50). Two labellers, **A and C (not B**, who tuned the system); one sheet row per
(query, model). The unit labelled is the *union* of each query's top-5 across the four systems (about 10 unique query-model pairs per query), so 40 queries is about 400 judgements per labeller, roughly 3.5 hours; 50 queries would be about 5 hours. Grade against the *soft preference only* (hard constraints are scored
automatically):

| Grade | Meaning |
|---|---|
| 2 | Clearly suits the preference (card says so or evidence is explicit) |
| 1 | Plausible: right task/language, no evidence on the preference |
| 0 | Does not suit |

Report mean grade@5 and the share of queries with at least one grade-2 model. Label blind
to which system produced the list (shuffle systems together). Both label the same items;
report **Cohen's kappa** from `eval.metrics.cohens_kappa`: quadratic-weighted (the usual
choice for ordinal grades, since 0-vs-2 is worse than 1-vs-2) and unweighted. Disagreements
are resolved by discussion, and the pre-resolution kappa is the one reported.

**Faithfulness** (~30 answers), scored **by hand**. For each explanation, split into claims; mark each
*supported* / *unsupported* / *contradicted* by the cited `card_section`. Report the share
supported and list the unsupported claims. RAGAS faithfulness may be run as a cross-check
only: it adds an LLM judge, which is another component that can fail.

## 6. Ablations and design justification

- **Four-system table** (D19) on the full query set.
- At least one **tuning choice backed by a number**: relevance@5 with section chunking vs
  fixed-size chunking (same index otherwise). Optionally reranker on/off.
- Slice the results: by task, by slice (§2), and Indic vs non-Indic queries.

## 7. Reproducibility (D21)

`eval/run_eval.py` (to be implemented in Phase 5, tasks 5.3 and 5.7) must regenerate the results table from
**snapshot + `config.yaml` + the query set** with one command, writing
`eval/results/<snapshot-date>.md`. Record: snapshot date, config hash, git commit,
LLM provider/model, reranker. Cache LLM responses (already automatic) so a rerun is
deterministic.

## 7b. Staying inside the free-tier limits

Groq's free tier for `gpt-oss-20b` is 8,000 tokens/minute and 200,000/day (about 30 fully
explained queries a day, see [architecture.md §7.0](architecture.md#70-staying-inside-free-tier-token-limits)).
So: (1) the automatic metrics (violation, unknown, abstention, clarification) need **no
explanations**; run them with `Deps.explain = None`, which costs ~1K tokens a query (about 120K for
the whole set, one day). (2) Generate explanations only for the ~30–50 answers that are hand-checked
for faithfulness, over two days or on Ollama. (3) Shard long runs across teammates' own accounts
(limits are per organization, not per key). (4) The response cache means a rerun costs nothing, so
**never change a prompt or model mid-evaluation** without accepting a full re-run.

## 8. Results table template

| System | Violation @5 | Unknown @5 | Relevance @5 | Abstention | Clarification | Median latency |
|---|---|---|---|---|---|---|
| Naive RAG | | | | n/a | n/a | |
| Keyword + filters | | | | | n/a | |
| HF Hub filters | | | | | n/a | n/a |
| **Ours** | | | | | | |

## 9. Threats to validity (state these in the write-up)

- The query set has ~120 items; differences of a few points are noise. Report counts, not just rates.
- Ground truth for hard constraints is *declared metadata*, which can be wrong or missing.
- The snapshot is a sample of the Hub (~5–8k models), not the Hub.
- Relevance labels are subjective; mitigate with two labellers and an agreement figure.
- Extraction errors silently drop constraints and make violation rates look better; the
  silent-drop rate from the extraction test (testing-strategy §6) bounds this.
