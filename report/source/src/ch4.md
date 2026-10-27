# Snapshots of the Project, Results and Discussion

This chapter shows the working application and then presents the measurements. Section 4.1 walks through screenshots of the interface. Sections 4.2 to 4.7 report the results of the evaluation described in Section 3.10, and Section 4.8 discusses what they show and what they do not. Every number in the tables comes from the result files stored in the repository; **relevance and faithfulness figures were produced by language-model judges and not by human annotators**, and are labelled as such.

## Application snapshots

The screenshots were captured from the running Streamlit application. Where the live services were not needed, the application was run in *replay* mode, which serves recorded runs from disk and says so on the page ("Replay mode: showing recorded runs, no live services"); the recordings were made against the live index and models. In the tables, a pass is shown as plain text, a failure with a red cross and an unknown with a warning sign.

### Start page

@fig:ui_start shows the start page: the data-snapshot date, five example queries covering different tasks and languages, the search box and the switch that adds the naive-RAG comparison. A disclaimer under the title states that rights are read from the declared licence and are not legal advice (FR-1, NFR-4).

::: fig ui_start w=10
ui_start.png
Start page with example queries, the search box and the comparison switch.
:::

### Verified results against naive RAG

@fig:ui_compare shows the request "Small sentiment model for Hindi I can use in a commercial app" with the comparison switched on. The sentence "We understood" shows that "small" was read as 500 MB. The left column is the full system and the right column is naive RAG running on the same index, with no filters and no checks. Every row on the left passes. On the right, naive RAG recommends models with a red cross for size: they sound relevant but are larger than the limit the user implied. The caption at the end of the right-hand column counts the failures (four of five in this run).

::: fig ui_compare w=12
ui_compare.png
Side-by-side comparison for a small Hindi sentiment model under a commercial licence (first three results of each column shown).
:::

### Clarifying questions

For the request "I want a Hindi model", the system does not guess. @fig:ui_clarify shows the reading ("a model, we are not sure what for yet, for Hindi") and the question "What should the model do?" with one button per task. Choosing "Detect sentiment / classify text" re-runs the graph with that answer as an override and produces the results of @fig:ui_after. Every vague query in the evaluation behaved this way.

::: fig ui_clarify w=10.5
ui_clarify.png
A vague request ("I want a Hindi model") is answered with a question, not a guess.
:::

::: fig ui_after w=10.5
ui_after_clarify.png
Results after the user chose "Detect sentiment / classify text".
:::

### Honest unknowns and the banner

@fig:ui_banner shows the request "Hindi to Marathi translation under 1 MB". No model can be verified: size and direction are unknown for every candidate, so the page shows the banner "No model fully verified: every result below has at least one unknown", and each row carries a warning sign. The system does not claim a pass it cannot prove, and it does not discard the candidates either. In @fig:ui_direction, for "Urdu to English translation I can use in a product", the top results pass the direction check because the model *name* states it (`opus-mt-ur-en`), and the note "direction from model name" makes the source of the verdict visible; other models in the same list remain unknown.

::: fig ui_banner w=11.5
ui_banner.png
The banner "No model fully verified" when every candidate has an unknown, for a request no model can fully satisfy.
:::

::: fig ui_direction w=11.5
ui_direction.png
Translation direction known from the model name, and flagged as such.
:::

### Trying a model and building on it

Under each model, two panels give the next step. **Try it** shows a starter snippet built from a fixed template and says in plain words that it is a standard template that has not been tested on that model. **Build on it** shows the modification right, lineage ("fine-tune of X; N other fine-tunes in our snapshot"), the estimated GPU memory for inference, LoRA and full fine-tuning against a free 16 GB GPU, and a link to the official fine-tuning guide for the task (@fig:ui_buildon). When the parameter count is not known the panel says that no memory estimate is possible.

::: fig ui_buildon w=10
ui_buildon.png
The Try it and Build on it panels for a Tamil named-entity model that the user wants to modify.
:::

### Coverage beyond language models

@fig:ui_vision shows an image-classification request answered with models that pass the task and commercial-use checks, and @fig:ui_summ a summarization request. Both were added when the scope was extended to eleven tasks. An image request is no longer read as a text task: before the extension, "image classifier" was parsed as text classification and returned text models marked as passing the task check. Requests that the index cannot serve, such as "Text to image diffusion model", are refused with a message and no models (@fig:ui_scope).

