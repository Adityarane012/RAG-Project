# Data notes (live checks and data-quality report)

Fill this in during Phase 1 and Phase 2 of the [implementation plan](implementation-plan.md). Everything in the other docs that says "verify" or
"measure" should end up as a dated line here, with the command that produced it.

## Live checks (Phase 1)

| Date | Check | Result | By |
|---|---|---|---|
| | Models per task (`python -m src.ingest counts`) | | |
| | Total unique models vs the 5–8k estimate | | |
| | Hub response shape matches `normalize_record` (5 fixtures) | | |
| | Pinecone `$or` with a missing field (10-vector index) | | |
| | Pinecone `$in` on a list field; `$and` of `$or`s | | |
| | Pinecone Starter: inference token limit; hosted reranking available? | | |
| | Groq: JSON parse rate / extraction accuracy (20 queries); rate limits | | |
| | Ollama: same test; latency on a team laptop | | |
| | NLLB-200 license on its card | | |
| | Hub returns `FacebookAI/xlm-roberta-base` as the canonical id for `xlm-roberta-base` | | |
| | `directions_from_name` vs 3 real `opus-mt-*` cards and one fine-tune | | |
| | Groq `openai/gpt-oss-20b` accepts `response_format=json_object`; fallback model works | | |
| | The five `TASK_GUIDES` URLs open | | |
| | e5 tokenizer vs `approx_tokens` on 50 Indic cards | | |
| | Embedding throughput (CPU / Colab GPU) | | |

## Data-quality report (Phase 2)

Snapshot date: ____

| Measure | Value |
|---|---|
| Models per task | |
| Total unique | |
| % size unknown, and the count per reason | |
| % commercial unknown / % modifiable unknown | |
| Top unmapped licenses | |
| % language unknown; unrecognised language spellings | |
| % multilingual | |
| % with base_model / % with param_count | |
| % doc_quality minimal | |
| % with model-index | |
| Failed fetches | |

## Decisions triggered by the data

(e.g. "base_model coverage 9%: lineage dropped from the demo", "adapter-only repos are 4%: widened the weight-name rule".)
