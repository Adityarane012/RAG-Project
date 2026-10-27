# Methodology, Implementation, Flowcharts and Algorithms

This chapter explains how the system is built. It states the requirements and design principles (Section 3.1), shows the block diagram (3.2), describes the hardware and software environment (3.3 and 3.4), and then follows the data from the Hugging Face Hub to the index (3.5) and a user request from the browser to the answer (3.6). The algorithms are given as pseudocode with their cost and correctness arguments (3.7). The user interface, the security design and the evaluation method follow (3.8 to 3.10), and the chapter closes with how the software itself was tested and how the work can be reproduced (3.11 and 3.12). The design is described in the views recommended for a software design description [@ieee1016]: context and composition (3.2 to 3.4), information (3.5), logic and algorithm (3.6 and 3.7), interface (3.8) and the decisions that cut across them (3.9 to 3.12).

## Requirements and design principles

The requirements were written as numbered, verifiable statements with a rationale and a verification method, following the practice of the requirements-engineering standard [@ieee29148]. @tab:requirements lists them. A requirement is considered met only if the last column names evidence that exists in the repository or in Chapter 4.

::: table requirements size=8.5 cols=1.1,6.2,3.6,2.8
Software requirements, with the evidence that verifies each one.
| ID | The system shall | Rationale | Verification |
|:--|:--|:--|:--|
| FR-1 | accept a natural-language request and show, in plain words, how it was understood, editable by the user | Beginners cannot judge a result without knowing what was asked | UI test; @fig:ui_start, @fig:ui_edit |
| FR-2 | extract task, languages, translation direction, size limit, commercial and modification requirements and a soft preference, and validate every field against a fixed schema | Model output is untrusted input | Unit tests; 29-case extraction set |
| FR-3 | ask at most two clarifying questions when the task, or the language pair of a translation, is missing | Guessing silently changes the question | Clarification rate on 15 vague queries |
| FR-4 | decide pass, fail or unknown for every requested constraint in code, from metadata only | Verdicts must not depend on generated text | Unit tests; violation rate |
| FR-5 | never present a model that fails a requested constraint as a recommendation | The core promise of the tool | Violation rate on 75 queries |
| FR-6 | show *unknown* where metadata is missing, and not guess or omit | Guessing invents facts; omitting hides good answers | Unknown rate; data-quality report |
| FR-7 | state when no returned model is fully verified | Prevents false assurance | No-verified slice (12 queries) |
| FR-8 | explain each model with citations restricted to the candidates, without stating licence, size or language facts | Explanations must be grounded and cannot override verdicts | Faithfulness study; poisoned-card test |
| FR-9 | give a starter snippet, rights notes, lineage and a fine-tuning memory estimate | Finding a model is the first step of using it | Unit tests; Try-it smoke test |
| FR-10 | check any model in the snapshot against stated requirements | Serves reviewers of models already in use | Unit tests; @fig:ui_check |
| FR-11 | refuse requests outside its eleven tasks, without searching | Wrong-task models must never appear | Unit tests; @fig:ui_scope |
| FR-12 | offer to relax one constraint or abstain when no candidate is viable, at most once | Bounded recovery | Unit tests (paths reachable only in tests) |
| NFR-1 | be reproducible from a dated, checksummed snapshot, one configuration file and cached model calls | Results must be re-derivable | Snapshot checksum; frozen-evaluation reproduction |
| NFR-2 | treat card text as untrusted data and keep secrets out of the repository | Anyone can publish a card | Poisoned-card test; secret scan |
| NFR-3 | answer in a median of about 2 s without the explanation, and stay inside free-tier token limits with it | Interactive use on free services | Latency measurements |
| NFR-4 | state its limits: rights are declared and not legal advice; labels were produced by language-model judges | Honest, non-misleading claims | Sections 4.8 and 6.2 |
:::

Four design principles follow from these requirements and run through the rest of the chapter.

1. **The language model parses; code verifies.** The model's only jobs are to turn a request into a constraint record (FR-2) and to write an explanation (FR-8). Everything that decides a verdict (FR-4 to FR-7) is a plain function.
2. **Unknown is a first-class value.** Each constraint has three outcomes, and a missing field is never replaced by a default.
3. **Filters are loose and verification is exact.** The vector store's filter only narrows the search; it is written to keep unknowns, and the verification step is the single place where pass or fail is decided.
4. **Every deployed claim has a measurement.** Each design choice that could be wrong (the verify pool, the extraction backstop, the size rule) is backed by a number or listed as a limitation.

## Block diagram

@fig:block shows the system. The left column is the **offline** pipeline that turns the Hub into an index; it is run once per snapshot. The right column is the **online** pipeline that answers a request. The only place the two meet is the index, which holds one vector and one copy of the model's metadata per chunk of a model card.

::: fig block w=14.5
fig_block.png
Block diagram of HF Model Finder: the offline data pipeline (left) and the online query pipeline (right). Orange boxes are the only places a language model is used.
:::

The blocks have the following responsibilities.

