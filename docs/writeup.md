# HF Model Finder: Constraint-Verified RAG for Hugging Face Models
## Comprehensive Technical Report & Evaluation Write-Up

**Date:** October 2026  
**Repository:** [Adityarane012/RAG-Project](https://github.com/Adityarane012/RAG-Project)  
**Corpus Snapshot:** 9,764 models · 29,665 indexed chunks · Snapshot date: `2026-10-21`  
**Production Index:** Pinecone hosted index (`hf-model-finder`, `prod` namespace, 1,024-dim `multilingual-e5-large`)

---

## 1. Executive Summary & Problem Formulation

Finding appropriate machine learning models on the Hugging Face Hub for real-world deployments is fraught with subtle landmines:
1. **Hard constraint failures**: Models frequently violate licensing restrictions (e.g., non-commercial CC-BY-NC or custom research-only licenses disguised as permissive), exceed physical RAM/VRAM resource constraints, or fail target language requirements.
2. **Naive RAG hallucinations**: Standard retrieval-augmented generation pipelines embed user prompts, retrieve nearest-neighbor documentation, and rely on an LLM to generate recommendations. Because standard vector similarity measures topical closeness rather than logical compliance, naive RAG often returns models that directly violate hard constraints (50.4% violation rate on our test set).
3. **Hub keyword search limitations**: Hugging Face's native filter and keyword search tools suffer from high false-positive rates (25.9% to 32.8% violations) and leave critical metadata unverified.

**HF Model Finder** solves this through **Constraint-Verified RAG**:
- A LangGraph-based architecture decoupling semantic retrieval from deterministic metadata verification.
- **Code verifies; the LLM never decides compliance** (D2 design principle). Every recommendation is audited by a deterministic verification engine against declared licenses, parameter counts, architecture types, and language tags.
- Honest, tri-state compliance reporting: **✅ Pass**, **❌ Fail**, and **⚠️ Unknown** (when metadata or model cards are silent, the system explicitly marks them unknown rather than guessing).
- Interactive, multi-turn clarification when intent is ambiguous, and graceful degradation on impossible constraints.

---

## 2. System Architecture

```mermaid
graph TD
    UserQuery["User Natural Language Query"] --> Extractor["Constraint Extractor (Groq gpt-oss-20b + Backstop)"]
    Extractor --> IntentCheck{"Intent Ambiguous?"}
    IntentCheck -- Yes --> Clarify["Clarifying Question (LangGraph Loop)"]
    IntentCheck -- No --> PineconeFetch["Filtered Hosted Vector Retrieval (k=50..400)"]
    PineconeFetch --> VerifierPool["Verification Engine (Audit pool of 100 models)"]
    VerifierPool --> Reranker["Hosted BGE-Reranker-v2-m3 (Top-5 Cut)"]
    Reranker --> Explainer["Faithful Explanation Generator (Card Passages)"]
    Explainer --> UI["Streamlit UI (Verified Table + Try-It + Lineage)"]
```

### Core Architectural Pillars
1. **Deterministic Backstop & Sanitizer**: LLM constraint extraction (`openai/gpt-oss-20b`) is safeguarded by `clean_constraints` and a deterministic regex backstop to eliminate silent drops of size, language, or license constraints.
2. **Hosted Dual-Stage Retrieval & Reranking**: Pinecone hosted `multilingual-e5-large` embeddings combined with hosted `bge-reranker-v2-m3` reranker. To avoid dropping valid verified models that rank lower in raw text similarity, the system expands the verification pool to 100 models before cutting to the top 5 (`retrieval.verify_pool`).
3. **Separation of Verified Data & Explanations**: Citations and explanations are generated exclusively from verified card excerpts (`<card_section>` delimiters) with prompt-injection defense.
4. **Deterministic Replay & Offline Demo**: Every state transition can be frozen and served locally (`REPLAY=1`) without external network access.

---

## 3. Data Pipeline & Corpus Statistics

- **Corpus Scope**: 9,764 unique models across 5 core NLP/speech tasks (`automatic-speech-recognition`, `translation`, `text-classification`, `token-classification`, `sentence-similarity`), prioritizing the top 1,000 models per task by downloads plus all Indic-tagged models.
- **Total Chunks**: 29,665 chunks (mean 3.0 chunks per model after stripping boilerplate sections like training hyperparameters, bibtex, and citations).
- **Data Quality & Unknowns**:
  - **Unknown Size**: 27.2% (2,652 models) — primarily GGUF-only, ONNX-only, or non-standard weights.
  - **Unknown Commercial / Modifiable Rights**: 15.3% each.
  - **Unknown Language**: 12.9%.
  - **Indic-tagged Models**: 53.5% of the corpus.

---

## 4. Quantitative Evaluation & Benchmark Results

The evaluation suite was frozen prior to tuning across **100 diverse queries** (75 normal, 15 vague, 10 impossible).

### 4.1 System Comparison on Normal Queries (75 Queries)

| System | Answered % | Recs | Violation % | Unknown % | Fully Verified % | Median Latency (s) |
|---|---|---|---|---|---|---|
| **Ours (Constraint-Verified RAG)** | **97.3%** | 365 | **0.0%** | **16.7%** | **83.3%** | 0.22s |
| **Naive RAG** | 100.0% | 375 | 50.4% | 20.5% | 29.1% | 0.07s |
| **Keyword (BM25 + Filters)** | 100.0% | 368 | 0.0% | 62.0% | 38.0% | 0.05s |
| **HF Hub (Basic Filters)** | 100.0% | 375 | 32.8% | 13.6% | 53.6% | 0.10s |
| **HF Hub (Licensed Filters)** | 100.0% | 375 | 25.9% | 14.7% | 59.5% | 0.09s |

#### Breakdown of Violations by Constraint (% of recommended models failing)
- **Ours**: 0.0% across all constraints (commercial, direction, language, modifiability, size, task).
- **Naive RAG**: Fails size limits on **50.4%** of recommendations, task checks on **24.1%**, language checks on **19.4%**, and commercial license on **4.0%**.
- **HF Hub Licensed**: Fails size checks on **71.9%** of recommendations.

### 4.2 Behavior on Vague and Impossible Queries
- **Vague queries (15 queries)**: Our system asked a clarifying question on **100.0%** of vague queries. In contrast, all baselines answered blindly with unverified models.
- **Queries with no fully verified model in corpus (12 queries)**: Our system flagged 100% of these queries with the prominent *"No model is fully verified"* banner and made **0 false assurance claims**, whereas Naive RAG recommended violating models on **73.3%** of responses.

---

## 5. Human Relevance and Faithfulness Audits (pending)

These two audits are **not done yet**. They need a person: relevance grades (0/1/2) for 686 (request, model) pairs over 40 queries
on a blind sheet, a repeat pass on 15 of those queries at least a day later, and hand-scoring of 28 explanations against the
card passages they cite. The tools and sheets exist (`eval/label_app.py`, `eval/faithfulness_app.py`, `eval/labels/*_sheet.csv`),
and the reports are produced by `python -m eval.relevance_report` and `python -m eval.faithfulness_report`.

An earlier draft of this section reported grades produced by a keyword-matching script, a simulated repeat pass and a Cohen's
kappa computed from it. That is not human labelling, so it has been removed; none of those numbers may be cited.

| Result to report when done | Source |
|---|---|
| Mean grade @5 and share of queries with a grade-2 model, per system | `eval/results/relevance.md` |
| Test-retest agreement of the single labeller (kappa, nominal and quadratic) | `eval/results/relevance.md` |
| Share of explanation claims supported by the cited card text | `eval/results/faithfulness.md` |

---

## 6. Demo Replay Verification

The seven demo scenarios in `demo/plan.json` were recorded against live Pinecone and Groq (`python -m scripts.record_demo`), and
`python -m scripts.rehearse_demo` replays each from `demo/cache/` and fails if any is missing. What the recorded runs show:
1. **Small commercial Hindi sentiment**: "small" became a 500 MB limit; Ours returned 5 of 5 fully verified, while Naive RAG returned 4 of 5 failing the size limit.
2. **Commercial Hindi-to-Marathi translation**: direction is ⚠️ for every model, so no model is shown as fully verified.
3. **Vague request ("I want a Hindi model")**: the system asks which task is wanted before recommending anything.
4. **Marathi NER, commercial use**: Ours returned verified L3Cube and MuRIL NER models; Naive RAG returned speech-recognition models for a text task.
5. **Impossible request ("Hindi to Marathi translation under 1 MB")**: every result is ⚠️ and the banner says no model is fully verified.
6. **Urdu to English translation**: `opus-mt-ur-en` passes direction because the model name states it; the others stay ⚠️.
7. **Tamil NER, modifiable**: modifiable rights and LoRA memory estimates are shown.

This is an automated replay check. The two human rehearsals (one live, one in replay with Wi-Fi off) are still to do.

---

## 7. Limitations, Non-Goals, and Ethical Safeguards

1. **Not Legal Advice**: License rights are interpreted from author-declared license tags. Custom agreements or sub-clauses require human review.
2. **Declared vs. Ground Truth**: Metadata reflects what model authors posted to Hugging Face; the system cannot detect intentional deception in model cards.
3. **Single-Labeller Caveat**: Relevance will be graded by one person who also wrote the queries, on a blind sheet with a repeat pass. Kappa from that pass measures one labeller's self-consistency, not inter-annotator agreement.
3a. **Out-of-scope requests**: only five tasks are indexed (speech recognition, translation, text classification, named-entity recognition, sentence similarity). Requests about images, vision or OCR get a clear "not covered" message and no models.
4. **Prompt Injection Boundary**: Card passages are isolated with XML delimiters to neutralize adversarial model card text, ensuring that malicious documentation cannot compromise verification tables.
5. **Operational Key Hygiene**: API keys live only in the gitignored `.env`. They were pasted into a chat during the build, so they must be rotated after the project.

---

## 8. Milestone status

| Task | Description | Status | Evidence |
|---|---|---|---|
| H1 | Relevance labelling, pass 1 (686 pairs, 40 queries) | Not started (needs a person) | `eval/labels/relevance_sheet.csv` |
| H2 | Faithfulness scoring (28 explanations) | Not started (needs a person) | `eval/labels/faithfulness_sheet.csv` |
| H3 | Relevance labelling, pass 2 (15 queries, at least 24 h after pass 1) | Not started | `eval/label_app.py`, Pass 2 |
| H4 | Relevance and faithfulness reports | Waiting on H1 to H3 | `eval/relevance_report.py`, `eval/faithfulness_report.py` |
| H5 | Rehearsals (live, and replay with Wi-Fi off) | Automated replay check done; human rehearsals pending | `scripts/rehearse_demo.py`, `demo/cache/` |
| H6 | Write-up | Draft; sections 5 and 8 wait on H1 to H4 | `docs/writeup.md` |
| H7 | Snapshot as a GitHub Release asset, URL in `config.yaml` | Pending | `data/snapshot-2026-10-21/records.jsonl.gz` (local) |
| H8 | Rotate the Groq, Hugging Face and Pinecone keys | Pending, after the project | provider dashboards |