::: fig ui_vision w=10.5
ui_vision.png
Image classification with a commercial-use requirement: vision models are verified in the same way.
:::

::: fig ui_summ w=10.5
ui_summ.png
Summarization with a commercial-use requirement.
:::

::: fig ui_scope w=12
ui_scope.png
An out-of-scope request is refused, with nothing shown rather than a model for a different task.
:::

### Editing the reading, glossary, examples and check-a-model

Any field of the reading can be edited and the search repeated (@fig:ui_edit); a glossary defines licence, commercial, modifiable, NER, parameters, size, LoRA and unknown in plain words; and the Examples tab offers more than 25 queries grouped by task (@fig:ui_examples). The Check a model tab (@fig:ui_check) looks a model up in the snapshot, shows its facts (task, languages, size, parameters, rights, base model, documentation) and optionally checks it against requirements, which serves a reviewer who wants to know whether a model already in use is acceptable.

::: fig ui_edit w=10
ui_edit.png
The editable reading ("Edit what we understood") and the glossary.
:::

::: fig ui_examples w=10
ui_examples.png
The Examples tab: more than 25 queries grouped by task.
:::

::: fig ui_check w=10
ui_check.png
Check-a-model mode for a model in the snapshot.
:::

## Corpus statistics

The index covers 15,991 models over eleven tasks (@fig:chart_corpus). The proportion of models whose size cannot be determined varies strongly by task: 6% for image classification, where weights follow the standard file names, but 75% for object detection, where many repositories keep weights in sub-folders or in formats the size rule does not count. @tab:quality gives the data-quality figures for the whole snapshot and for the original five tasks on which the evaluation was run.

::: fig chart_corpus w=14
chart_corpus.png
Models per task in the snapshot, split by whether the size is known.
:::

::: table quality size=9 cols=4.4,2,2
Data-quality figures of the snapshot (percentages of models).
| Measure | All 11 tasks (15,991) | Original 5 tasks (9,764) |
|:--|:-:|:-:|
| Size unknown | 29.5% | 27.2% |
| Commercial and modifiable right unknown | 20.1% | 15.3% |
| Commercial use *yes* / *conditional* / *no* | 70.3% / 6.5% / 3.2% | – |
| Language status unknown | 32.4% (mostly vision, where language does not apply) | 12.9% |
| Declared multilingual | 4.9% | 7.6% |
| Documentation minimal | 6.5% | 5.8% |
| Base model declared | 47.5% | 51.9% |
| Parameter count available | 50.6% | 51.4% |
| Author-reported evaluation results (`model-index`) | 23.8% | 26.6% |
| Translation direction stated by the model name | 380 models | 380 models |
:::

## Constraint extraction

Extraction was tested on a set of hand-written requests with the expected constraint record, scored by exact match, and by the number of *silent drops* (a requested constraint that the extractor omitted, which would make a violation rate look better than it is). @tab:extraction shows the effect of the deterministic backstop. These are tuning-set figures, used to choose the model and to design the backstop, and they are not an estimate of how well the extractor generalises.

::: table extraction size=9.5 cols=4.4,2,2,2
Constraint-extraction accuracy on the tuning sets.
| Configuration | Cases | Exact match | Silent drops |
|:--|:-:|:-:|:-:|
| `gpt-oss-20b` alone | 20 | 100% | 0 |
| `gpt-oss-120b` (fallback model) alone | 20 | 85% | 3 |
| `gpt-oss-20b` alone, after three cases were added | 23 | 87% | – |
| `gpt-oss-20b` alone, after six cases for the new tasks | 29 | 90% | 5 |
| `gpt-oss-20b` with the deterministic backstop | 29 | 100% | 0 |
:::

Re-parsing all 100 evaluation queries with the final prompt and backstop changed only seven parses, all intended (six for the permissive-licence rule and one for a language name), and when the prompt later gained hints for the six new tasks, four parses changed again (for example "not too big" now reads as a small model). The evaluation therefore uses the *pinned* parses of the frozen run, so later prompt changes cannot move its results.

## Comparison with the baselines on normal queries

