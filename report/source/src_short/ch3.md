# Methodology, Implementation, Flowchart and Algorithms

## Requirements and design principles

Requirements were written as identified, verifiable statements [@ieee29148] (@tab:requirements). Four principles follow: the language model parses and code verifies; *unknown* is a first-class value; filters are loose and verification is exact; and every claim has a measurement.

::: table requirements size=8 cols=0.9,6.6,3.6
Main requirements and the evidence that verifies them.
| ID | The system shall | Verification |
|:--|:--|:--|
| FR-1 | show how a request was understood, editable by the user | UI test; @fig:ui_compare |
| FR-2 | extract constraints and validate every field against a schema | Unit tests; 29-case extraction set |
| FR-3 | ask at most two clarifying questions when the task or language pair is missing | Rate on 15 vague queries |
| FR-4 | decide pass, fail or unknown per requested constraint in code, from metadata only | Unit tests; violation rate |
| FR-5 | never present a model that fails a requested constraint | Violation rate on 75 queries |
| FR-6 | show *unknown* where metadata is missing; never guess or omit | Unknown rate; data-quality report |
| FR-7 | state when no returned model is fully verified | 12-query no-verified slice |
| FR-8 | cite only candidates and never state licence, size or language in explanations | Faithfulness; poisoned-card test |
| NFR | be reproducible (checksummed snapshot, one config, cached calls), treat card text as untrusted, and state its limits | Reproduction run; poison test |
:::

## Block diagram

@fig:block shows the offline pipeline (Hub to index) and the online pipeline (request to answer); they meet only in the index, which holds one vector and the model's metadata per card chunk.

::: fig block w=11.5
fig_block.png
Block diagram: offline data pipeline (left) and online query pipeline (right); orange marks language-model use.
:::

## Hardware description

No special hardware is needed. Development and evaluation ran in a cloud container (4 virtual CPUs, 16 GB RAM, no GPU, Python 3.13); embedding and re-ranking use Pinecone-hosted `multilingual-e5-large` [@wang2024me5] and `bge-reranker-v2-m3` [@chen2024bge] on a serverless index (48,179 vectors, 1,024 dimensions, cosine); the language model is `gpt-oss-20b` [@openai2025] on Groq's free tier (8,000 tokens per minute), with `gpt-oss-120b` as fallback and a local Ollama model as an offline option. The hosted re-ranker's 500-requests-a-month quota was reached on 25 October 2026, so uncached searches are not re-ranked and the page says so.

## Software description

The stack is Python, LangGraph [@langgraph] for the query graph, Streamlit [@streamlit] for the interface, Pinecone for vectors and filters [@pineconefilter], the Hugging Face Hub API [@hfhub] for data, and 335 offline pytest tests (about 3,600 lines in `src/` and `app.py`, 900 in `eval/`, 3,300 in `tests/`). One `config.yaml` holds every number that affects results.

**Data pipeline.** For each of eleven tasks the top 1,000 models by downloads are fetched, plus all models tagged with ten Indic languages for the language tasks; downloads are used only for sampling. Normalisation turns raw records into verifiable facts. *Size* is the exact sum of the top-level `.safetensors` (else `.bin`) files, and unknown if any doubt remains (29.5% of models). *Rights* come from a map of 54 licences to commercial use and modification (*yes*, *no*, *conditional*, *unknown*); non-commercial and no-derivative licences are mapped separately, and copyleft and use-restricted licences are *conditional* and never a clean pass. *Languages* are normalised to ISO codes with a small cited map for multilingual models, and *translation direction* is recorded only for `opus-mt-<src>-<tgt>` names (380 models). Cards are cleaned, split by heading into chunks of at most 450 tokens (at most four per model), embedded, and indexed in Pinecone and in an exact local index with the same filter semantics; a SHA-256-checked snapshot freezes the 15,991 records.

::: fig pipeline w=12
fig_pipeline.png
The offline data pipeline: from the Hub API to the index and snapshot (@fig:block shows it in context).
:::

