# Data notes (live checks and data-quality report)

Everything in the other docs that says "verify" or "measure" ends up here as a dated line. All measurements are from
**2026-10-21**, run from the cloud session. "Not run" means the check could not be made from there (reason given).

## Live checks

| Check | Result |
|---|---|
| Models per task (`python -m src.ingest counts`) | ASR 3,469 · translation 1,886 · sentence-similarity 1,383 · text-classification 1,617 · token-classification 1,409. **9,764 unique** (D6 estimated 5,000 to 8,000: about 20% more) |
| Hub response shape matches `normalize_record` | Yes: 8 real responses are saved as fixtures (`tests/fixtures/hub/`) and tested. Two real bugs found and fixed: `HfApi.list_models(language=)` does not exist (use `filter=`), and `/raw/main/README.md` returned 403 for some repos and was cached empty (now `/resolve/main/`; non-404 errors raise and are logged) |
| Fetch | 9,763 of 9,764 cards fetched; 1 logged failure (a transient proxy error on `RGalliennePeren/Voxtral-rg`) |
| Canonical base-model ids | 1,513 distinct base ids; 71 resolved to a different current id (legacy ids merged) |
| Pinecone control plane and hosted inference | Work: index created, hosted embeddings (`multilingual-e5-large`, 1,024 dimensions) and hosted rerank (`bge-reranker-v2-m3`, API version `2024-10`; `2024-07` returns 404) |
| Pinecone data plane (upsert/query), `$or`/`$in`/`$and` filter semantics | **Not run**: the host `hf-model-finder-cactjug.svc.aped-4627-b74a.pinecone.io` is blocked by the sandbox. The same filter semantics are implemented and unit-tested in `LocalIndex`; a live comparison is pending (needs the host allowed) |
| Pinecone hosted embedding quota | Not stated by the API. The whole corpus (29,665 chunks) used **2.49M tokens** with no quota error |
| Hosted rerank limits | Pair limit 1,024 tokens: Indic chunks exceeded it and failed the whole request, so the call now sends `parameters.truncate = END` |
| Groq limits | `gpt-oss-20b` and `gpt-oss-120b`: 8,000 tokens/min, 1,000 requests/day, 200,000 tokens/day (from response headers). `llama-3.1-8b-instant` is **not** on the account (fallback is `gpt-oss-120b`) |
| Groq JSON mode / extraction | Both models accept `response_format=json_object`. 20-case extraction set: `gpt-oss-20b` exact match **100%** (0 silent drops); `gpt-oss-120b` **85%** (3 silent drops), which led to the deterministic backstop. After the backstop and 3 added cases (23 total): LLM only 87%, with backstop 100% (a tuning-set number, not a generalisation estimate) |
| Groq token cost (measured) | Extraction about 500 tokens/call; explanation 1,345 tokens for 1 model and 2,778 for 5 models. About 3,300 tokens per fully explained query, so about 60 explained queries per day on the 200K daily budget, and two calls fit inside one minute |
| Reasoning tokens | With default reasoning, extraction cost about 1,150 tokens; `reasoning_effort=low` removed that |
| Latency | Warm query, no explanation: median 1.3 s, p95 2.0 s (local index, hosted embed + rerank). With explanation: 7 to 17 s (the Groq call and the throttle) |
| Poisoned cards | Redesigned test (poisoned cards with unknown metadata so the filter cannot remove them): 5/5 runs, tables come from metadata only, poisoned cards ranked below honest ones, 0/5 explanations repeated the injected claims (`eval/results/poison_test.json`) |
| e5 tokenizer vs `approx_tokens` | Not run (needs the model weights; the HF CDN host is blocked). Hosted embeddings took the place of local ones |
| Local reranker / local embeddings | Not run (HF CDN host `us.aws.cdn.hf.co` is blocked) |
| Try-it smoke test on small models | Not run (needs weight downloads). Snippet templates are covered by unit tests |
| NLLB-200 licence card, `TASK_GUIDES` URLs | Not run |
| Ollama | Not run (no Ollama in the sandbox); the provider code is tested with fakes |

## Data-quality report (snapshot 2026-10-21)

Snapshot: `data/snapshot-2026-10-21/records.jsonl.gz`, sha256 `3c887c9a733c58a4fc64d129c40530299c2ad13eb4113cef9ad2b860b6034160`
(recorded in `config.yaml`). Rebuild with `python -m src.snapshot build`; the build is deterministic.

| Measure | Value |
|---|---|
| Models | 9,764 (ASR 3,469 · translation 1,886 · sentence-similarity 1,383 · text-classification 1,617 · token-classification 1,409) |
| Size unknown | **2,652 (27.2%)**: no weight files 1,158 · GGUF only 924 · weights under another name 210 · weights only in a sub-folder 204 · adapter only 156 |
| Commercial / modifiable unknown | 15.3% each (after extending the license map); rights: yes 7,532 · unknown 1,490 · conditional 378 · no 364 (before the last map extension) |
| Top unmapped licenses | `other` 345 (custom licenses; kept unknown on purpose), `cc` 6, `unknown` 6. Mapped after the report: `openmdw-1.0/1.1`, `afl-3.0`, `pddl`, `llama4`, `lfm1.0`, `nvidia-open-model-license`, `falcon-llm-license`, `lgpl`, `odbl` |
| Language unknown | 12.9% |
| Multilingual (declared) | 7.6% (745 models) |
| Indic-tagged | 53.5% |
| With `base_model` / with parameter count | 51.9% / 51.4% |
| Minimal documentation | 5.8% |
| With `model-index` | 26.6% |
| Directions from the model name | 380 (`opus-mt-<src>-<tgt>`) |
| Language tokens that are not 2 letters | 40, mostly 3-letter codes (`sat`, `mai`, `bho`, `mni`, `brx`, ...) kept as written; Indic names for them were added to the language table |
| Chunks | 29,665 over 9,764 models (3.0 per model) after dropping boilerplate sections and capping at 4 per model |
| Embedding cost | 2.49M hosted tokens, one pass; rebuilds are free (content-hash cache) |

## Decisions triggered by the data

- **27% unknown size** is the largest source of ⚠️. Widening the size rule to ONNX/GGUF/NeMo files is a D20 non-goal; the models stay ⚠️ and the count is reported.
- **Verified models were invisible to semantic search** (direction, size and license are not in the text). Fix: verify 100 models, then show 5 (`retrieval.verify_pool`). Fully verified answers on the normal queries went from 72.3% to 83.3%.
- **Retrieval uses the user's own words**, not the extractor's `soft_query`, after the extractor turned a query into "permissive license".
- **Named permissive licenses** ("Apache", "MIT", "BSD", "permissive") are read as commercial + modifiable. This is an approximation and is shown in "We understood".
- **Only one multilingual map entry family was added** (Qwen3-ASR, Hindi only). Most popular multilingual models already carry language tags, and the cards of `bge-m3` and `embeddinggemma` give no Indic language list to cite, so they are not mapped.
- **Translation direction** is known for only 380 models, so most translation answers show direction ⚠️.