- **Hugging Face Hub API** supplies the raw metadata and card text of each model.
- **Ingest, normalise and clean** convert raw records into the metadata schema of @tab:schema, computing size, rights, languages and direction and marking every unknown as unknown.
- **Chunk and embed** split each card by section and convert each chunk into a 1,024-dimensional vector with a multilingual embedding model.
- **Index and snapshot** store the vectors with their metadata in Pinecone (production) or in an exact local index with the same filter semantics, and freeze the normalised records in a checksummed snapshot.
- **Extract** (language model plus deterministic backstop) turns the request into constraints.
- **Filtered search and re-rank** narrow the 48,179 chunks to a pool of 100 candidate models.
- **Verify** decides pass, fail or unknown for each requested constraint and ranks the pool.
- **Explain** (language model) writes a cited explanation of why each shown model suits the request; card text reaches it only as delimited data.
- **Streamlit interface** shows the verdict tables, explanations, snippets, adaptation information and the optional naive-RAG comparison.

## Hardware description

The system needs no special hardware. All development, indexing and evaluation were run in a managed cloud container, and the heavy computation (embedding, re-ranking, language-model inference) is done by hosted services. @tab:hardware lists the environment and the resources each part consumes.

::: table hardware size=9 cols=3,6
Hardware and service environment.
| Item | Specification and use |
|:--|:--|
| Development and evaluation host | Cloud container, Linux 6.x, 4 virtual CPUs, 16 GB RAM, no GPU; Python 3.13 |
| Local data on disk | Normalised snapshot (about 16,000 records), raw card cache, embedding cache (128 MB), exact local index (376 MB) |
| Vector database | Pinecone Starter plan, serverless index `hf-model-finder` on AWS us-east-1, cosine metric, 1,024 dimensions, 48,179 vectors in namespace `prod` |
| Embedding and re-ranking | Pinecone-hosted `multilingual-e5-large` and `bge-reranker-v2-m3`; 4.05 million hosted tokens used to embed the whole corpus once; hosted re-ranking limited to 500 requests per month |
| Language model | Groq free tier, `gpt-oss-20b` (fallback `gpt-oss-120b`): 8,000 tokens per minute, 1,000 requests and 200,000 tokens per day |
| Offline language model | Ollama with `qwen2.5:7b-instruct` (about 4.7 GB, needs about 8 GB RAM) or `qwen2.5:3b` for 8 GB laptops; not run in the evaluation environment |
| Client | Any current web browser; the Streamlit server runs on a laptop or server with Python 3.10 or later and no GPU |
| Local re-ranker (fallback) | The same cross-encoder on CPU: about 103 s to load and about 43 s for 100 chunks, so it is capped at 40 chunks (about 20 s per query) |
:::

Two measured consequences of this environment shaped the design. First, the hosted re-ranker has a monthly request limit that was reached on 25 October 2026, so the application detects the quota error, keeps the vector-search order and says so on the page (Section 3.6.4). Second, the free language-model tier limits *tokens per minute* more tightly than requests, which led to the token throttle of Section 3.7.4 and to the budgeted evidence selection of Section 3.6.8.

## Software description

@tab:software lists the software stack. Versions are those installed in the evaluation environment.

::: table software size=9 cols=3,2.2,5
Software stack.
| Component | Version | Role |
|:--|:-:|:--|
| Python | 3.13 | Implementation language of all modules |
| LangGraph [@langgraph] | 1.2 | Query pipeline as a state graph with conditional edges |
| Streamlit [@streamlit] | 1.66 | Web interface; session state holds the graph state between runs |
| Pinecone client and hosted inference [@pineconefilter; @pineconee5; @pineconererank] | 10.1 | Vector store, metadata filters, embeddings and re-ranking |
| Groq client [@groqlimits] | 1.7 | Language-model calls (JSON mode, low reasoning effort) |
| `huggingface_hub` [@hfhub] | 2.2 | Listing models by task and fetching metadata and cards |
| Transformers [@wolf2020] | 4.57 / 5.20 | Used only by the Try-it smoke test to run generated snippets |
| BM25 keyword index | own code | Keyword baseline (Okapi BM25, k1 = 1.5, b = 0.75), about 100 lines |
| NumPy, PyYAML, requests | 2.5 / 6.0 / 2.34 | Numerics, configuration and HTTP |
| pytest | 9.1 | 335 offline tests |
| Playwright, LibreOffice, matplotlib | – | Screenshots, document rendering and figures for this report |
:::

The code base comprises about 3,600 lines in `src/` and `app.py`, 900 in `eval/`, 700 in `scripts/` and 3,300 in `tests/`. A single `config.yaml` holds every number that influences results (model names, token budgets, chunk limits, retrieval widths, size-word thresholds, graph caps). Language-model providers are hidden behind one function so that changing from Groq to a local Ollama model is a matter of one environment variable.

## Data pipeline

@fig:pipeline summarises the offline pipeline. It is deterministic given the raw cache, resumable after any interruption, and every stage writes to disk before the next begins.

::: fig pipeline w=14.5
fig_pipeline.png
The offline data pipeline: from the Hub API to the index and snapshot.
:::

### Candidate selection and ingestion

