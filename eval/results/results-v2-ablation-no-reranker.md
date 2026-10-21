# Evaluation results (v2-ablation-no-reranker)

- date 2026-10-21 · git `152cfcb` · config sha256 `9b94abbbe378` · LLM `openai/gpt-oss-20b (reasoning_effort=low)` · vector store `local` · embeddings `pinecone:intfloat/multilingual-e5-large` · reranker `none`
- queries: 100 ({'normal': 75, 'vague': 15, 'impossible': 10}); single author, written before any retrieval experiment (D11 deviation)
- queries whose parsed constraints are empty (violation is trivially 0 for them): 3

## Normal queries (75): recommendations judged with verify()

| System | Answered % | Recs | Violation % | Unknown % | Fully verified % | Median s | p95 s |
|---|---|---|---|---|---|---|---|
| ours | 97.3 | 365 | 0.0 | 16.7 | 83.3 | 0.19 | 0.29 |

### Violations by constraint (% of recommended models failing that constraint)

| System | commercial | direction | languages | modifiable | size | task |
|---|---|---|---|---|---|---|
| ours | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

### By task and language group (violation % / answered %)

- **ours**: automatic-speech-recognition: 0.0/100.0 · none: None/0.0 · sentence-similarity: 0.0/100.0 · text-classification: 0.0/100.0 · token-classification: 0.0/100.0 · translation: 0.0/93.3 · indic: 0.0/100.0 · non_indic: 0.0/85.7

## Behaviour of the full system

- vague queries (15): asked a clarifying question on **100.0%**; outcomes {'clarify': 15}
- impossible queries (10): abstained or offered a relaxation on **0.0%**; shown with the 'no model fully verified' banner on 70.0%; shown as fully verified on 30.0%; outcomes {'answer': 10}

### Impossible queries: models in the corpus that could answer them

| query | full pass | not failing (pass or unknown) |
|---|---|---|
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

0/10 are verifiably impossible (no model passes or is unknown).

### Queries with no fully verified model in the corpus (12): false assurance and violations

| System | answered % | violation % | unknown % | claimed fully verified | shown with banner | abstained / relaxed |
|---|---|---|---|---|---|---|
| ours | 100.0 | 0.0 | 100.0 | 0 | 12 | 0 |

## Vague and impossible queries: baselines (they never ask or abstain)

- vague · ours: answered 0.0%, violation None%, unknown None%
- impossible · ours: answered 100.0%, violation 0.0%, unknown 78.0%