@tab:main gives the main result on the 75 normal queries. A *recommendation* is one of the top five models returned for a query; 365 to 375 recommendations were made by each system. The verdict of every recommendation was computed by the same verification rules.

::: table main size=9 cols=3.6,1.5,1.2,1.5,1.5,1.7,1.3,1.3
Main results on the 75 normal queries (top five per query, one set of rules for all systems).
| System | Answered % | Recs | Violation % | Unknown % | Fully verified % | Median s | p95 s |
|:--|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| **Ours (constraint-verified RAG)** | 97.3 | 365 | **0.0** | 16.7 | **83.3** | 0.22 | 0.36 |
| Naive RAG | 100.0 | 375 | 50.4 | 20.5 | 29.1 | 0.07 | 0.64 |
| Keyword (BM25) + filters | 100.0 | 368 | 0.0 | 62.0 | 38.0 | 0.05 | 0.08 |
| HF Hub, basic filters | 100.0 | 375 | 32.8 | 13.6 | 53.6 | 0.10 | 0.15 |
| HF Hub, licensed filters | 100.0 | 375 | 25.9 | 14.7 | 59.5 | 0.09 | 0.14 |
:::

::: fig chart_main w=14
chart_main.png
Share of recommended models that are fully verified, unknown or violating, by system.
:::

The full system recommended no model that fails a requested constraint, and 83.3% of its recommendations were verified on every requested constraint, against 29.1% for naive RAG and 59.5% for the best Hub filter. It answered 73 of 75 queries: on the other two (a request naming no single language and a request for language identification, for which no task is mapped) it asked a clarifying question. The latencies in @tab:main are for replayed, cached runs and are discussed in Section 4.7.

@fig:chart_violations shows *which* constraints the baselines break. Naive RAG fails the size limit on half of its recommendations, returns a model for the wrong task on 24.1% (for example speech-recognition models for a text request) and in the wrong language on 19.4%. The Hub filters never return the wrong task or language because those are the filters they have, but they cannot filter by size, since the Hub has no size filter, and fail it on 80.0% (basic) and 71.9% (licensed) of recommendations. The licensed variant removes commercial-use failures completely because it filters on one permissive licence string, which also excludes every model under other permissive licences (MIT, BSD, CC-BY-4.0), a loss of recall that the violation rate does not show. Keyword search with the same filters never violates a requested constraint, because the filters are the same as ours, but 62% of its recommendations are unknown: BM25 matches words in card text, which say nothing about size or licence, so it surfaces unknown-metadata models that merely contain the right words, and nothing ranks verified models first.

::: fig chart_violations w=13.5
chart_violations.png
Recommendations that fail each constraint, by baseline. Ours and keyword search: 0.0 on every constraint.
:::

@tab:bytask breaks the violation rate down by task. Naive RAG and the Hub filters fail on every task, with rates between 16.0% and 62.7%. For the full system the violation rate is 0.0% on every task, and it answered 100% of the queries on each task except translation (93.3%), where the one query that asked for "Indian languages" without naming one was answered with a question.

::: table bytask size=9.5 cols=3.4,1.6,1.6,1.8,1.8
Violation rate (%) by task.
| Task | Ours | Naive RAG | HF basic | HF licensed |
|:--|:-:|:-:|:-:|:-:|
| Speech recognition | 0.0 | 34.7 | 38.7 | 28.0 |
| Translation | 0.0 | 45.3 | 45.3 | 30.7 |
| Sentence similarity | 0.0 | 53.3 | 16.0 | 16.0 |
| Text classification | 0.0 | 60.0 | 35.7 | 32.9 |
| Token classification | 0.0 | 62.7 | 30.7 | 24.0 |
| Indic-language queries | 0.0 | 52.8 | 32.5 | 24.9 |
| Non-Indic queries | 0.0 | 40.0 | 34.3 | 30.0 |
:::

The effect of the verify pool is itself a result. With a pool of 25 models, the first version of the system recommended 72.3% fully verified models; with the pool of 100 it recommended 83.3%. The translation queries are the clearest case: before the change, six queries had no fully verified model in their top five although a model such as `Helsinki-NLP/opus-mt-en-hi` existed in the corpus. The comparison against the Pinecone index and the exact local index gave the same aggregates for ours, naive RAG and keyword search; the top-five lists were identical on 72 of 100 queries for ours and for naive RAG and on all 100 for keyword search, the differences being ties and approximate-search ordering.

