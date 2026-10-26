# Evaluation results (v2-extended)

- date 2026-10-25 · git `148963b` · config sha256 `e039ccae0b0c` · LLM `openai/gpt-oss-20b (reasoning_effort=low)` · vector store `local` · embeddings `pinecone:intfloat/multilingual-e5-large` · reranker `pinecone`
- queries: 100 ({'normal': 75, 'vague': 15, 'impossible': 10}); single author, written before any retrieval experiment (D11 deviation)
- queries whose parsed constraints are empty (violation is trivially 0 for them): 3

## Normal queries (75): recommendations judged with verify()

| System | Answered % | Recs | Violation % | Unknown % | Fully verified % | Median s | p95 s |
|---|---|---|---|---|---|---|---|
| ours | 97.3 | 365 | 0.0 | 16.7 | 83.3 | 0.21 | 0.33 |
| naive | 100.0 | 375 | 56.5 | 16.0 | 27.5 | 0.55 | 1.36 |
| keyword | 100.0 | 368 | 0.0 | 59.5 | 40.5 | 0.06 | 0.11 |

### Violations by constraint (% of recommended models failing that constraint)

| System | commercial | direction | languages | modifiable | size | task |
|---|---|---|---|---|---|---|
| ours | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| naive | 4.0 | 0.0 | 22.5 | 0.0 | 43.7 | 30.3 |
| keyword | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

### By task and language group (violation % / answered %)

- **ours**: automatic-speech-recognition: 0.0/100.0 · none: None/0.0 · sentence-similarity: 0.0/100.0 · text-classification: 0.0/100.0 · token-classification: 0.0/100.0 · translation: 0.0/93.3 · indic: 0.0/100.0 · non_indic: 0.0/85.7
- **naive**: automatic-speech-recognition: 46.7/100.0 · none: 0.0/100.0 · sentence-similarity: 60.0/100.0 · text-classification: 55.7/100.0 · token-classification: 70.7/100.0 · translation: 53.3/100.0 · indic: 58.7/100.0 · non_indic: 47.1/100.0
- **keyword**: automatic-speech-recognition: 0.0/100.0 · none: 0.0/100.0 · sentence-similarity: 0.0/100.0 · text-classification: 0.0/100.0 · token-classification: 0.0/100.0 · translation: 0.0/100.0 · indic: 0.0/100.0 · non_indic: 0.0/100.0

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
| naive | 100.0 | 75.0 | 25.0 | 0 | 12 | 0 |
| keyword | 100.0 | 0.0 | 100.0 | 0 | 12 | 0 |

## Vague and impossible queries: baselines (they never ask or abstain)

- vague · ours: answered 0.0%, violation None%, unknown None%
- vague · naive: answered 100.0%, violation 10.7%, unknown 6.7%
- vague · keyword: answered 100.0%, violation 0.0%, unknown 18.7%
- impossible · ours: answered 100.0%, violation 0.0%, unknown 78.0%
- impossible · naive: answered 100.0%, violation 88.0%, unknown 6.0%
- impossible · keyword: answered 100.0%, violation 0.0%, unknown 94.0%
