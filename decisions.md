# Decision Log: HF Model Finder (RAG course project)

Each entry records what was decided, why, and what it commits us to.
**Status key:** Accepted = team agreed · Proposed = recommended, not yet confirmed · Open = undecided

Companion document: [PROJECT.md](PROJECT.md)

---

## D1. Project topic: constraint-verified Hugging Face model finder
- **Status:** Accepted (2026-10-16)
- **Decision:** Build a RAG system that recommends Hugging Face models from natural-language requests that combine hard constraints (size, license, language) with soft preferences (e.g., "works on noisy social-media text").
- **Alternatives considered:** version-aware docs assistant, ToS gotcha finder, food-additive decoder, stack-trace debugger, license compatibility agent (full scored list in ideation notes).
- **Rationale:** clean public data (HF API), a ground-truth evaluation that is largely automatic, a strong side-by-side demo, and relevance to an ML audience.
- **Prior art:** semantic search over the HF Hub already exists (davanstrien's hub-semantic-search MCP; the *Model Fit Finder* Space). Our differentiator is **guaranteed hard-constraint satisfaction with honest *unknown* handling**, not semantic search itself.

## D2. Core principle: the LLM parses, code verifies
- **Status:** Proposed
- **Decision:** The LLM only (a) extracts constraints from the query into JSON and (b) writes explanations. All yes/no checks (size, license, language) are done in code, before retrieval (filters) and after (re-verification).
- **Rationale:** an LLM will recommend a non-commercial or oversized model if its card *sounds* relevant. Deterministic checks make the violation rate measurable and close to zero.
- **Consequence:** every recommendation shows a per-constraint table: ✅ pass / ❌ fail / ⚠️ unknown.

## D3. Three possible results per constraint, plus license mapping
- **Status:** Proposed
- **Decision:** constraints evaluate to `pass`, `fail`, or `unknown`. Licenses map to commercial use as `yes` / `no` / `conditional` / `unknown` (e.g., Apache-2.0 and MIT → yes; CC-BY-NC → no; Llama-style and OpenRAIL → conditional).
- **Rationale:** many cards are missing metadata. Guessing produces false claims; dropping those models silently produces false negatives.

## D4. Vector database: Pinecone
- **Status:** Accepted (2026-10-16)
- **Rationale:** it's the course tool, it has built-in metadata filtering, and it offers hosted reranking.

## D5. Task scope: 5 pipeline tags
- **Status:** Accepted (2026-10-16)
- **In scope:** `automatic-speech-recognition`, `translation`, `text-classification`, `token-classification`, `sentence-similarity`.
- **Out of scope:** `text-generation` (largest category, messiest licenses, already the focus of existing tools). Stretch goal only.
- **Demo roles:** ASR showcases the size constraint (sizes from tens of MB to several GB). Translation showcases the license constraint (NLLB-200 is believed to be CC-BY-NC; **verify**).

## D6. Corpus sampling: top models plus the Indic long tail
- **Status:** Accepted (2026-10-16)
- **Decision:** the union of (a) the top ~1,000 models per task by downloads and (b) *all* models in those tasks tagged `hi`, `mr`, `bn`, `ta`, `te`, `gu`, `kn`, `ml`, `pa`, `ur`.
- **Rationale:** Indic models sit in the low-download long tail; sampling by downloads alone would miss most of them.
- **Expected size:** ~5–8k models. **Verify counts on day 1** before committing.

## D7. LLM provider: Groq primary, local Ollama backup
- **Status:** Accepted (2026-10-16)
- **Commitments:**
  - The provider is hidden behind one function, e.g. `extract_constraints(query) -> dict`, so switching is a single change.
  - Every LLM response is cached (protects against rate limits and makes runs reproducible).
  - Day 2: run 20 test queries and measure **JSON parse success** and **constraint extraction accuracy** on Groq; confirm Ollama passes the same test as a backup.
  - Demo day: switching to Ollama has been rehearsed in advance.

## D8. Embeddings: local `intfloat/multilingual-e5-large`
- **Status:** Proposed
- **Decision:** embed locally and upload the vectors, instead of using Pinecone's hosted inference.
- **Rationale:** the estimated corpus (~6k models × 3 chunks × ~300 tokens ≈ 5.4M tokens) exceeds the Starter plan's historical 5M monthly inference tokens (verify the current limit), and we will re-index several times while tuning.
- **Constraints:** 1024 dimensions, ~507-token input limit, so card sections stay under ~450 tokens. Queries **must** be embedded with the same model.
- **Bonus:** multilingual, so Hindi/Marathi queries work.

## D9. Reranking: Pinecone hosted if the plan allows, local fallback
- **Status:** Proposed
- **Decision:** use Pinecone's integrated reranking if the Starter plan includes it (check with the list-models API on day 1); otherwise run `bge-reranker-v2-m3` locally.

## D10. Metadata schema (draft)
- **Status:** Proposed
- **Fields:** `task`, `languages` (list), `size_mb` (number, only written when known), `size_status` (`known` / `unknown`), `commercial` (`yes` / `no` / `conditional` / `unknown`), `downloads`, `section`, `model_id`.

## D12. Missing-value handling in filters
- **Status:** Accepted (2026-10-16)
- **Problem:** in Pinecone, a vector whose metadata lacks `size_mb` never matches `{"size_mb": {"$lte": 500}}`, so it is **silently dropped**. Sentinel values are worse: `0` or `-1` makes the model **wrongly pass**, and `1e9` makes it **wrongly fail**. All three hide the unknown.
- **Decision:** write `size_mb` only when it's known, always write `size_status`, and filter with an explicit OR:
  ```python
  {"$or": [
      {"size_mb": {"$lte": max_size_mb}},
      {"size_status": {"$eq": "unknown"}},
  ]}
  ```
- **Consequences:**
  - Unknown-size models are retrieved, then marked ⚠️ by `verify.py` and **ranked below** all models that fully pass.
  - Each unknown is recorded *as* unknown, so the violation-rate metric counts it neither as a pass nor as a violation (report "% unknown" as a separate column).
  - The same pattern applies to `commercial` (already has an `unknown` value) and to `languages` (empty list → treat as unknown).
- **Day-1 check:** confirm `$or` filters behave as expected on a 10-vector test index before full ingestion.

## D11. Evaluation design
- **Status:** Proposed
- **Test set:** ~100 queries written **before** tuning, including ~10 impossible queries (no model satisfies all constraints).
- **Metrics:**
  - Constraint violation rate @5: automatic, computed from metadata
  - Relevance @5: manually labelled on ~50 queries
  - Abstention accuracy: does it say "no match" on impossible queries?
- **Ablation:** pure semantic RAG vs. keyword search with filters vs. our system, on the same query set.

---

## Open questions

| # | Question | Why it matters | Owner |
|---|---|---|---|
| Q2 | Size rule: which file counts (safetensors vs .bin, quantized versions)? | Inconsistent sizes make the constraint meaningless | Data owner |

*(Q1 resolved as D12.)*

## Day-1 verification checklist
- [ ] Model counts per task (top 1,000 + Indic-tagged); confirm the ~5–8k estimate
- [ ] Pinecone Starter: current inference token limit, and whether reranking is included
- [ ] Groq free tier: current rate limits for the chosen model
- [ ] NLLB-200 license on its model card
- [ ] Ollama model runs acceptably on at least one team laptop
- [ ] `$or` metadata filter with a missing field behaves as D12 assumes (10-vector test index)