For each of the eleven tasks the pipeline lists the top 1,000 models by downloads. For the language tasks (speech recognition, translation, text and token classification, sentence similarity, summarization and question answering) it also adds every model tagged with one of ten Indic languages (Hindi, Marathi, Bengali, Tamil, Telugu, Gujarati, Kannada, Malayalam, Punjabi, Urdu), so that the low-download Indic long tail is represented; this sampling is skipped for the vision tasks, where language does not apply, and for text generation, where thousands of multilingual models carry Indic tags. Downloads are used only to *sample*, never to rank.

For every candidate the pipeline fetches the model's API record with file sizes [@hfhub] and its card in Markdown [@hfcards]. Responses are written atomically to a raw cache, the fetch honours the server's retry hints and exponential back-off on rate limiting, and a re-run never calls the API for a model already cached. Base-model identifiers declared in cards are resolved to their current canonical identifiers (71 legacy identifiers were merged in the original corpus), so that lineage counts are not split across old and new names. The result is a corpus of **15,991 models**: the original five tasks contribute 9,764 and the six added tasks 6,227.

### Normalisation: turning metadata into verifiable facts

Normalisation converts the raw record into the schema of @tab:schema. Four rules matter most.

::: table schema size=8.5 cols=2.4,2.2,6
Metadata written on every chunk of a model.
| Field | Type | Meaning and unknown convention |
|:--|:--|:--|
| `model_id`, `task`, `downloads` | text, text, number | Identifier, Hub task tag, popularity (used for sampling only) |
| `languages`, `language_status`, `multilingual` | list, enum, bool | ISO codes; status is *unknown* when the list is empty; `multilingual` marks models whose list may be partial |
| `size_mb`, `size_status` | number, enum | `size_mb` is written only when known; status is *known* or *unknown* |
| `param_count` | number | Written only when the Hub reports it |
| `commercial`, `modifiable` | enum | `yes`, `no`, `conditional` or `unknown`, from the licence map |
| `base_model`, `lineage_status` | text, enum | Declared base model, if any |
| `directions`, `direction_source` | list, text | Translation direction, only when stated by a naming pattern |
| `doc_quality` | enum | `full` or `minimal` documentation |
| `section`, `text` | text | Per chunk: the card section and its text (what the explanation cites) |
:::

**Size (rule D20).** The model size is the sum of the sizes of its main weight files: the top-level `.safetensors` files if any exist, otherwise the top-level `.bin` files. Duplicate formats (ONNX, GGUF, TensorFlow and Flax copies), nested folders and optimiser state are excluded, and the sum is kept exact (1 MB = 10^6 bytes, as on the Hub) because it is compared with a hard limit. If a counted file has no recorded size, or no weight files qualify, the size is unknown and no number is written. The rule is shown as a flowchart in Appendix A (@fig:a_size). Across the corpus 11,279 models (70.5%) have a known size and 4,712 (29.5%) do not; the reasons are no weight files at all (2,416), GGUF-only (1,570), weights under another name (262), weights only in a sub-folder (243) and adapter-only repositories (221). Widening the rule to those formats is deliberately out of scope, because a quantised or ONNX size is not the size of the model the snippet would load.

**Rights from licences.** A map of 54 licence identifiers assigns each licence a pair of values for commercial use and for modification, each *yes*, *no* or *conditional* (@tab:rights). Permissive licences are *yes / yes*. A non-commercial licence such as CC-BY-NC is *no* for commercial use but *yes* for modification (the result stays non-commercial). A no-derivatives licence is the reverse. Licences that attach use restrictions that follow the model into a fine-tune (OpenRAIL, Llama, Gemma) and copyleft or share-alike licences (GPL, AGPL, CC-BY-SA) are *conditional* for both rights, and a *conditional* right is never shown as a clean pass. Any licence that is missing or not in the map, including the generic identifier `other`, is *unknown* for both. Over the corpus, commercial use is *yes* for 70.3% of models, *conditional* for 6.5%, *no* for 3.2% and *unknown* for 20.1%.

::: table rights size=9 cols=3,2,2,4
Licence-to-rights map (representative entries; the full map has 54).
| Licence identifiers | Commercial use | Modification | Reason |
|:--|:-:|:-:|:--|
| apache-2.0, mit, bsd-3-clause, cc-by-4.0, cc0-1.0 | yes | yes | Permissive |
| cc-by-nc-4.0, cc-by-nc-sa-4.0 | no | yes | Non-commercial; derivatives allowed but stay non-commercial |
| cc-by-nd-4.0 | yes | no | No derivatives |
| cc-by-nc-nd-4.0 | no | no | Neither |
| openrail, creativeml-openrail-m, llama3.1, gemma | conditional | conditional | Use restrictions carry over to derivatives |
| gpl-3.0, agpl-3.0, cc-by-sa-4.0, mpl-2.0 | conditional | conditional | Share-alike or copyleft obligations |
| other, missing, any identifier not in the map | unknown | unknown | Never guessed |
:::

**Languages.** Card language fields are normalised to two-letter codes (region subtags are dropped, three-letter codes for the ten Indic languages are aliased), "multilingual" is removed from the list and recorded as a flag, and an empty list gives *unknown*. Because some widely used multilingual models (XLM-R, Whisper, Qwen3-ASR) cover Indic languages without tagging them, a small hand-made map with a cited source for each entry (13 model identifiers) merges their documented languages into the list and sets the multilingual flag.

