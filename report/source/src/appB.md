# Appendix B: Data Sheets

This appendix documents the data and the services that the system depends on, in the manner of a datasheet [@gebru2021].

## Datasheet of the model snapshot

**Motivation.** The snapshot exists so that models can be verified against requirements without calling the Hub at query time, and so that results can be reproduced. It was created for this project by the author.

**Composition.** Each record describes one model repository on the Hugging Face Hub: identifier, task, downloads, languages and language status, size and size status, parameter count, commercial and modification rights, base model and lineage status, translation directions, documentation quality, and a flag for the presence of author-reported evaluation results. The snapshot holds 15,991 records (SHA-256 `45814b8c7c15f569e2b558e7b0ae56a77f6835223500a69ab8937f2f443b8fa8`, dated 25 October 2026). The 9,764 records of the earlier five-task snapshot (dated 21 October 2026) are byte-identical in it. Card text is not in the snapshot; it is in the raw cache and, in chunked form, in the index (48,179 chunks).

**Collection process.** For each of eleven task tags the pipeline listed the 1,000 models with the most downloads and, for the language tasks, every model tagged with one of ten Indic languages; it then fetched each model's API record and card (two logged transient failures among about 16,000 fetches). Downloads were used for sampling only.

**Preprocessing.** Size, rights, languages and direction were computed by the rules of Section 3.5.2, with unknown preserved. Base-model identifiers were canonicalised through the Hub API. Cards were cleaned and chunked as in Section 3.5.3.

**Uses.** Intended: verifying constraints on candidate models, check-a-model, evaluation. Not intended: ranking models by quality, legal advice, or any claim about models outside the snapshot.

**Distribution and maintenance.** The snapshot is a local file whose checksum is recorded in the configuration; publishing it as a release asset is pending. It is not updated automatically; a rebuild re-runs the pipeline and produces a new dated snapshot.

**Known limitations.** The snapshot is a sample of the Hub, taken on one date. Metadata is as declared by model authors. Licence rights are interpreted from licence identifiers and are not legal advice.

## Models per task

@tab:b_tasks gives, for each task, the number of models, the number with unknown size, and the number with commercial use *yes* and *unknown*.

::: table b_tasks size=9 cols=3.6,1.5,1.8,1.9,1.9
Composition of the snapshot by task.
| Task | Models | Size unknown | Commercial *yes* | Commercial *unknown* |
|:--|:-:|:-:|:-:|:-:|
| automatic-speech-recognition | 3,469 | 993 | 2,989 | 372 |
| translation | 1,886 | 812 | 1,241 | 290 |
| text-classification | 1,617 | 355 | 1,096 | 388 |
| token-classification | 1,409 | 284 | 1,200 | 156 |
| sentence-similarity | 1,383 | 208 | 1,006 | 284 |
| text-generation | 1,135 | 396 | 668 | 295 |
| question-answering | 1,077 | 263 | 655 | 355 |
| summarization | 1,015 | 130 | 571 | 407 |
| image-classification | 1,000 | 62 | 793 | 153 |
| object-detection | 1,000 | 746 | 479 | 195 |
| image-segmentation | 1,000 | 463 | 544 | 314 |
| **All tasks** | **15,991** | **4,712** | **11,242** | **3,209** |
:::

## Licences in the snapshot

@tab:b_licences lists the most frequent licence identifiers and the rights assigned to them.

::: table b_licences size=9 cols=3,1.6,2.2,2.2
Most frequent licence identifiers.
| Identifier | Models | Commercial | Modification |
|:--|:-:|:-:|:-:|
| apache-2.0 | 7,990 | yes | yes |
| mit | 2,537 | yes | yes |
| (no licence declared) | 2,361 | unknown | unknown |
| other | 808 | unknown | unknown |
| cc-by-4.0 | 573 | yes | yes |
| cc-by-nc-4.0 | 409 | no | yes |
| agpl-3.0 | 368 | conditional | conditional |
| gemma | 194 | conditional | conditional |
| cc-by-sa-4.0 | 99 | conditional | conditional |
| gpl-3.0 | 90 | conditional | conditional |
| cc-by-nc-sa-4.0 | 77 | no | yes |
| bsd-3-clause | 71 | yes | yes |
| llama3.1 | 65 | conditional | conditional |
| llama3.2 | 57 | conditional | conditional |
:::

