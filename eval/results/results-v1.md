# Evaluation results (v1)

- date 2026-10-21 · git `e007ed9` · config sha256 `b353b243fc87` · LLM `openai/gpt-oss-20b (reasoning_effort=low)` · vector store `local` · embeddings `pinecone:intfloat/multilingual-e5-large` · reranker `pinecone`
- queries: 100 ({'normal': 75, 'vague': 15, 'impossible': 10}); single author, written before any retrieval experiment (D11 deviation)
- queries whose parsed constraints are empty (violation is trivially 0 for them): 3

## Normal queries (75): recommendations judged with verify()

| System | Answered % | Recs | Violation % | Unknown % | Fully verified % | Median s | p95 s |
|---|---|---|---|---|---|---|---|
| ours | 97.3 | 365 | 0.0 | 27.7 | 72.3 | 1.35 | 1.77 |
| naive | 100.0 | 375 | 50.4 | 19.7 | 29.9 | 1.79 | 2.21 |
| keyword | 100.0 | 368 | 0.0 | 61.4 | 38.6 | 0.04 | 0.07 |
| hf_basic | 100.0 | 375 | 32.5 | 13.3 | 54.1 | 0.09 | 0.17 |
| hf_licensed | 100.0 | 375 | 26.4 | 14.1 | 59.5 | 0.09 | 0.12 |

### Violations by constraint (% of recommended models failing that constraint)

| System | commercial | direction | languages | modifiable | size | task |
|---|---|---|---|---|---|---|
| ours | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| naive | 3.8 | 0.0 | 19.4 | 0.0 | 50.4 | 24.1 |
| keyword | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| hf_basic | 14.6 | 0.0 | 0.0 | 0.0 | 80.0 | 0.0 |
| hf_licensed | 0.0 | 0.0 | 0.0 | 0.0 | 73.3 | 0.0 |

### By task and language group (violation % / answered %)

- **ours**: automatic-speech-recognition: 0.0/100.0 · none: None/0.0 · sentence-similarity: 0.0/100.0 · text-classification: 0.0/100.0 · token-classification: 0.0/100.0 · translation: 0.0/93.3 · indic: 0.0/100.0 · non_indic: 0.0/85.7
- **naive**: automatic-speech-recognition: 34.7/100.0 · none: 0.0/100.0 · sentence-similarity: 53.3/100.0 · text-classification: 60.0/100.0 · token-classification: 62.7/100.0 · translation: 45.3/100.0 · indic: 52.8/100.0 · non_indic: 40.0/100.0
- **keyword**: automatic-speech-recognition: 0.0/100.0 · none: 0.0/100.0 · sentence-similarity: 0.0/100.0 · text-classification: 0.0/100.0 · token-classification: 0.0/100.0 · translation: 0.0/100.0 · indic: 0.0/100.0 · non_indic: 0.0/100.0
- **hf_basic**: automatic-speech-recognition: 37.3/100.0 · none: 0.0/100.0 · sentence-similarity: 16.0/100.0 · text-classification: 35.7/100.0 · token-classification: 30.7/100.0 · translation: 45.3/100.0 · indic: 32.1/100.0 · non_indic: 34.3/100.0
- **hf_licensed**: automatic-speech-recognition: 28.0/100.0 · none: 0.0/100.0 · sentence-similarity: 16.0/100.0 · text-classification: 35.7/100.0 · token-classification: 24.0/100.0 · translation: 30.7/100.0 · indic: 25.6/100.0 · non_indic: 30.0/100.0

## Behaviour of the full system

- vague queries (15): asked a clarifying question on **100.0%**; outcomes {'clarify': 15}
- impossible queries (10): abstained or offered a relaxation on **0.0%**; shown with the 'no model fully verified' banner on 90.0%; shown as fully verified on 10.0%; outcomes {'answer': 10}

### Impossible queries: models in the corpus that could answer them

| query | full pass | not failing (pass or unknown) |
|---|---|---|
| q091 | 7 | 360 |
| q092 | 0 | 105 |
| q093 | 0 | 302 |
| q094 | 1 | 127 |
| q095 | 0 | 117 |
| q096 | 7 | 342 |
| q097 | 0 | 31 |
| q098 | 0 | 308 |
| q099 | 3469 | 3469 |
| q100 | 6 | 192 |

0/10 are verifiably impossible (no model passes or is unknown).

## Vague and impossible queries: baselines (they never ask or abstain)

- vague · ours: answered 0.0%, violation None%, unknown None%
- vague · naive: answered 100.0%, violation 5.3%, unknown 12.0%
- vague · keyword: answered 100.0%, violation 0.0%, unknown 16.0%
- vague · hf_basic: answered 100.0%, violation 5.3%, unknown 0.0%
- vague · hf_licensed: answered 100.0%, violation 5.3%, unknown 0.0%
- impossible · ours: answered 100.0%, violation 0.0%, unknown 90.0%
- impossible · naive: answered 100.0%, violation 80.0%, unknown 10.0%
- impossible · keyword: answered 100.0%, violation 0.0%, unknown 90.0%
- impossible · hf_basic: answered 100.0%, violation 80.0%, unknown 0.0%
- impossible · hf_licensed: answered 100.0%, violation 70.0%, unknown 10.0%
