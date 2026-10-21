# HF Model Finder: Constraint-Verified RAG for Hugging Face Models

> RAG course project · team of 3 · 2 weeks (~6 h/day each) · grading emphasis: working demo
> **Status:** design complete (2026-10-21). Topic and stack accepted 2026-10-16; beginner guidance, build-on support, users, baselines and engineering rules added after professor review on 2026-10-21.
> **Rationale for every choice lives in [decisions.md](decisions.md)** (referenced below as D1, D2, …).
> This file describes *what* we're building and *how*. `decisions.md` records *why*. Keep both up to date.

---

## 1. Problem

Hugging Face hosts well over a million models. Real requests combine **hard constraints** with **soft preferences**:

> "A Marathi NER model **under 500 MB**, **usable commercially**, that works **well on noisy social-media text**."

- Keyword search can't handle the semantic part.
- The Hub's own filters match the license *string*; they don't know that CC-BY-NC rules out commercial use.
- Plain RAG ignores the hard constraints: it will recommend a non-commercial or oversized model because its card *sounds* relevant.
- Beginners don't know the vocabulary (task names, licenses) needed to ask well.
- Finding a model is only the first step. Users then need to **use** it and often **adapt** it.

**The user journey we support: find → use → adapt.**

## 2. Users and use cases (D22)

| User | Example request | What they rely on |
|---|---|---|
| **Primary: Indian developer, commercial product** | "Marathi sentiment for our app, commercial use, under 300 MB" | `commercial`, size, Indic coverage |
| **Secondary: student / beginner** | "I want a Hindi model" | Clarifying questions, shown intent, "Try it", Colab memory check |
| ML researcher planning to fine-tune | "Best base to fine-tune for Tamil NER" | `modifiable`, lineage, LoRA estimate (D14) |
| Compliance reviewer | "Is the model we already use OK commercially?" | Check-a-model mode (D23) |

**Non-goals:** LLM chatbots (`text-generation`), legal advice (rights come from the *declared* license), benchmark leaderboards (D24), edge/quantized deployment (D20).

## 3. What makes it different (D1)