**Translation direction.** A language list cannot say whether a model translates Hindi to Marathi or the reverse. Direction is therefore recorded only for models named `opus-mt-<source>-<target>` (380 models), where the name states it and the pattern is one-directional; every other translation model has an *unknown* direction. The interface shows "direction from model name" next to such a pass.

### Cleaning and chunking

Cards are cleaned (front matter, badges, images, HTML, code blocks and long tables removed; short tables kept), then split by Markdown heading into sections, and long sections are split on paragraph and word boundaries so that no chunk exceeds 450 estimated tokens, below the embedding model's limit. Sections that add tokens but no retrieval value (training hyper-parameters, framework versions, citations, acknowledgements, contact details and similar) are dropped, and at most four chunks per model are kept, which brought the corpus from an estimated 85,000 chunks to 48,179 (3.0 per model). A card with fewer than 200 characters of real content is marked `doc_quality = minimal`, and a single fallback chunk built from the metadata (identifier, task, languages, base model, tags) is embedded instead, so that such a model can still be found and is shown with a "minimal documentation" note.

### Embedding, index and snapshot

Each chunk is embedded with `multilingual-e5-large` (1,024 dimensions), with the prefixes the model expects for passages and for queries. Vectors are cached by the hash of the text, so rebuilding an index in a new namespace costs no new embedding; the whole corpus used 4.05 million hosted tokens. The vectors and their metadata are upserted into Pinecone (namespace `prod`; experiments use `exp-<name>`). An exact in-process index with the same filter operators (`$eq`, `$lte`, `$in`, `$and`, `$or`) can be substituted by setting an environment variable; it was used for the frozen evaluation and as a fallback when the data plane was unreachable. A live check confirmed that the hosted filters behave as the local ones do on the four semantics the design depends on: a missing field is kept by an explicit `$or`, `$in` matches any element of a list field, nested `$and` of `$or` clauses is accepted, and namespaces do not mix.

Finally, the normalised records are written to a snapshot file whose SHA-256 checksum is recorded in `config.yaml` and checked on load, and the build is deterministic. The snapshot (15,991 records, SHA-256 `45814b8c…`, dated 25 October 2026) is the ground truth for check-a-model mode and for the evaluation.

## Query pipeline

The online pipeline is a LangGraph state graph, shown in @fig:graph. Nodes are thin functions over plain-Python components that are unit-tested on their own; the graph only routes between them. @tab:nodes lists the nodes.

::: fig graph w=14.5
fig_graph.png
The LangGraph query pipeline and its branches. Clarify and relax end a run; the interface re-invokes the graph with the user's answer.
:::

::: table nodes size=9 cols=1.6,1.4,6
Nodes of the query graph.
| Node | Uses an LLM | Function |
|:--|:-:|:--|
| extract | yes | Out-of-scope check, language-model extraction, validation, deterministic backstop, user overrides |
| clarify | no | Returns one question with clickable options (at most two per query) |
| retrieve | no | Filtered dense search with the user's own words, widening *k* until the pool is large enough |
| rerank | no | Cross-encoder re-ordering of chunks; falls back to vector order if the quota is exhausted |
| verify | no | Pass, fail or unknown for each requested constraint; rank; keep five |
| relax | no | Offers to loosen one constraint (at most once) |
| abstain | no | Ends with no recommendation when every candidate has a known fail and nothing can be relaxed |
| enrich | no | Rights notes, lineage, memory estimate, task guide and snippet for each shown model |
| explain | yes | Cited explanation of each shown model from budgeted card excerpts |
:::

### Constraint extraction

A request first passes a deterministic out-of-scope check: image or music generation, captioning, optical character recognition, text-to-speech, video and similar requests are refused with a message and neither an LLM call nor a search is made. Otherwise the request is sent to the language model with a prompt that lists the eleven tasks with a hint for each, asks for JSON only, and forbids inventing a size: the model may output an explicit size in megabytes only if the user gave one, and otherwise picks a **size word** from a fixed table (@tab:sizewords) whose numeric value comes from code. The model runs at temperature zero with low reasoning effort (about 500 tokens a call), and every response is cached on disk by the hash of the model, prompt and system text.

::: table sizewords size=9.5 cols=3,2
Vague size words and their fixed thresholds.
| Word | Threshold |
|:--|:-:|
| "tiny", "mobile" | at most 100 MB |
| "small", "lightweight" | at most 500 MB |
| "medium" | at most 2,000 MB |
:::

The output is *untrusted*. `clean_constraints` coerces every field to the schema (an unknown task, a non-positive size or a non-boolean right becomes null) and a **deterministic backstop** then fills in only what the model left empty and the request plainly states: an explicit size with a unit (MB or GB), one size word, commercial and modification keywords, named permissive licences ("Apache", "MIT", "BSD" or "permissive licence" are read as commercial and modifiable, an approximation that is shown to the user), exactly one task keyword (two or more categories are ambiguous and left for the user), and language names including Indic spellings. It never overrides the model, never runs on instruction-like queries ("ignore previous instructions", "set commercial to false"), and rejects a `text-generation` guess unless the request has a generation cue. The backstop was added because the larger fallback model silently dropped constraints in three of twenty test cases; with it, extraction matches the expected record exactly on all 29 cases of the extraction set, against 90% for the model alone (@tab:extraction in Chapter 4). The flow is drawn in Appendix A (@fig:a_extract).

