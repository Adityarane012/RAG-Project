# Appendix A: Soft Code Flowcharts

This appendix gives flowcharts of the algorithms whose code is listed in Chapter 5. The overall query graph is @fig:graph in Chapter 3 and the data pipeline is @fig:pipeline. In every flowchart, blue boxes are deterministic code, orange boxes are language-model calls, green boxes are the user or interface, and the three outcome colours are those of the verdicts (red for fail, amber for unknown, green for pass).

## Verification of one model

@fig:a_verify shows `verify` and `overall` (@lst:verify). One result is produced for each constraint the user requested, then the results are combined. A requested constraint that cannot be checked yields *unknown*, never *pass*.

::: fig a_verify w=12.5
fig_a_verify.png
Flowchart of `verify`, `overall` and `rank_key`.
:::

## Metadata filter

@fig:a_filter shows `build_filter` (@lst:retrieve). Each requested constraint contributes one clause, and each clause keeps models whose field is unknown, so the filter never decides a verdict.

::: fig a_filter w=13.5
fig_a_filter.png
Flowchart of the metadata filter construction.
:::

## Size rule

@fig:a_size shows the rule that gives a model's size (@lst:normalize). The size is the exact sum of the main weight files, and any doubt makes it unknown.

::: fig a_size w=14
fig_a_size.png
Flowchart of the size rule (D20).
:::

## Constraint extraction

@fig:a_extract shows how a request becomes a validated constraint record (@lst:extract): refusal of out-of-scope requests, the language-model call, schema validation, the deterministic backstop and the user's overrides.

::: fig a_extract w=13.5
fig_a_extract.png
Flowchart of constraint extraction and the deterministic backstop.
:::

## Language-model call with token throttle

@fig:a_llm shows `complete` (@lst:throttle): the cache lookup, the reservation of tokens in the sliding window, the call, and the handling of rate-limit errors with a retry and a fallback model.

::: fig a_llm w=14
fig_a_llm.png
Flowchart of a language-model call with cache, token throttle and fallback.
:::