Semantic search over the Hub already exists (davanstrien's hub-semantic-search MCP, the *Model Fit Finder* Space), and the Hub UI filters by license string. Our contribution:

1. **Hard constraints are never violated.** The LLM parses the request; code verifies every constraint (D2).
2. **License rights, not license strings:** `commercial` and `modifiable` are interpreted (D3, D14).
3. **Honest unknowns.** Missing metadata shows as ⚠️ unknown instead of a guess or a silent drop (D3, D12).
4. **Coverage of the Indic long tail** that download-ranked search misses, including multilingual models that don't tag Indic languages (D6, D18).
5. **Beginner-friendly:** plain-language intent, clarifying questions, ready-to-run code (D13).
6. **Build-on support:** modification rights, lineage and fine-tuning memory estimates, all computed from metadata (D14).
7. **A measured result** against naive RAG, keyword search, and the HF Hub's own filters (D11, D19).

## 4. Scope

| In | Out |
|---|---|
| 5 tasks: ASR, translation, text-classification, token-classification, sentence-similarity (D5) | `text-generation` (stretch only) |
| Top ~1,000 models per task + all Indic-tagged models, ~5–8k total (D6) | Datasets, Spaces, the full Hub, quantized variants (D20) |
| Constraints: size, commercial use, modification rights, language, task | Ranking by benchmark scores (shown unverified only, D24) |
| Beginner guidance: shown intent, examples, "Try it", tooltips, clarifying questions (D13) | RAG over fine-tuning tutorials |
| Build-on info: `modifiable`, lineage, memory estimate, task-guide links (D14) | Dataset recommendations, fine-tuning inside the app |
| Two entry points: search, and check-a-model (D23) | |

## 5. Architecture

```
Entry A: search query (or example query)              Entry B: model ID (check-a-model, D23)
   │                                                      │
   ▼                                                      │
[LLM: Groq, Ollama fallback] extract_constraints(query)   │                                              (D7)
   │   size words → fixed threshold table                 │                                              (D18)
   ├── task or key constraint missing? ──► ask ONE clarifying question ──► back to extract (≤2)          (D13)
   ▼                                                      │
[UI] parsed intent in plain words, editable               │                                              (D13)
   ▼                                                      │
[Pinecone] metadata filter ($or keeps unknowns) + dense search, ~50 chunks                               (D4, D10, D12)
   ▼                                                      │
[Reranker] Pinecone hosted or local bge-reranker-v2-m3    │                                              (D9)
   ▼                                                      │
[Code] group chunks → models (best chunk score), top 5    │                                              (D18)
   ▼                                                      ▼
[Code] verify every constraint → pass / fail / unknown ◄──┘   (multilingual and translation-direction rules) (D2, D3, D18)
   ├── nothing passes? ──► relax one constraint and retry (≤1), or abstain                               (D13)
   ▼
[Code] build-on info: modifiable, lineage, memory estimate, reported metrics (unverified)                (D14, D24)
   ▼
[LLM] explanation citing card sections, card text wrapped as untrusted data                             (D17)
   ▼
[Streamlit] ranked models + constraint table + "Try it" + "Build on it" + disclaimer                     (D16)
```

The pipeline is implemented as a **LangGraph graph** (D15). The two loops (clarify, relax-and-retry) are its conditional edges and form the agentic part of the system. Each loop has a cap: at most 2 clarifying questions and 1 retry per query.

| Stage | Responsibility | Tooling |
|---|---|---|
| Ingest | Pull metadata and cards for the 5 tasks; cache raw responses, resumable (D21) | `huggingface_hub` |
| Clean | Strip front matter, badges, HTML, code blocks; metadata fallback chunk for sparse cards (D20) | Python |
| Normalize | `size_mb` (D20 rule), `param_count`, `commercial`, `modifiable`, `languages`, `multilingual`, `base_model`, `doc_quality` | Python, license map, multilingual map |
| Chunk | Split cards by section (≤ ~450 tokens) | Python |
| Embed | `intfloat/multilingual-e5-large`, 1024-d, run locally (D8) | sentence-transformers |
| Index | Upsert vectors + metadata; namespaces `prod` / `exp-<name>` (D10, D21) | Pinecone |
| Query | Extract → clarify → filtered search → rerank → group → verify → relax/abstain → enrich → explain | LangGraph (D15), Groq / Ollama, Pinecone |
| Guide | Plain-language intent, examples, tooltips, templated "Try it" snippet (D13) | Python templates |
| Adapt | Lineage, memory estimate, task-guide link, reported metrics (D14, D24) | Python |
| UI | Side-by-side naive vs. ours; Try it / Build on it panels; check-a-model tab | Streamlit (D16) |

**Invariants**
- Queries and documents are embedded with the same model. Changing the embedding model means re-indexing everything.
- Card text never changes a verification result (D2, D17).
- Every number shown to the user (size, threshold, memory, rights) comes from code or metadata, never from the LLM.

## 6. Evaluation (D11, D19)

**Query set (~120, written before tuning):** ~100 by the teammate not building the pipeline (incl. ~10 impossible, ~15 vague), ~20 from classmates who haven't seen the system.

| Metric | Measures | How |
|---|---|---|
| Constraint violation rate @5 | Recommended models that break a hard constraint | Automatic |
| % unknown @5 | Recommendations with ⚠️ | Automatic |
| Relevance @5 | Match to the soft preference | Manual, ~50 queries |
| Abstention accuracy | "No match" on impossible queries | Automatic |
| Clarification rate | Asks instead of guessing on vague queries | Automatic |
| `modifiable` correctness | Matches the license map | Automatic |
| Explanation faithfulness | Claims supported by cited card text | RAGAS or manual, ~30 answers |
| "Try it" smoke test | Snippet runs | Script, ~20 models |
| Latency | Median and worst case per query | Logged |

**Baselines (D19):** naive RAG (same stack, no filters or verification) · keyword search + filters · HF Hub filters · ours.
**Design justification:** at least one tuning choice backed by a number (e.g. section vs. fixed-size chunking).
**Reproducibility (D21):** snapshot + config + one script regenerate the results table.

## 7. Demo script

1. *"Small sentiment model for Hindi I can use in a commercial app."* Naive RAG recommends a non-commercial or oversized model; ours returns 3 models that pass, each with a ✅ / ❌ / ⚠️ table and card citations. Point out that "small" became "≤ 500 MB" from a fixed table.
2. *"Commercial Hindi→Marathi translation."* Naive RAG and the HF filters suggest NLLB-200 (CC-BY-NC, to be verified); ours excludes it and marks translation direction honestly.
3. **Beginner:** *"I want a Hindi model."* It asks one question ("What should the model do? Find names / Detect sentiment / Transcribe speech / …"), then shows the parsed intent and a "Try it" snippet.
4. **Build on it:** open a recommended model → "Fine-tune of `xlm-roberta-base`; LoRA fits a free Colab T4 ✅; modifiable: yes" + task-guide link.
5. **Check a model:** paste a well-known model ID → instant rights table.
6. An impossible query → "No model meets all constraints; relax the size limit to 1 GB?"
7. Close on the baseline comparison table.

Every planned demo query is cached, so the demo works offline (D21).

## 8. Plan (14 days, started 2026-10-16)

| Days | Data & evaluation | Pipeline | Demo |
|---|---|---|---|
| 1–3 | Checks, resumable ingestion, cleaning, normalization, license + multilingual maps | Local embedding + Pinecone indexing (`prod` / `exp-` namespaces) | UI skeleton |
| 4–6 | **Query set written before tuning** (by non-pipeline teammate); collect classmate queries | Constraint extraction, size-word table, filtered search, chunk → model grouping | Constraint table, shown intent |
| 7–9 | Relevance labels; check `base_model`, `param_count`, `model-index` coverage; run HF Hub baseline once | LangGraph wiring; reranking, abstention, clarifying loop; D17 delimiters + poisoned-card test | Side-by-side view, "Try it" card, check-a-model tab |
| 10–12 | Run all baselines; faithfulness check; smoke test; latency; results table | Relax-and-retry, lineage, memory estimate; fix failure cases | "Build on it" panel, tooltips, disclaimer, polish |
| 13–14 | Write-up; verify results reproduce from snapshot + config + script | Code freeze | Cache demo queries; rehearse, including the Ollama switch |

**Cut order if behind schedule:** reported metrics (D24) → live fetch in check-a-model → memory estimate → lineage → relax-and-retry → tooltips.
**Never cut:** constraint verification, `modifiable`, shown intent, clarifying loop, "Try it", the naive-RAG baseline, faithfulness check, evaluation.

## 9. Risks

| Risk | Mitigation |
|---|---|
| Messy or missing metadata | Unknown state is a feature (D3); filters keep unknowns via explicit `$or` (D12) |
| Multilingual models silently dropped by language filter | Multilingual map, shown as "⚠️ multilingual" (D18) |
| One model fills several top-5 slots | Group chunks by model, best-chunk score (D18) |
| Sparse long-tail cards retrieve poorly | Metadata fallback chunk + "minimal documentation" flag (D20) |
| Constraint extraction misreads the query | Shown intent, editable (D13); fixed size-word table (D18); extraction accuracy measured (D7) |
| Prompt injection through model card text | Cards wrapped in `<card_section>` delimiters and marked as data; verification is code-only, so a card can't change ✅ / ❌; citations restricted to candidates; poisoned-card test (D17) |
| Agent loops forever or burns rate limits | Caps: ≤2 clarifying questions, ≤1 retry per query (D15) |
| Evaluation biased toward our own queries | Non-pipeline teammate writes queries; classmate queries added (D11) |
| Weak or unfair baseline | Naive RAG = same stack minus filters/verification; HF Hub baseline included (D19) |
| HF API rate limits mid-ingestion | Raw responses cached; ingestion resumable (D21) |
| Teammate experiment breaks demo data | Pinecone namespaces `prod` / `exp-<name>` (D21) |
| Groq rate limits or Wi-Fi failure during the demo | Cached demo queries + rehearsed Ollama fallback (D7, D21) |
| Pinecone inference quota | Local embeddings (D8) |
| Users treat rights as legal advice | Disclaimer: based on the declared license, not legal advice (D22) |
| Memory estimate read as exact | Labelled as a lower bound excluding activations (D14) |
| Low `base_model` coverage | Show ⚠️ unknown; drop lineage from the demo if coverage is too low |
| Scope creep | Task list frozen (D5); Must/Should/Skip in D13/D14; cut order in §8 |

## 10. Likely viva questions

| Question | Short answer | Backed by |
|---|---|---|
| Why not just use Hugging Face's filters? | They match license strings, not rights; no soft preferences, no unknowns, no guidance. We measured the difference. | D19 baseline |
| Where is the "G" in RAG? | Grounded, cited explanations, and we measure their faithfulness. | D11 |
| Isn't your test set biased? | Written before tuning, by the non-pipeline teammate, plus classmates' queries. | D11 |
| What if a card contains instructions for your LLM? | Treated as data; verification never reads LLM output. | D17 |
| What if the card's license is wrong? | We verify the *declared* license; not legal advice. | D22 |
| Why Pinecone for ~18k vectors? | Metadata filtering and the course tool, not scale. | D4 |
| How do multilingual models pass a Hindi filter? | Multilingual map, shown as ⚠️. | D18 |
| Which model is the most accurate? | Reported metrics shown unverified, never ranked on. | D24 |
| Who is it for? | Primary: Indian developer building a product. Secondary: beginners. Non-goals stated. | D22 |
| Can you reproduce your results? | Snapshot + config + one script. | D21 |
| What did each of you build? | Every member can explain the full graph and defend D2. | — |

## 11. Repository layout

```
hf-model-finder/
├── PROJECT.md          # what & how (this file)
├── decisions.md        # why
├── config.yaml         # embedding model, chunk size, k, thresholds (D21)
├── .env.example        # API key names only; real .env is gitignored
├── data/
│   ├── raw/            # cached HF API responses (resumable ingestion)
│   └── snapshot-<date>/# normalized metadata used for results
├── eval/
│   ├── queries.jsonl   # written before tuning
│   ├── labels/         # relevance + faithfulness labels
│   ├── baselines/      # naive RAG, keyword, HF Hub results
│   └── run_eval.py     # one script → results table
├── src/
│   ├── ingest.py       # resumable, cached
│   ├── clean.py        # card cleaning, metadata fallback chunk
│   ├── normalize.py    # size rule, params, license map (commercial + modifiable), languages, multilingual map, base_model
│   ├── index.py        # Pinecone upsert, namespaces
│   ├── llm.py          # extract_constraints(), provider switch, cache, delimiter wrapping (D17)
│   ├── retrieve.py     # filtered search, rerank, chunk → model grouping
│   ├── verify.py       # pass / fail / unknown, size-word table
│   ├── guide.py        # plain-language intent, clarifying questions, "Try it" templates
│   ├── adapt.py        # lineage, memory estimate, task-guide links, reported metrics
│   └── graph.py        # LangGraph: nodes, conditional edges, loop caps (D15)
├── tests/              # license map, verify, size table, multilingual map
└── app.py              # Streamlit UI (graph state in st.session_state)
```