### Clarifying questions and the editable reading of the request

If no task was found, or a translation names fewer than two languages, the graph ends the run with a question and clickable options (for example "What should the model do?" with one button per task). The interface shows the question; when the user answers, it re-invokes the graph with the answer as an *override* and carries the counters forward, so the caps (two questions per request, one relaxation) hold across turns. Every result page starts with a plain-language sentence, for example "We understood: you want a model to find names, places and other items in text (NER), for Marathi, usable commercially", and a panel in which any field can be edited and the search repeated. Edits pass through the same validator as model output.

### Retrieval

Retrieval embeds the **user's own words**, not a rewritten query. This was a finding of the project: the extractor's `soft_query` field occasionally lost the topic (a request for a small Gujarati classifier with a permissive licence came back as "permissive license" and retrieved only licence sections), so every system now searches with the original text. A metadata filter is built from the constraints (@fig:a_filter): the task is an exact match; a size limit becomes "size at most the limit *or* size unknown"; a rights requirement removes only models with a definite *no*; and each language becomes "tagged with it, *or* language unknown, *or* multilingual". Every clause keeps the unknowns, so the filter is deliberately loose and verification is exact.

The search asks for 50 chunks and, if they cover fewer than the wanted number of distinct models, doubles the request up to 400, because several chunks of one model can fill the first results. Chunks are then grouped by model and scored by the model's best chunk, so one model cannot occupy several slots. The wanted number is **100**, not five (@fig:funnel). Semantic search cannot see direction, size or licence, because these are not in the card text; if only five models were verified, a fully verified model ranked sixth by meaning would never be seen, and five better-sounding but unknown models would be shown instead. Verifying a pool of 100 and then cutting to five raised the share of fully verified recommendations on the 75 normal queries from 72.3% to 83.3%.

::: fig funnel w=14.5
fig_funnel.png
Verify wide, show narrow: from 48,179 chunks to five models.
:::

### Re-ranking

The chunks returned by the search are re-ordered by a cross-encoder (`bge-reranker-v2-m3`), which reads the request and each chunk together and is more accurate than comparing two separate vectors [@nogueira2019]. At most 100 chunks are sent, truncated to the model's input limit (Indic scripts consume many more tokens than a word count suggests, and an over-long chunk once made a whole request fail), and results are cached by query and chunk text so that a repeated evaluation consumes no quota. If the hosted service reports that its monthly quota is exhausted, the graph sets a flag, keeps the vector order and the interface shows a caption saying that results are not re-ranked; the verdicts are unaffected. A local re-ranker with the same model is the fallback, capped at 40 chunks.

### Verification

Verification is the heart of the system. For each model in the pool, `verify` computes one result for each *requested* constraint (rows for constraints nobody asked for are not produced, so the interface never shows a pass for something the user did not request). @tab:verdicts gives the rule for each constraint, and @fig:verification the combination.

::: table verdicts size=8.5 cols=1.7,3.2,2.6,3.6
Verdict rules for each constraint.
| Constraint | Pass | Fail | Unknown |
|:--|:--|:--|:--|
| Task | Model's task equals the requested task | A different task | No task in metadata |
| Languages (all requested) | Every requested language is in the list | List known, some language absent, model not multilingual | List empty or status unknown; or absent from the list of a multilingual model (list may be partial) |
| Direction | The model name states the direction | Never | Otherwise |
| Size | `size_mb` at most the limit | `size_mb` above the limit | Size unknown |
| Commercial, modifiable | Right is *yes* | Right is *no* | Right is *conditional* or *unknown* |
:::

The overall verdict of a model is *fail* if any row fails, otherwise *unknown* if any row is unknown, otherwise *pass*. Models are sorted by this verdict, then by the number of unknown rows, and the sort is stable so that the re-ranker's order decides between equals. Models that fail are never shown as recommendations. The top five are kept. A model that passes while being multilingual carries a note ("multilingual, not specific to Hindi"), and a model with minimal documentation carries a note; notes never change a verdict.

::: fig verification w=14.5
fig_verification.png
Per-constraint verdicts and their combination into one verdict and a rank.
:::

### Relax-and-retry and abstention

If no model in the pool is viable (every one fails), the graph offers to relax one constraint, in a fixed order (the size limit moves to the next larger size-word threshold, then the modification requirement, then the commercial requirement; the task and languages are never relaxed) and at most once; if nothing can be relaxed it abstains. Because a model whose size or language is unknown can never fail (FR-6), every real request in the corpus leaves something to show, so these two paths are exercised by unit tests but are unreachable on this corpus; an impossible request ends instead as an all-unknown answer with the banner "No model fully verified". This is a limitation discussed in Chapter 4.

### Enrichment