## Vague queries, impossible queries and the no-verified slice

**Vague queries.** On the 15 beginner requests the full system asked a clarifying question on 100%. The baselines have no such behaviour and answered all of them, with unverified models (violation rates of 5.3% for naive RAG and both Hub variants, and 16.0% unknown for keyword search).

**Impossible queries.** Ten requests were written to be impossible (for example "Marathi speech recognition under 10 MB" or "Santali speech recognition model"). Because a model with unknown size or language can never fail a constraint, none of the ten could be proved impossible: every one left at least 31 models that were not failing (@tab:impossible). The abstain and relax paths therefore never fired and the system answered all ten. For three of the ten it showed at least one fully verified model; the corpus holds at least one fully passing model for five of the ten (up to 33 for q099), so those requests were not impossible after all, and for the remaining seven the system showed unknown models with the banner.

::: table impossible size=9 cols=1.5,2,3
Models in the corpus that could answer each intended-impossible query.
| Query | Fully pass | Not failing (pass or unknown) |
|:--|:-:|:-:|
| q091 | 7 | 360 |
| q092 | 0 | 105 |
| q093 | 0 | 284 |
| q094 | 1 | 127 |
| q095 | 0 | 117 |
| q096 | 7 | 342 |
| q097 | 0 | 31 |
| q098 | 0 | 308 |
| q099 | 33 | 319 |
| q100 | 6 | 192 |
:::

**The no-verified slice.** Because the original abstention metric could not be satisfied, the measure was redefined on the 12 queries (normal and impossible) for which no model in the corpus fully passes. On this slice the right behaviour is *not to claim verification*. @fig:chart_noverified shows that the full system and keyword search recommended only unknown models (no violation), and showed the banner on all 12 queries and claimed full verification on none; naive RAG and the Hub filters recommended violating models for 63.3% to 75.0% of their recommendations and do not warn the user.

::: fig chart_noverified w=14
chart_noverified.png
Recommendations on the 12 queries for which no model in the corpus fully passes.
:::

## Relevance

Not violating a constraint is necessary, but a recommendation must also suit the purpose. @tab:relevance and @fig:chart_relevance give the blind relevance study. The sheet had 686 pairs over 40 queries, made of the union of the top-five models of ours, naive RAG, keyword search and the licensed Hub baseline. **The grades were produced by independent language-model judges, not humans.** The full system covers 38 queries because it asked a clarifying question on two of the 40.

::: table relevance size=9.5 cols=3,1.4,1.7,1.8,2.2,2.2
Relevance at five, graded 0 to 2 by language-model judges (blind).
| System | Queries | Models graded | Mean grade | Queries with a grade-2 model | Models graded 1 or 2 |
|:--|:-:|:-:|:-:|:-:|:-:|
| **Ours** | 38 | 190 | **1.28** | **81.6%** | **76.8%** |
| Keyword + filters | 40 | 197 | 1.06 | 65.0% | 70.1% |
| Naive RAG | 40 | 200 | 0.87 | 67.5% | 51.5% |
| HF Hub, licensed filters | 40 | 200 | 0.69 | 22.5% | 61.5% |
:::

::: fig chart_relevance w=14.5
chart_relevance.png
Relevance results from the blind study (language-model judges).
:::

The full system has the highest mean grade and the highest share of useful models, so verification did not cost relevance: filtering on facts removed unsuitable candidates and the verify-wide design kept the relevant ones. Naive RAG retrieves topically related models (67.5% of its queries have a grade-2 model, close to keyword search) but half of those fail a constraint, and its share of useful models is lowest among the semantic systems. The licensed Hub filter performs worst on relevance because the Hub orders by downloads and cannot express the soft part of a request.

