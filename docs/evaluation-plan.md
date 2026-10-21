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
| Impossible | ~10 | same | no model can satisfy all constraints (e.g. Marathi ASR under 10 MB, commercial and modifiable; a CC-BY-ND-only niche); confirmed impossible against the snapshot |
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

## 3. Metrics

All computed by re-verifying each system's top-5 with `verify.verify` against the query's
parsed constraints, so one definition of "violation" is applied to every system.

| Metric | Definition | Computed by |
|---|---|---|
| **Violation rate @5** | recommended models (top 5/query) with ≥1 ❌ ÷ all recommended | `violation_rate_at_k` |
| **% unknown @5** | models with no ❌ but ≥1 ⚠️ ÷ all recommended | `unknown_rate_at_k` |
| **Relevance @5** | graded match to the soft preference (see §5) | manual, ~50 queries |
| **Abstention accuracy** | on impossible queries, share where the outcome is `abstain` or `relax` | `abstention_accuracy` |
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
| **Naive RAG** | same index, embeddings, reranker and LLM; **no metadata filters, no verification** (task-only filtering is not allowed either) |
| **Keyword + filters** | BM25 over card text with the same metadata filters as ours |
| **HF Hub filters** | the Hub's own task / language / license filters plus its search; run **once**, results saved to `eval/baselines/` because the Hub changes |
| **Ours** | the full graph |

For baselines, "the query's parsed constraints" come from the same `extract_constraints`
output so every system is judged against identical rules. The HF baseline filters on the
license *string*, so expect a measurable rights-violation rate from it, which is the point.

**Fairness checks:** same corpus snapshot; same top-5 cut; the baselines get the same
constraint parse for building their filters (where they have filters); no per-system
prompt tuning beyond what ours also received.

## 5. Manual labelling

**Relevance @5** (~50 queries). Two labellers where possible; one sheet row per
(query, model). Grade against the *soft preference only* (hard constraints are scored
automatically):

| Grade | Meaning |
|---|---|
| 2 | Clearly suits the preference (card says so or evidence is explicit) |
| 1 | Plausible: right task/language, no evidence on the preference |
| 0 | Does not suit |

Report mean grade@5 and the share of queries with at least one grade-2 model. Label blind
to which system produced the list (shuffle systems together). Report inter-labeller
agreement on a shared subset of ~10 queries.

**Faithfulness** (~30 answers). For each explanation, split into claims; mark each
*supported* / *unsupported* / *contradicted* by the cited `card_section`. Report the share
supported and list the unsupported claims.

## 6. Ablations and design justification

- **Four-system table** (D19) on the full query set.
- At least one **tuning choice backed by a number**: relevance@5 with section chunking vs
  fixed-size chunking (same index otherwise). Optionally reranker on/off.
- Slice the results: by task, by slice (§2), and Indic vs non-Indic queries.

## 7. Reproducibility (D21)

`eval/run_eval.py` (to be implemented in WP7) must regenerate the results table from
**snapshot + `config.yaml` + the query set** with one command, writing
`eval/results/<snapshot-date>.md`. Record: snapshot date, config hash, git commit,
LLM provider/model, reranker. Cache LLM responses (already automatic) so a rerun is
deterministic.

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