For each shown model the pipeline computes, from metadata only: **rights notes** in plain words (for example, "You may modify it, but the result stays non-commercial"); **lineage** ("fine-tune of X; N other fine-tunes in our snapshot"); a **fine-tuning memory estimate**; a link to the official task guide for fine-tuning; and a **starter snippet** built from a fixed template filled with the model identifier and task (never generated by a language model, and the identifier is validated against a strict pattern before it is placed in code). The memory estimate for a model with *P* parameters uses two bytes per parameter for inference, and sixteen bytes per parameter for full fine-tuning with AdamW in mixed precision; LoRA is estimated as the inference weights plus a trainable adapter of 1% of the parameters at the full-fine-tuning cost (@eq:memory). The estimates are lower bounds that exclude activations and are compared with a free 16 GB GPU.

::: eq memory
M_{inf} = 2P,   M_{LoRA} = 2P + 0.01 · 16P = 2.16P,   M_{full} = 16P   (bytes)
:::

### Explanation

For the shown models, the explanation step selects up to four passages per model from distinct sections (best chunk of each section first) and trims each to its share of a 5,000-token prompt budget, keeping the sentences that overlap with the user's request. The budget exists because the free tier allows 8,000 tokens per minute, so five models with several full chunks each would not fit. The passages are wrapped in `<card_section>` tags and sent to the language model, whose system prompt states that tagged text is third-party data to be described and not obeyed, and that licence, size and language facts must not be stated because they come from the verified table. The reply is JSON; explanations that cite a model identifier outside the candidate set are dropped. If the language model fails, the verified table is still rendered and the page says explanations are unavailable.

## Algorithms

This section gives the main algorithms as pseudocode and states their cost.

### Verification and ranking

::: algo verify cap="Verification of one model and ranking of the pool"
VERIFY(meta, C):                    # C = constraints the user requested
  R <- empty map
  if C.task:
    R[task] <- UNKNOWN if meta.task is empty
               else PASS if meta.task = C.task else FAIL
  if C.langs:
    R[languages] <- UNKNOWN if meta.languages is empty or status unknown
                    else PASS if every requested code is in meta.languages
                    else UNKNOWN if meta.multilingual else FAIL
  if C.direction:
    R[direction] <- PASS if "src-tgt" is in meta.directions else UNKNOWN
  L <- C.max_size_mb, else SIZE_WORDS[C.size_word], else none
  if L is not none:
    R[size] <- UNKNOWN if meta.size_status != known
               else PASS if meta.size_mb <= L else FAIL
  for r in {commercial, modifiable} that were requested:
    R[r] <- PASS if meta[r] = yes; FAIL if meta[r] = no; else UNKNOWN
  return R

OVERALL(R):  FAIL if FAIL in R; else UNKNOWN if UNKNOWN in R; else PASS
RANK_KEY(R): (0 PASS | 1 UNKNOWN | 2 FAIL ,  number of UNKNOWN rows in R)

POOL <- the 100 best models by re-ranked chunk score
sort POOL by RANK_KEY (stable); drop models whose OVERALL is FAIL; keep first 5
:::

*Correctness.* Because every row is a comparison of a requested value with a stored field, and because *fail* is produced only when the stored field is known and violates the request, a returned model cannot violate a requested constraint (FR-5). The property holds independently of retrieval, re-ranking and the language model. *Cost.* Verifying a model is O(|C|), so the 100-model pool costs a few hundred comparisons, negligible beside the network calls.

### Filter construction and widening search

::: algo filter cap="Metadata filter with unknowns kept, and widening k"
BUILD_FILTER(C):
  clauses <- []
  if C.task:      add {task = C.task}
  if L defined:   add {size_mb <= L  OR  size_status = unknown}
  for r in {commercial, modifiable} that were requested:
                  add {r in [yes, conditional, unknown]}
  for each requested language g:
                  add {g in languages OR language_status = unknown
                       OR multilingual = true}
  return {} if no clauses; the clause if one; AND(clauses) otherwise

FETCH_CHUNKS(query, C, want = 100):
  k <- 50
  loop:
    M <- INDEX.search(embed(query), filter = BUILD_FILTER(C), top_k = k)
    if distinct models in M >= want or k >= 400 or |M| < k:  return M
    k <- min(2k, 400)
:::

*Cost.* At most four index calls (k = 50, 100, 200, 400). With the hosted index each call is a single approximate nearest-neighbour query; with the exact local index it is a linear scan of the 48,179 vectors after the filter.

### The query graph

::: algo graph cap="Control flow of one run of the query graph"
RUN(query, overrides, counters):
  if OUT_OF_SCOPE(query): return refusal
  C <- CLEAN(LLM_EXTRACT(query));  C <- BACKSTOP(query, C)
                                    # the backstop is skipped for instruction-like queries
  C <- CLEAN(C overlaid with overrides)
  if C.task is missing (or a translation names < 2 languages)
     and counters.asked < 2:        return CLARIFY(question)
  M <- FETCH_CHUNKS(query, C, want = 100)
  M <- RERANK(query, M)             # vector order is kept if the quota is exhausted
  P <- GROUP_BY_MODEL(M)[:100]
  for m in P:  R[m] <- VERIFY(m.meta, C)
  sort P by RANK_KEY;  S <- first 5
  if no model in S has OVERALL != FAIL:
      if counters.relaxed < 1 and an offer exists:  return RELAX(offer)
      return ABSTAIN
  report[m] <- ENRICH(m) for each viable m in S
  text <- LLM_EXPLAIN(budgeted <card_section> passages of S)  # failure keeps the table
  return table, report, text, banner if no model has OVERALL = PASS