**Agreement.** A repeat pass by three different judges graded 15 of the queries (266 pairs) from scratch, without seeing the first pass. The two passes gave an identical grade on 92.1% of the pairs, Cohen's kappa [@cohen1960] was **0.874** (unweighted) and **0.945** (quadratic-weighted), and there were no disagreements between a grade of 0 and a grade of 2. In the bands of Landis and Koch [@landis1977], both values are "almost perfect". This measures the consistency of language-model judging; it is not agreement between independent humans and it says nothing about agreement with humans. The judges share a model family with the assistant that helped to build the system, so shared blind spots are possible, and a human spot check on a sample (for example one query per task) is the recommended strengthening.

## Explanations, security, usability and performance

**Faithfulness of explanations.** Two judges counted the factual claims in 28 explanations (one explained model per query, chosen at random) and how many of them the card passages shown to the model support. Of 98 claims, 80 (81.6%) were supported, and 14 of 28 explanations (50.0%) had every claim supported. The unsupported claims were mostly statements the passages do not make: that a model is suitable for commercial use or fits a size limit (these come from the request, not the card), that a generic multilingual model supports a named language, and in one case a wrong translation direction. The verdict tables are built from metadata, not from the explanation, so these errors do not change a verdict, but they confirm the design rule that explanation text must not be used as a source of constraint facts (and the explanation prompt now forbids stating them).

**Poisoned cards.** With three hostile cards in a separate namespace and with deliberately unknown metadata, verdict tables came from metadata only in 5 of 5 runs, hostile cards ranked below honest ones, citations to identifiers outside the candidate set were dropped, and 0 of 5 explanations repeated an injected claim for each hostile card.

**Try-it snippets.** The snippet template was run on 32 small models, with the Transformers library plus the image libraries (@fig:chart_tryit). Twenty ran: all three of the image-classification, text-generation, question-answering and token-classification models, two of three object-detection, image-segmentation and summarization models, one of three text-classification and sentence-similarity models, and none of the translation and speech-recognition models. The failures were MLX or 4-bit quantised weights, a corrupt weights file, custom code, a missing tokenizer package, and decoder-only models used as translation pipelines. The interface therefore says that the snippet is a standard template, suitable for ordinary Hugging Face weights, and not tested on the model shown.

::: fig chart_tryit w=13
chart_tryit.png
Try-it smoke test: small models for which the generated snippet ran, by task.
:::

**Latency.** @tab:latency gives the timings. The evaluation timings are for cached embeddings, re-ranking and language-model calls, so they measure the code path and not the network. A live query with warm caches took a median of 1.3 s and a 95th percentile of 2.0 s without the explanation, which meets NFR-3; the explanation adds 7 to 17 s because of the language-model call and the throttle that keeps the call inside the free token limit. Removing the re-ranker leaves every verification metric unchanged (violation 0.0%, unknown 16.7%, fully verified 83.3%), because verification, not ordering, decides the verdicts; its effect on *relevance* was not measured, since the ablation outputs are not in the graded sheet.

::: table latency size=9 cols=5,3
Latency of the pipeline.
| Measurement | Value |
|:--|:--|
| Live query, warm caches, no explanation (hosted embedding and re-ranking, local index) | median 1.3 s, p95 2.0 s |
| Live query with explanation | 7 to 17 s |
| Evaluation harness, cached runs: ours | median 0.22 s, p95 0.36 s |
| Evaluation harness, cached runs, ours without the re-ranker | median 0.19 s, p95 0.29 s |
| Evaluation harness, cached runs: naive, keyword, Hub basic, Hub licensed | median 0.07, 0.05, 0.10, 0.09 s |
| Local re-ranker fallback (CPU, 40 chunks) | about 20 s per query |
| Replay mode | no network; effectively instant |
:::

**Scope extension.** The six tasks added on 25 October are not part of the 100-query evaluation. They were checked in three ways: smoke queries (for example "object detection model for traffic cameras", where the unranked results were thermal, drone and stamp detectors and the re-ranked results were YOLO and VisDrone vehicle detectors and a traffic-accident detector), the Try-it smoke test above, and a regression check showing that the frozen evaluation is reproduced exactly on the five-task corpus and that ours is unchanged on the full index (the task filter excludes the new models), whereas naive RAG changed on 68 queries and keyword search on 46, because they have no task filter.

## Discussion

**Does verification reduce violations?** Yes, and by construction: on the 75 normal queries the full system recommended no failing model, against 50.4% for naive RAG and 25.9% to 32.8% for the Hub filters. The more informative number is the share of *fully verified* recommendations (83.3%), because it shows what the user can rely on without reading anything. The remaining 16.7% are unknown, not wrong, and they are marked.

