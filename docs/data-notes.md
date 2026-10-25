# Data notes (live checks and data-quality report)

Everything in the other docs that says "verify" or "measure" ends up here as a dated line. All measurements are from
**2026-10-21**, run from the cloud session. "Not run" means the check could not be made from there (reason given).

## Scope extension to 11 tasks (2026-10-25)

Added image-classification, object-detection, image-segmentation, text-generation, summarization and question-answering
(`config.yaml: corpus.tasks`). Everything below was measured on 2026-10-25.

| Measure | Result |
|---|---|
| Candidates per task (`python -m src.ingest counts`) | image-classification 1,000 · object-detection 1,000 · image-segmentation 1,000 · text-generation 1,000 (a first attempt that added every Indic-tagged model gave 6,105, so the Indic sample is skipped for text-generation and the vision tasks) · summarization 1,015 · question-answering 1,077 |
| Fetch | 6,092 candidates; 1 logged failure. Fetched with `--tasks` so the original corpus was not re-listed |
| Snapshot | 15,991 records (sha256 `45814b8c7c15f569e2b558e7b0ae56a77f6835223500a69ab8937f2f443b8fa8`, date 2026-10-25). **All 9,764 original records are byte-identical** in the new snapshot |
| Index | 48,179 chunks (15,990 models; one card had no fetched text). Hosted embedding total 4.05M tokens (the extension used 1.56M). Upserted to Pinecone `prod`: `describe_index_stats` = 48,179 vectors |
| Frozen evaluation unchanged | With the five-task corpus restored (`CORPUS_TASKS=five`, namespace `eval5`, parses pinned with `--parsed eval/results/frozen_parses_v2.json`) all 100 queries give the **identical top-5 lists** for ours, naive and keyword as v2 (`eval/results/raw-v2-repro.json`). On the full 11-task index ours is also identical on all 100 queries (the task filter excludes the new models); naive RAG changed on 68 queries and keyword on 46, because naive has no filter and BM25 statistics moved (`raw-v2-extended.json`). The labelled v2 results are therefore for the five-task corpus |
| Extraction prompt drift | The prompt gained six task hints and a rule that generic phrases ("Indian languages") give no language. Re-parsing the 100 evaluation queries changed 4: q045 now `text-classification` (was: ask), q030 "not too big" now small, q063 lost a redundant size word, q085 "build something" now modifiable. q024 and q057 ("covering Indian languages") first became 8 and 12 specific languages; the prompt rule fixed them. q076 ("I want a Hindi model") first became `text-generation`; a deterministic guard now accepts `text-generation` only with a generation cue. All 15 vague queries still ask a question |
| Extraction set | 29 cases (6 new for the new tasks): with the backstop 100% exact match (0 silent drops); LLM alone 90% (5 silent drops, all filled in by the deterministic backstop). Tuning-set figures, not a generalisation estimate |
| Backstop | Image requests no longer become text tasks ("image classifier" is `image-classification`); vision words suppress text-labelling task words |
| Guide links | The six new fine-tuning guide URLs all return 200 |
| Hosted rerank quota | **Reached: 500 requests per month** (495 units used). New queries are not reranked and the UI says so. Local reranker (same model) measured: 103 s to load, 43 s for 100 chunks on a CPU, so it is capped at 40 chunks (about 20 s). For "object detection for traffic cameras" the unreranked top results were thermal, drone and stamp detectors; reranked, they were YOLO and VisDrone vehicle detectors and a traffic-accident detector |
| Try-it smoke, transformers 4.57 + timm + torchvision (`eval/results/tryit_smoke_transformers4.json`) | 20 of 32 ran: image-classification 3/3, object-detection 2/3, image-segmentation 2/3, text-generation 3/3, summarization 2/3, question-answering 3/3, token-classification 3/3, text-classification 1/3, sentence-similarity 1/3, translation 0/2, speech recognition 0/3. Failures: MLX or quantized weights, a corrupt safetensors file, custom code, missing `sentencepiece`, tokenizers that need a newer transformers |
| Try-it smoke, transformers 5.20 without the extras (`eval/results/tryit_smoke_new_tasks.json`) | 6 of 18 on the new tasks: summarization and question answering are not available in the transformers 5 `pipeline`; image models need `timm` / `torchvision` |

## Live checks