:::

### Token-budget throttle

The free tier counts tokens per minute, so every call first reserves its estimated tokens in a 60-second sliding window and sleeps until the window has room; after the call the estimate is replaced by the provider's own count (@fig:a_llm). A rate-limit error is handled once by waiting the server's `retry-after` period if it is short, and otherwise by trying a fallback model with its own limit. The cost of waiting is bounded by one minute per call.

### Evaluation formulas

For a system answering query *q* with top-five models *m*, and the overall verdict *v(m)* computed by the same verification rules for every system, the report uses the following definitions.

::: eq violation
Violation = |{m : v(m) = fail}| / |{m}|,   Unknown = |{m : v(m) = unknown}| / |{m}|,   Fully verified = |{m : v(m) = pass}| / |{m}|
:::

The three fractions add up to one over all recommended models (@eq:violation). Agreement between two grading passes is reported as Cohen's kappa [@cohen1960],

::: eq kappa
κ = (p_{o} − p_{e}) / (1 − p_{e})
:::

where p_{o} is the observed agreement and p_{e} the agreement expected by chance (@eq:kappa), both unweighted and quadratic-weighted for the ordinal 0 to 2 grades, and is interpreted with the bands of Landis and Koch [@landis1977].

## User interface design

The interface is a single Streamlit page with three tabs (@tab:ui). The design follows the needs of the two main users: a developer who wants fast, trustworthy answers and a beginner who needs guidance. Pass is shown in plain text, fail with a red cross and unknown with a warning sign, so that colour is not the only signal; a legend and a glossary explain every term in plain words. Streamlit re-runs the whole script on every interaction, so the graph state, the loop counters and the loaded services are kept in session state and cached resources; otherwise a clarifying question would lose its place.

::: table ui size=9 cols=2.6,6.4
Interface elements.
| Element | Purpose |
|:--|:--|
| Search tab | Query box, five example queries, "Compare with naive RAG" switch, "We understood" sentence, clarifying questions and relax offers, verdict tables, explanations, banner, Try it and Build on it panels, editable intent, glossary |
| Examples tab | More than 25 example queries grouped by task, each with a "Use query" button |
| Check a model tab | Paste a model identifier from the snapshot; shows facts, an optional verdict table against requirements and the Build on it panel |
| Naive-RAG comparison | Runs the same request with no filters and no verification, side by side, and counts the models that fail a requirement |
| Replay mode | Serves recorded runs without network, for demonstrations; the page says it is a replay |
:::

## Security, safety and ethics

**Untrusted card text.** Anyone can publish a model card, and card text is placed in a prompt, so it is a channel for indirect prompt injection [@greshake2023]. @fig:injection summarises the defence in depth. The most important defence is architectural: verification reads only metadata and never language-model output, so injected text can at most change the *wording* of an explanation and can never change a pass, fail or unknown. Additional layers wrap each passage in delimiters that name its source, escape any literal delimiter inside the card, tell the model in the system prompt that tagged text is data, instruct it not to state licence, size or language facts, and drop any explanation that cites an identifier outside the candidate set. Delimiters reduce the risk but do not eliminate it, and the report says so. A test with three synthetic hostile cards (an authority spoof, a delimiter break and a citation bait) whose metadata was deliberately unknown, so that the filter could not remove them, found that tables came from metadata alone in five of five runs, hostile cards ranked below honest ones, and none of the five explanations repeated an injected claim.

::: fig injection w=14.5
fig_injection.png
Defence in depth against hostile card text: verdicts never depend on the language model.
:::

**Other safeguards.** User edits and model output share one validator; snippet templates reject identifiers that are not of the form `owner/name`; secrets live only in a git-ignored environment file and no key is logged; and no card text is rendered as HTML.

**Ethical concerns.** In line with the value-based approach of the ethics standard [@ieee7000], four values are treated as requirements and not as afterthoughts: *transparency* (every verdict, every unknown and the reading of the request are visible), *honesty* (the tool says when nothing is fully verified, does not guess, and states that rights are read from the declared licence and are not legal advice), *user autonomy* (the user can edit the reading, see the comparison with naive RAG and decide), and *fairness to the long tail* (Indic-language models are sampled deliberately and are not ranked by popularity). The limits of the evidence are also part of honesty: the relevance and faithfulness grades in this report were produced by language-model judges, not by humans, and say so wherever they appear.

## Evaluation methodology

@fig:evaldesign summarises the evaluation. The questions it answers are those of Section 1.3: does verification reduce violations, does it cost relevance, does the system ask and abstain appropriately, are the explanations grounded, and is it better than the Hub's own filters.

::: fig evaldesign w=14.5
fig_evaldesign.png
Design of the evaluation.
:::

**Queries.** One hundred queries were written and committed before any retrieval experiment: 75 normal queries over the five original tasks and at least six Indian languages, with a mix of size, rights, language and direction constraints; 15 vague beginner queries (for example "I want a Hindi model"); and 10 requests intended to be impossible. They were written by the author, from user needs and not from system output, and are frozen; every query later used to debug a failure is listed in a "seen" file (@tab:seen in Chapter 4). One author both wrote the queries and built the system, so there is no independent query writer; this limitation is stated again in Chapter 4.

