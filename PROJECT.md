# HF Model Finder: Constraint-Verified RAG for Hugging Face Models

> RAG course project · team of 3 · 2 weeks (~6 h/day each) · grading emphasis: working demo
> **Status:** design phase (2026-10-16), topic and stack accepted
> **Rationale for every choice lives in [decisions.md](decisions.md)** (referenced below as D1, D2, …).
> This file describes *what* we're building and *how*. `decisions.md` records *why*. Keep both up to date.

---

## 1. Problem

Hugging Face hosts well over a million models. Real requests combine **hard constraints** with **soft preferences**:

> "A Marathi NER model **under 500 MB**, **usable commercially**, that works **well on noisy social-media text**."

- Keyword search can't handle the semantic part.
- Plain RAG ignores the hard constraints: it will recommend a non-commercial or oversized model because its card *sounds* relevant.

## 2. What makes it different (D1)

Semantic search over the Hub already exists (davanstrien's hub-semantic-search MCP, the *Model Fit Finder* Space). Our contribution:

1. **Hard constraints are never violated.** The LLM parses the request; code verifies every constraint (D2).
2. **Honest unknowns.** Missing metadata shows as ⚠️ unknown instead of a guess or a silent drop (D3).
3. **Coverage of the Indic long tail** that download-ranked search misses (D6).
4. **A measured result:** constraint violation rate vs. naive RAG on a fixed query set (D11).

## 3. Scope

| In | Out |
|---|---|
| 5 tasks: ASR, translation, text-classification, token-classification, sentence-similarity (D5) | `text-generation` (stretch only) |
| Top ~1,000 models per task + all Indic-tagged models, ~5–8k total (D6) | Datasets, Spaces, the full Hub |
| Constraints: size, commercial license, language, task | Benchmark-score constraints |

## 4. Architecture

```
User query
   │
   ▼
[LLM: Groq, Ollama fallback] ── extract_constraints(query) → {task, langs, max_size_mb, commercial, soft_query}   (D7)
   │
   ▼
[Pinecone] metadata filter (hard constraints) + dense search on soft_query                                   (D4, D10)
   │
   ▼
[Reranker] Pinecone hosted or local bge-reranker-v2-m3                                                       (D9)
   │
   ▼
[Code] re-verify every constraint → pass / fail / unknown                                                    (D2, D3)
   │
   ▼
[LLM] explanation citing card sections → UI: ranked models + constraint table
```

| Stage | Responsibility | Tooling |
|---|---|---|
| Ingest | Pull model metadata and cards for the 5 tasks | `huggingface_hub` |
| Normalize | Derive `size_mb`, `commercial`, `languages`; mark gaps as unknown | Python, license map (D3) |
| Chunk | Split cards by section (≤ ~450 tokens) | Python |
| Embed | `intfloat/multilingual-e5-large`, 1024-d, run locally (D8) | sentence-transformers |
| Index | Upsert vectors + metadata (D10) | Pinecone |
| Query | Constraint extraction → filtered search → rerank → verify → explain | Groq / Ollama, Pinecone |
| UI | Side-by-side: naive RAG vs. ours | Streamlit or Gradio (Open) |

**Invariant:** queries and documents are embedded with the same model. Changing the embedding model means re-indexing everything.

## 5. Evaluation (D11)

| Metric | Measures | Labelling |
|---|---|---|
| Constraint violation rate @5 | Recommended models that break a hard constraint | Automatic |
| Relevance @5 | Match to the soft preference | Manual, ~50 queries |
| Abstention accuracy | Says "no match" on ~10 impossible queries | Automatic |

**Ablation:** pure semantic RAG vs. keyword search with filters vs. our system, same ~100 queries.
**Rule:** the query set is written **before** any tuning.

## 6. Demo script

1. *"Small sentiment model for Hindi I can use in a commercial app."* Naive RAG recommends a non-commercial or oversized model; ours returns 3 models that pass, each with a ✅ / ❌ / ⚠️ table and card citations.
2. *"Commercial Hindi→Marathi translation."* Naive RAG suggests NLLB-200 (CC-BY-NC, to be verified); ours excludes it.
3. An impossible query → "No model meets all constraints; closest matches are…"
4. Close on the ablation table.

## 7. Plan (14 days)

| Days | Data & evaluation | Pipeline | Demo |
|---|---|---|---|
| 1–3 | Day-1 checks, ingestion, normalization, license map | Local embedding + Pinecone indexing | UI skeleton |
| 4–6 | **100 test queries written before tuning** | Constraint extraction (Groq test on day 2) + filtered search | Constraint table |
| 7–9 | Manual relevance labels | Reranking, abstention logic | Side-by-side view |
| 10–12 | Run ablation, results table | Fix failure cases | Polish, demo script |
| 13–14 | Write-up | Code freeze | Rehearse, including the Ollama switch |

## 8. Risks

| Risk | Mitigation |
|---|---|
| Messy or missing metadata | Unknown state is a feature (D3); filters keep unknowns via explicit `$or` (D12) |
| Inconsistent size calculation | One documented rule (Q2) |
| Constraint extraction misreads the query | Show parsed constraints in the UI, editable |
| Groq rate limits during the demo | Cached responses + rehearsed Ollama fallback (D7) |
| Pinecone inference quota | Local embeddings (D8) |
| Scope creep | Task list frozen on day 1 (D5) |

## 9. Repository layout (proposed)

```
hf-model-finder/
├── PROJECT.md          # what & how (this file)
├── decisions.md        # why
├── data/               # raw + normalized metadata (gitignored if large)
├── eval/               # queries.jsonl, labels, results
├── src/
│   ├── ingest.py
│   ├── normalize.py    # size, license map, languages
│   ├── index.py
│   ├── llm.py          # extract_constraints(), provider switch, cache
│   ├── retrieve.py
│   └── verify.py       # pass / fail / unknown
└── app.py              # UI
```