| Check | Result |
|---|---|
| Models per task (`python -m src.ingest counts`) | ASR 3,469 · translation 1,886 · sentence-similarity 1,383 · text-classification 1,617 · token-classification 1,409. **9,764 unique** (D6 estimated 5,000 to 8,000: about 20% more) |
| Hub response shape matches `normalize_record` | Yes: 8 real responses are saved as fixtures (`tests/fixtures/hub/`) and tested. Two real bugs found and fixed: `HfApi.list_models(language=)` does not exist (use `filter=`), and `/raw/main/README.md` returned 403 for some repos and was cached empty (now `/resolve/main/`; non-404 errors raise and are logged) |
| Fetch | 9,763 of 9,764 cards fetched; 1 logged failure (a transient proxy error on `RGalliennePeren/Voxtral-rg`) |
| Canonical base-model ids | 1,513 distinct base ids; 71 resolved to a different current id (legacy ids merged) |
| Pinecone control plane and hosted inference | Work: index created, hosted embeddings (`multilingual-e5-large`, 1,024 dimensions) and hosted rerank (`bge-reranker-v2-m3`, API version `2024-10`; `2024-07` returns 404) |
| Pinecone data plane and filter semantics (E-RET-9 to 12) | **Pass, all four** (`python -m scripts.pinecone_semantics_check`, `eval/results/pinecone_semantics.json`): a missing `size_mb` is kept by the `$or`, `$in` matches any element of a list field, nested `$and` of `$or` clauses is accepted and correct, namespaces never cross. The data-plane host was blocked at first and was allowed later the same day. The Python SDK ignores `HTTPS_PROXY` by default, so `src.index.connect` now passes `proxy_url` and the CA bundle when those variables are set |
| Real upsert | `prod` namespace holds **29,665 vectors** (`describe_index_stats`) |
| Evaluation on Pinecone vs the exact local index | Same aggregates for ours, naive and keyword (violation, unknown, fully verified, answered). Top-5 lists identical on 72 of 100 queries for ours and for naive, 100 of 100 for keyword; the rest differ in order or by one model (approximate search, ties). The labelled results are from the local index; see `eval/results/results-v2-pinecone.md` |
| Pinecone hosted embedding quota | Not stated by the API. The whole corpus (29,665 chunks) used **2.49M tokens** with no quota error |
| Hosted rerank limits | Pair limit 1,024 tokens: Indic chunks exceeded it and failed the whole request, so the call now sends `parameters.truncate = END` |
| Groq limits | `gpt-oss-20b` and `gpt-oss-120b`: 8,000 tokens/min, 1,000 requests/day, 200,000 tokens/day (from response headers). `llama-3.1-8b-instant` is **not** on the account (fallback is `gpt-oss-120b`) |
| Groq JSON mode / extraction | Both models accept `response_format=json_object`. 20-case extraction set: `gpt-oss-20b` exact match **100%** (0 silent drops); `gpt-oss-120b` **85%** (3 silent drops), which led to the deterministic backstop. After the backstop and 3 added cases (23 total): LLM only 87%, with backstop 100% (a tuning-set number, not a generalisation estimate) |
| Groq token cost (measured) | Extraction about 500 tokens/call; explanation 1,345 tokens for 1 model and 2,778 for 5 models. About 3,300 tokens per fully explained query, so about 60 explained queries per day on the 200K daily budget, and two calls fit inside one minute |
| Reasoning tokens | With default reasoning, extraction cost about 1,150 tokens; `reasoning_effort=low` removed that |
| Latency | Warm query, no explanation: median 1.3 s, p95 2.0 s (local index, hosted embed + rerank). With explanation: 7 to 17 s (the Groq call and the throttle) |
| Poisoned cards | Redesigned test (poisoned cards with unknown metadata so the filter cannot remove them): 5/5 runs, tables come from metadata only, poisoned cards ranked below honest ones, 0/5 explanations repeated the injected claims (`eval/results/poison_test.json`) |
| e5 tokenizer vs `approx_tokens` | Not run: hosted embeddings replaced local ones, so the tokenizer is not in the path |
| Local reranker / local embeddings | Not run: the hosted equivalents are used; the local classes are unit-tested with fakes only |
| Try-it smoke test (`python -m scripts.tryit_smoke`, `eval/results/tryit_smoke.json`) | **10 of 18** snippets ran on small safetensors models recommended in the evaluation. Failures: 4 MLX or 4-bit quantized weights (`transformers` cannot load them), 1 corrupt safetensors header, 1 architecture needing newer code, 2 decoder-only models used as `translation` pipelines (unsupported in `transformers` 5). The UI now says the snippet is a standard template, not tested on that model |
| NLLB-200 licence card, `TASK_GUIDES` URLs | Not run |
| Ollama | Not run (no Ollama in the sandbox); the provider code is tested with fakes |

## Data-quality report (the original five-task snapshot, 2026-10-21; the 11-task snapshot is 2026-10-25)

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