## Size summary

Among the 11,279 models with a known size, the median is 866 MB and the 90th percentile 6,173 MB. The reasons for an unknown size in the other 4,712 models are no weight files (2,416), GGUF only (1,570), weights under another name (262), weights only in a sub-folder (243) and adapter only (221).

## Vector index

@tab:b_index gives the specification of the vector index and the chunks.

::: table b_index size=9 cols=3.2,6
Vector index specification.
| Item | Value |
|:--|:--|
| Service | Pinecone serverless, index `hf-model-finder`, AWS us-east-1 |
| Namespaces | `prod` (production data), `exp-<name>` (experiments), `eval5` (five-task reproduction of the frozen evaluation) |
| Vectors | 48,179 in `prod`; 15,990 models (one card produced no text) |
| Dimension and metric | 1,024; cosine |
| Embedding model | `multilingual-e5-large`, with the passage and query prefixes the model expects |
| Chunking | By Markdown heading; at most 450 estimated tokens per chunk; at most 4 chunks per model; boilerplate sections dropped; mean 3.0 chunks per model |
| Metadata on each vector | The fields of @tab:schema |
| Filter operators used | `$eq`, `$lte`, `$in`, `$and`, `$or` [@pineconefilter] |
:::

## Models and service limits

@tab:b_models lists the models used and the limits of the free services, as measured or documented in October 2026.

::: table b_models size=9 cols=3,6
Models used and free-tier limits.
| Item | Value |
|:--|:--|
| Embedding [@pineconee5; @wang2024me5] | `multilingual-e5-large`, 1,024 dimensions; Pinecone-hosted; 4.05 million tokens used for the whole corpus |
| Re-ranking [@pineconererank; @chen2024bge] | `bge-reranker-v2-m3`; hosted limit of 500 requests per month, reached on 25 October 2026; local fallback on CPU |
| Primary language model [@openai2025; @groqlimits] | `openai/gpt-oss-20b` on Groq, temperature 0, JSON mode, low reasoning effort; 8,000 tokens per minute, 1,000 requests and 200,000 tokens per day |
| Fallback language model | `openai/gpt-oss-120b` on Groq, tried once after a rate-limit error; same limits, own bucket |
| Offline language model [@qwen2024] | `qwen2.5:7b-instruct` via Ollama (about 4.7 GB), `qwen2.5:3b` for 8 GB machines; the provider code is tested with stubs only |
| Cost of a query | About 500 tokens for extraction and 1,300 to 2,800 for the explanation; about 3,300 for a fully explained query, so about 60 explained queries a day |
:::

## Configuration values that affect results

@tab:b_config lists the values in `config.yaml` on which the results depend.

::: table b_config size=9 cols=3.6,2.4,4
Selected configuration values.
| Key | Value | Meaning |
|:--|:-:|:--|
| `retrieval.k_chunks`, `k_chunks_max` | 50, 400 | First and maximum number of chunks requested |
| `retrieval.top_models` | 5 | Models shown |
| `retrieval.verify_pool` | 100 | Models verified before the cut |
| `embedding.max_section_tokens` | 450 | Largest chunk |
| `embedding.max_chunks_per_model` | 4 | Chunks kept per model |
| `cleaning.min_card_chars` | 200 | Below this a card counts as minimal |
| `size_words_mb` | 100 / 500 / 2,000 | tiny and mobile / small and lightweight / medium |
| `graph.max_clarifying_questions`, `max_relax_retries` | 2, 1 | Loop caps |
| `explain.max_prompt_tokens` | 5,000 | Prompt budget for the explanation |
| `adapt.reference_gpu_gb` | 16 | Reference GPU for memory estimates |
:::