**Query pipeline.** A LangGraph graph runs *extract* (deterministic out-of-scope refusal; language-model JSON at temperature 0; validation; a deterministic backstop that fills only what the request plainly states and never runs on instruction-like queries) → *clarify* (at most two questions) → *retrieve* (the user's own words; metadata filter built so unknowns are kept; k doubled from 50 to 400 until 100 distinct models are covered) → *rerank* → *verify* → *relax* or *abstain* → *enrich* (rights notes, lineage, a LoRA/fine-tuning memory estimate of 2P, 2.16P and 16P bytes for P parameters, a template snippet) → *explain*. Verifying a pool of 100 and showing five (@fig:funnel) raised fully verified answers from 72.3% to 83.3%, because semantic search cannot see size, licence or direction.

::: fig graph w=12
fig_graph.png
The LangGraph query pipeline; clarify and relax end a run and the interface re-invokes the graph with the user's answer.
:::

::: fig funnel w=12
fig_funnel.png
Verify wide, show narrow: from 48,179 chunks to five models.
:::

**Algorithm.** @alg:verify gives the verification rule, the only place where a verdict is decided; the flowcharts are in Appendix A.

::: algo verify cap="Verification of one model and ranking of the pool"
VERIFY(meta, C):                    # C = constraints the user requested
  task:       UNKNOWN if meta.task empty; else PASS if equal, else FAIL
  languages:  UNKNOWN if list empty/unknown; PASS if all requested present;
              else UNKNOWN if meta.multilingual else FAIL
  direction:  PASS if "src-tgt" in meta.directions else UNKNOWN   # never FAIL
  size:       UNKNOWN if size unknown; PASS if size_mb <= limit else FAIL
  commercial, modifiable:  PASS if yes; FAIL if no; else UNKNOWN
OVERALL = FAIL if any FAIL, else UNKNOWN if any UNKNOWN, else PASS
POOL = 100 best re-ranked models; stable-sort by (OVERALL, #UNKNOWN); drop FAIL; show 5
:::

@fig:verification shows how per-constraint verdicts combine. Because a row fails only when the stored field is known and violates the request, a shown model cannot violate a requested constraint, whatever the retriever or the language model does.

::: fig verification w=12
fig_verification.png
Per-constraint verdicts and their combination into one verdict and a rank.
:::

**Security and ethics.** Card text is untrusted [@greshake2023]: verdicts read only metadata, passages are wrapped in `<card_section>` tags with literal tags escaped, the model is told not to follow them or state licence, size or language facts, and citations outside the candidate set are dropped (@fig:injection). In line with [@ieee7000], transparency (every unknown is visible), honesty (rights are *declared*, not legal advice) and user autonomy are requirements.

::: fig injection w=12
fig_injection.png
Defence in depth: verdicts never depend on the language model.
:::

**Evaluation method.** One hundred queries (75 normal, 15 vague, 10 impossible) were written and committed before tuning by one author. Five systems answer them: ours; naive RAG (same index, no filters, no checks); BM25 with the same filters; and the Hub's filters, basic and with `license:apache-2.0`. All are judged by the same verification rules, with outputs frozen before grading. Relevance (0 to 2, 686 blind pairs over 40 queries) and faithfulness (28 explanations) were graded by **language-model judges, not humans**. Testing follows the practice of [@ieee1012] and [@ieee29119]: 335 unit tests, a 140-case edge-case catalogue, live-service checks, an extraction test, a poisoned-card test and a Try-it smoke test.

**Development process.** The project was carried out by one person between 16 and 27 October 2026, with an AI coding assistant (Claude Code) writing and running much of the code and tests under the author's direction; the design decisions, scope and interpretation of results are the author's, and design decisions D1 to D24 were logged with alternatives and rationale. The tuning policy was fixed in advance: queries committed first, every query used for debugging listed, and no retrieval, prompt or configuration change after outputs were frozen for grading.
