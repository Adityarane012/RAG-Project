# Snapshots, Results and Discussion

## Application snapshots

@fig:ui_compare shows the request "Small sentiment model for Hindi I can use in a commercial app" with the naive-RAG comparison switched on. "We understood" shows that "small" was read as 500 MB. The left column is the full system and every row passes; the right column is naive RAG on the same index with no filters and no checks, and it recommends models whose size row is a red cross. Pass is shown as plain text, fail with a red cross and unknown with a warning sign. For vague requests ("I want a Hindi model") the system asks what the model should do instead of guessing. @fig:ui_banner shows an honest unknown: for "Hindi to Marathi translation under 1 MB" no candidate can be verified (size and direction unknown), so the page shows the banner "No model fully verified" and each row carries a warning sign. Under each model, *Try it* gives a template snippet and *Build on it* gives the modification right, lineage, a GPU-memory estimate for inference, LoRA and full fine-tuning, and a link to the official guide (@fig:ui_banner (b)). Requests the index cannot serve ("text to image diffusion model") are refused with nothing shown.

::: fig ui_compare w=11
ui_compare_short.png
Verified results (left) against naive RAG (right) for a small Hindi sentiment model under a commercial licence.
:::

::: fig ui_banner w=8.8
ui_banner_short.png | (a) Banner when nothing is fully verified
ui_buildon_short.png | (b) Try it and Build on it panels
Unknowns are shown, never guessed; the next step is one click away.
:::

## Corpus and extraction

The snapshot has 15,991 models in eleven tasks. Size is unknown for 29.5% (27.2% in the original five tasks, 6% for image classification and 75% for object detection), commercial use is *yes* for 70.3%, *conditional* for 6.5%, *no* for 3.2% and *unknown* for 20.1%, and 380 translation models state a direction. The language model alone matched the expected constraint record on 90% of 29 test cases with five silent drops; with the deterministic backstop the match was 100% with none (a tuning-set figure, not a generalisation estimate).

## Comparison with the baselines

@tab:main gives the main result on the 75 normal queries; every system's top five is judged by the same verification rules.

::: table main size=8.5 cols=3.6,1.4,1.2,1.5,1.5,1.7,1.2
Main results on 75 normal queries (top five per query).
| System | Answered % | Recs | Violation % | Unknown % | Fully verified % | Median s |
|:--|:-:|:-:|:-:|:-:|:-:|:-:|
| **Ours (constraint-verified RAG)** | 97.3 | 365 | **0.0** | 16.7 | **83.3** | 0.22 |
| Naive RAG | 100.0 | 375 | 50.4 | 20.5 | 29.1 | 0.07 |
| Keyword (BM25) + filters | 100.0 | 368 | 0.0 | 62.0 | 38.0 | 0.05 |
| HF Hub, basic filters | 100.0 | 375 | 32.8 | 13.6 | 53.6 | 0.10 |
| HF Hub, licensed filters | 100.0 | 375 | 25.9 | 14.7 | 59.5 | 0.09 |
:::

::: fig chart_main w=12
chart_main.png
Share of recommended models that are fully verified, unknown or violating, by system.
:::

The full system recommended no failing model and 83.3% of its recommendations were fully verified, against 29.1% for naive RAG and 59.5% for the best Hub filter. @fig:chart_violations shows which constraints the baselines break. It answered 73 of 75 queries; on the other two it asked a clarifying question. Naive RAG failed the size limit on 50.4% of its recommendations, the task on 24.1% and the language on 19.4%. The Hub cannot filter by size and failed it on 80.0% (basic) and 71.9% (licensed) of recommendations; its licensed variant removes commercial-use failures only by accepting a single licence string. Keyword search never violates because it uses the same filters, but 62% of its recommendations are unknown: BM25 matches words, which say nothing about size or licence. Verifying a pool of 100 instead of 25 raised fully verified answers from 72.3% to 83.3% and repaired six translation queries.

::: fig chart_violations w=11
chart_violations.png
Recommendations that fail each constraint, by baseline (ours and keyword search: 0.0 on every constraint).
:::

On the 15 vague queries the system asked a clarifying question every time; baselines answered all of them. Ten requests written to be impossible could not be proved impossible, because a model with unknown size or language never fails; the abstain and relax paths are therefore tested but unreachable on this corpus. On the 12 queries for which no model in the corpus fully passes, ours and keyword search recommended only unknown models, ours showed the banner on all 12 and never claimed verification, while naive RAG and the Hub filters recommended violating models for 63.3% to 75.0% of their recommendations.

## Relevance, faithfulness, security and speed

Relevance was graded 0 to 2 on a blind sheet of 686 pairs over 40 queries by **language-model judges, not humans** (@tab:relevance). The full system has the highest mean grade, so verification did not cost relevance. A repeat pass by different judges over 266 pairs agreed on 92.1% of grades (Cohen's kappa [@cohen1960] 0.874 unweighted, 0.945 quadratic-weighted); this shows consistent judging, not agreement with humans.

::: table relevance size=8.5 cols=3.4,1.3,1.6,1.5,2.4,2.2
Relevance at five (judged by language models, blind).
| System | Queries | Models graded | Mean grade | Queries with a grade-2 model | Models graded 1 or 2 |
|:--|:-:|:-:|:-:|:-:|:-:|
| **Ours** | 38 | 190 | **1.28** | **81.6%** | **76.8%** |
| Keyword + filters | 40 | 197 | 1.06 | 65.0% | 70.1% |
| Naive RAG | 40 | 200 | 0.87 | 67.5% | 51.5% |
| HF Hub, licensed | 40 | 200 | 0.69 | 22.5% | 61.5% |
:::

::: fig chart_relevance w=14
chart_relevance.png
Relevance results from the blind study (language-model judges).
:::

Judges also counted 98 factual claims in 28 explanations: 80 (81.6%) were supported by the shown card text and 14 explanations (50%) were entirely supported, so explanation text is a convenience and not evidence; the verdict tables do not depend on it. With three hostile cards of unknown metadata, tables came from metadata only in 5 of 5 runs and no explanation repeated an injected claim. The Try-it template ran for 20 of 32 small models (MLX, quantised and custom-code models need other tooling). A warm live query took a median of 1.3 s (p95 2.0 s) without the explanation, and 7 to 17 s with it.

## Discussion and limitations

Verification in code removes violations that retrieval alone cannot, without costing relevance, and unknowns are shown instead of guessed. The main limit is the data: where 27% to 30% of sizes, 20% of rights and most translation directions are unknown, no method can verify them, so the 16.7% unknown rate is close to a floor. Other limits: relevance and faithfulness were judged by language models that share a model family with the assistant that helped build the system; one author wrote the queries and built the system; the 100-query evaluation covers the original five tasks and the six added tasks were checked by smoke queries only; the hosted re-ranker's monthly quota is exhausted, so new searches are not re-ranked (verdicts are unaffected); rights are read from *declared* licences and are not legal advice; and the snapshot is a sample of the Hub dated 25 October 2026.