**Systems.** Five systems answer the same queries. (1) **Ours**: the full graph. (2) **Naive RAG**: the same index, embeddings, re-ranker and language model, but no metadata filter (not even the task) and no verification-driven behaviour. (3) **Keyword + filters**: Okapi BM25 over the same chunks with the same metadata filters. (4) **HF Hub, basic filters**: the Hub's own listing filtered by task and language, ordered by downloads. (5) **HF Hub, licensed filters**: the same plus the licence filter `apache-2.0` whenever commercial use or modification is required, which is the best case for a licence-string filter. Every system is judged by the *same* verification rules applied to its top five, using the same parsed constraints, so one definition of "violation" applies to all, and outputs were frozen before any grading.

**Metrics.** The automatic metrics are the three fractions of (@eq:violation), the share of queries answered, clarification rate on vague queries, behaviour on queries for which no model in the corpus fully passes, and latency. *Relevance* was graded 0 (does not suit), 1 (plausible) or 2 (clearly suits) on a blind sheet of 686 (request, model) pairs over 40 queries, which is the union of the top five of four systems, shuffled, with system names hidden. Size and licence are checked automatically and are not graded. *Faithfulness* counted the factual claims in 28 explanations and how many the shown card passages support. **All relevance and faithfulness grades were produced by independent language-model agents acting as judges** (eight agents for the first relevance pass, three different agents for a repeat pass over 15 queries, two agents for faithfulness) with a written rubric, no access to system names and a requirement to grade by reading; their one-line reasons are stored. This is weaker evidence than human grading, because the judges share a model family with the assistant that helped build the system and no human has checked the grades.

**Reproducibility.** Results are generated by one command from the snapshot, the configuration file and the query file. The labelled evaluation was run on the five-task corpus; after the corpus grew to eleven tasks, the five-task index was restored (`CORPUS_TASKS=five`, a separate namespace and the frozen parses) and reproduced identical top-five lists for ours, naive RAG and keyword search on all 100 queries.

## Verification and validation of the software

Verification and validation activities were planned across four layers, in the spirit of the verification-and-validation standard [@ieee1012], and documented as identified test cases with expected results and recorded outcomes in the manner of the test-documentation standard [@ieee29119]. @tab:tests summarises them.

::: table tests size=9 cols=3,1.4,5.6
Test layers and evidence.
| Layer | Count | What it covers |
|:--|:-:|:--|
| Unit and component tests (`tests/`) | 335 | Licence map, languages, size rule, verification and ranking, filter construction, chunking, cleaning, backstop (40 cases), graph routing and loop caps, guidance, throttle, evidence budget, snapshot checksum, replay, app rendering. All run offline with stubs, in about 23 s |
| Edge-case catalogue | 140 cases | Cases identified as E-NORM, E-VER, E-RET, E-LLM, E-GRAPH and so on, each with an expected result; 103 are marked as covered in the testing plan |
| Live-service checks | – | Hub response shape (eight real responses saved as fixtures), Pinecone filter semantics (four checks), hosted embedding and re-ranking limits, Groq rate limits |
| Extraction accuracy test | 29 cases | Exact match of the constraint record, with and without the backstop |
| Poisoned-card test | 3 cards × 5 runs | Verdicts from metadata only; no repeated injected claim |
| Try-it smoke test | 32 models | The generated snippet runs on small models |
| End-to-end | 7 demo scenarios | Recorded against live services and replayed with the network broken |
:::

Testing found real defects that were fixed and are part of the project's history, among them: a missing `language` argument in the Hub client call, a card-download endpoint that returned an empty card for some repositories, the hosted re-ranker rejecting over-long Indic chunks, the Pinecone client ignoring the proxy setting, a size rule that left known-weights models unknown, and vacuous test assertions that passed regardless of behaviour. Evaluation queries used while debugging are listed in the "seen" table.

## Development process and reproducibility

The project was carried out by one person between 16 and 27 October 2026, with an AI coding assistant doing much of the implementation and test writing under the author's direction and the author making the design decisions. Design decisions D1 to D24 were recorded as they were taken, with alternatives and rationale, and amended when live measurements contradicted them (for example the hosted embedding quota, the verify-pool size and the unreachable abstain path). The repository history has more than 35 commits. A reader can reproduce the work with four commands: install the requirements, run the test suite, rebuild the index from the snapshot and embedding cache, and run the evaluation harness; secrets are supplied in an environment file, and nothing in the repository contains a key.

The tuning policy was set in advance. After the queries were committed, fixes made in response to failures were allowed only if every evaluation query used to debug was listed (@tab:seen), and after the outputs were frozen for grading, no retrieval, ranking, prompt or configuration value was changed. Two design changes made before the freeze were driven by measured failures on the evaluation queries: widening the verify pool from 25 to 100 models (translation queries had no fully verified model although one existed) and adding the permissive-licence and language-name rules to the backstop. Six tasks were added after the freeze; they were tested with smoke queries and the demonstration, and the frozen evaluation was shown to be unchanged.
