# Source Code

This chapter lists the parts of the source code that carry the main ideas of the work. The full repository (about 3,600 lines in `src/` and `app.py`, 900 in `eval/`, 700 in `scripts/` and 3,300 in `tests/`) is at <https://github.com/Adityarane012/RAG-Project>. The listings are copied directly from the files named in their captions, with the line ranges shown, so they match the code that produced the results in Chapter 4. Comments in the listings use the decision identifiers (D2, D12, D18 and so on) of the design log in `docs/decisions.md`.

## Repository layout

@tab:modules gives the role of each module. The module boundaries follow the design principle of Chapter 3: everything that decides a verdict is a plain module with no network access (`verify`, `normalize`, `retrieve`, `adapt`, `guide`), and everything that touches the network is injected into the graph through one dependency object so that the graph can be tested with stubs.

::: table modules size=8.5 cols=2.4,6.6,1.2
Modules of the system.
| File | Role | Lines |
|:--|:--|:-:|
| `src/verify.py` | Pass, fail or unknown for each requested constraint; overall verdict; rank key | 123 |
| `src/normalize.py` | Raw Hub record to metadata schema: size rule, licence map, languages, direction | 317 |
| `src/retrieve.py` | Metadata filter, chunk-to-model grouping, widening search | 96 |
| `src/graph.py` | LangGraph query pipeline and routing | 208 |
| `src/llm.py` | Provider access, cache, token throttle, extraction, backstop, explanation, injection defence | 404 |
| `src/evidence.py` | Selection and trimming of card passages for the explanation prompt | 126 |
| `src/guide.py` | Plain-language intent, clarifying questions, relax offers, snippets, out-of-scope check | 223 |
| `src/adapt.py` | Rights notes, lineage, fine-tuning memory estimate, model report | 125 |
| `src/index.py`, `src/embedder.py`, `src/localindex.py` | Chunking, embedding with cache, Pinecone and exact local index | 611 |
| `src/rerank.py`, `src/replay.py` | Hosted and local re-rankers; recorded-run replay | 217 |
| `src/ingest.py`, `src/snapshot.py`, `src/clean.py` | Hub download, snapshot with checksum, card cleaning | 408 |
| `src/baselines.py`, `src/checker.py`, `src/pipeline.py` | BM25 baseline and Hub filters; check-a-model; assembly of the live graph | 209 |
| `app.py` | Streamlit interface | 396 |
| `eval/` | Evaluation harness, metrics, labelling tools, reports | 911 |
| `scripts/` | Pinecone semantics check, poisoned-card test, Try-it smoke test, demo recording and rehearsal | 668 |
| `tests/` | 335 offline tests in 31 files | 3,349 |
:::

## Verification

@lst:verify is the whole verification module. It reads only the metadata dictionary and the constraint dictionary; it has no imports from the language-model or network code.

::: code verify cap="src/verify.py (lines 1 to 123): the single place where pass, fail or unknown is decided." src=src/verify.py lines=1-123
:::

## Normalisation: rights and size

@lst:rights is the licence-to-rights lookup, an unmapped licence giving *unknown* and never a guess. @lst:normalize holds the translation-direction parser, the size rule and the reason a size is unknown. The size rule sums the top-level weight files and returns nothing, not zero, when it cannot be sure.

::: code rights cap="src/normalize.py (lines 130 to 135): licence identifier to rights." src=src/normalize.py lines=130-135
:::

::: code normalize cap="src/normalize.py (lines 200 to 262): translation direction, size rule and the reason a size is unknown." src=src/normalize.py lines=200-262
:::

## Retrieval

@lst:retrieve builds the metadata filter, groups chunks by model and widens the search until enough distinct models are covered. Every clause keeps models whose field is unknown.

::: code retrieve cap="src/retrieve.py (lines 13 to 86): filter with unknowns kept, grouping, widening search." src=src/retrieve.py lines=13-86
:::

## The query graph

@lst:graph is the pipeline of Section 3.6: the state, the dependency object, the two routing functions and the construction of the graph for the full system and for the two baselines.

::: code graph cap="src/graph.py (lines 36 to 208): state, routing and graph construction." src=src/graph.py lines=36-208
:::

## Constraint extraction and the deterministic backstop

@lst:extract validates the language model's output and fills in only what the request plainly states.

::: code extract cap="src/llm.py (lines 248 to 358): validation, instruction guard, backstop and extraction." src=src/llm.py lines=248-358
:::

## Defence against hostile card text, and explanation

@lst:defence wraps card text as data, neutralises delimiters, filters citations and builds the explanation prompt from budgeted passages.

::: code defence cap="src/llm.py (lines 359 to 404): untrusted-text handling and the explanation call." src=src/llm.py lines=359-404
:::

## Token-budget throttle

@lst:throttle is the sliding-window throttle that keeps calls inside the free tier's tokens-per-minute limit (@fig:a_llm).

::: code throttle cap="src/llm.py (lines 133 to 175): sliding-window token budget." src=src/llm.py lines=133-175
:::

## Build-on information

@lst:adapt computes the plain-language rights notes and the fine-tuning memory estimate (@eq:memory).

::: code adapt cap="src/adapt.py (lines 22 to 60): rights notes and memory estimate." src=src/adapt.py lines=22-60
:::

## Evaluation metrics

@lst:metrics defines the automatic metrics (@eq:violation) and Cohen's kappa (@eq:kappa). The same functions score every system.

::: code metrics cap="eval/metrics.py (lines 21 to 64): violation, unknown and clarification rates." src=eval/metrics.py lines=21-64
:::

::: code kappa cap="eval/metrics.py (lines 90 to 119): Cohen's kappa, unweighted and quadratic-weighted." src=eval/metrics.py lines=90-119
:::

## Rendering a result

@lst:render is the function of the interface that renders one run of the graph in every outcome: out of scope, clarify, relax or abstain, and answer with the banner, the verdict tables, the explanations and the Try it and Build on it panels.

::: code render cap="app.py (lines 114 to 181): rendering the outcome of one graph run." src=app.py lines=114-181
:::