**Does it cost relevance?** No evidence of a cost was found. In the judged study the full system had the highest mean grade (1.28) and the highest share of queries with a clearly suitable model (81.6%). The explanation is that retrieval and verification do different jobs: retrieval ranks by meaning, verification removes what cannot suit, and verifying a wider pool than is shown means the removal does not empty the list.

**Does it ask and abstain when it should?** It asked on all 15 vague queries, and it never claimed verification when no model fully passes. It did not abstain, because abstention requires a known failure for every candidate and the corpus always contains unknown-metadata models; the honest behaviour on this data is to show the unknowns with a banner, which is also what the user chose.

**Are explanations grounded?** Mostly: 81.6% of claims are supported, but only half of the explanations are entirely supported, so the text should be read as a convenience and not as evidence. Safety-relevant facts come from the table.

**Is it better than the Hub's filters?** On constraint satisfaction, yes: the best Hub variant violated a requested constraint for 25.9% of recommendations, mostly size, which the Hub cannot filter. On relevance the licensed Hub variant graded lowest. The Hub is better in one respect, coverage: it searches over a million models and this system searches a sample of 15,991.

**What limits the result?** The main limit is the metadata itself. Where 27% to 30% of models have no determinable size, no method can verify a size limit for them; the system can only say so. The same holds for the 20% of models with no usable licence and, for translation, the direction of all but 380 models. The unknown rate of 16.7% is therefore close to a floor for this data and this set of queries, not a failure of the method.

## Threats to validity and limitations

@tab:limits lists the limits of the evidence and of the system. They are repeated here because they affect how far the results can be trusted.

::: table limits size=8.5 cols=3,7
Threats to validity and known limitations.
| Limit | Detail |
|:--|:--|
| Language-model judges | Relevance and faithfulness grades come from independent language-model agents, not humans; they share a model family with the assistant that helped build the system; the agreement figures are between two language-model passes |
| One author | The same person wrote the 100 queries and built the system; there are no classmate queries; mitigations are committing the queries before tuning, freezing outputs before grading and listing debugging queries (@tab:seen) |
| Evaluation covers five tasks | The 100 queries cover the original five tasks; the six added tasks were checked by smoke queries, the Try-it test and a regression check |
| Declared metadata | Verdicts are only as accurate as the declared metadata; the system cannot detect a false card or a wrong licence, and says rights are not legal advice |
| A sample of the Hub | 15,991 models, as of 25 October 2026, not the Hub |
| Unknown size, language and direction | 29.5% of sizes, 20.1% of rights and most translation directions are unknown and shown as such |
| Abstain and relax unreachable | Models with unknown fields never fail, so these paths are tested but do not fire on this corpus |
| Re-ranker quota | The hosted re-ranker's monthly quota is exhausted; uncached searches are not re-ranked (the page says so) |
| Permissive-licence approximation | "Apache", "MIT" or "permissive" in a request becomes commercial and modifiable; there is no constraint on the licence identifier itself |
| Try-it | Ran on 20 of 32 small models; MLX, GGUF and custom-code models need other tooling |
| Memory estimates | Lower bounds that exclude activations |
| Small sample of relevance | 40 queries, 686 pairs; differences of a few points are noise |
:::

::: table seen size=8.5 cols=2.4,5,4
Evaluation queries inspected while debugging, and what changed.
| Queries | What was looked at | Change it led to |
|:--|:--|:--|
| q016, q017, q018, q020, q025, q043 | Translation queries had no fully verified model although one existed | Verify pool widened from 25 to 100 models |
| q099, q100 | Santali was not a known language name, so the constraint was dropped | Indic language names added to the language table |
| q004, q038, q050, q066, q093 | A named permissive licence never became a constraint | Permissive-licence rule in the backstop, with three new extraction cases written in different words |
| q021 | Its parse changed when the permissive-licence rule was added | None beyond that rule |
| q046 | Candidate pool inspected for a Marathi NER example: relevant models are over the size limit and correctly fail | None |
| q024, q045 | Read only: both ask a clarifying question | None; reported as limitations |
:::
