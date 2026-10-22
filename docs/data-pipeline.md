# Data pipeline

From the Hugging Face Hub to vectors in Pinecone. Decisions: D5 (tasks), D6 (sampling),
D8 (embeddings), D10 (schema), D12 (unknowns), D20 (cleaning, size rule), D21 (resumable,
reproducible). Architecture context: [architecture.md](architecture.md).

## 1. Stages and artifacts

| Stage | Code | Input | Output | Resumable |
|---|---|---|---|---|
| 1. Candidate list | `ingest.candidate_ids` | Hub `list_models` | `{task: {ids}}` (in memory; counts printed) | – |
| 2. Fetch | `ingest.fetch_raw` | model id | `data/raw/<org>__<name>.json` (API response with `blobs=true&cardData=true`) and `.md` (README) | yes: per-file cache, atomic writes |
| 3. Normalise | `normalize.normalize_record` | raw JSON | model metadata dict | pure |
| 4. Clean | `clean.clean_card`, `doc_quality` | README | clean text, `full`/`minimal` | pure |
| 5. Chunk | `index.chunk_card` | clean text | `(section, text)` chunks ≤ 450 est. tokens; or one fallback chunk | pure |
| 6. Embed | `index.embed_passages` | chunk text | 1024-d vectors (`passage: ` prefix) | – |
| 7. Upsert | `index.upsert` | vectors + metadata | Pinecone namespace | idempotent per id (see orphan caveat below) |
| 7b. Canonical ids | `ingest.canonicalize` | distinct `base_model` values | `data/raw/_canonical_ids.json` (legacy → current id) | yes: cached, failures retried |
| 8. Snapshot | `snapshot.build` | raw cache + canonical ids | `data/snapshot-<date>/records.jsonl.gz` (sorted, deterministic bytes) + data-quality report | pure |

`data/` is gitignored (large, regenerable). The **snapshot** and `config.yaml` are what the
results table is reproduced from (D21). The snapshot holds normalised metadata only (a few MB
compressed), so it is attached to a **GitHub Release**; `python -m src.snapshot build` prints
the `snapshot_date` and `snapshot_sha256` to paste into `config.yaml`, and `snapshot_url` points
at the Release asset. `snapshot.load_snapshot` refuses a file whose checksum doesn't match. The
**raw cache stays local**: only whoever builds the index needs it. Note that rebuilding the
index therefore needs a re-fetch; the evaluation reads the snapshot and the `prod` namespace.

## 2. Sampling (D5, D6)

Per task in `corpus.tasks`: union of the top `top_n_per_task` (1000) by downloads and
**every** model tagged with one of the ten Indic languages. Indic models sit in the
low-download long tail, so a downloads-only sample would miss most of them. `downloads`
is used for sampling only and never as a ranking signal.

Run `python -m src.ingest counts` first and compare with the ~5–8k estimate before
committing to a full fetch. A model can appear in several tasks' lists; the raw cache is
keyed by model id so it is fetched once.

## 3. Fetching (D21)

- Two requests per model: the API JSON and the raw README.
- `HF_TOKEN` is optional but raises rate limits.
- 429/5xx are retried with growing back-off; other HTTP errors for the JSON propagate to
  `main`, which logs the model to `data/raw/failed.jsonl` and continues.
- A missing or forbidden README is cached as an empty file (the model becomes
  `doc_quality: minimal`).
- Files are written to `*.tmp` then renamed, and read/written as UTF-8, so an interrupted
  run never leaves a truncated file and Indic text survives on any OS.
- Interrupt and restart freely: cached models cost zero requests.

## 4. Normalisation rules

### 4.1 Size (resolves Q2, D20)

```
size_mb = (sum of top-level safetensors weights) / 1,000,000
        else (sum of top-level .bin weights) / 1,000,000
        else unknown
```

- "Weights" = files in the repo root whose name starts with `model` or `pytorch_model`.
- Excluded: `.onnx`, `.gguf`, TF/Flax copies, optimizer/training state, anything in a
  subfolder (alternative copies live there), and adapter-only files (`adapter_model.*`).
- If any counted file has no recorded size the whole answer is *unknown*.
- Never rounded: a 500.04 MB model must not pass "≤ 500 MB".
- 1 MB = 1,000,000 bytes, matching the sizes the Hub displays.
- Models whose weights use another name become **unknown**, which is honest but costly:
  measure the share in the data-quality report (§7) and widen the name rule if it is large.

### 4.2 License rights (D3, D14)

`normalize.LICENSE_RIGHTS` maps a license id to `(commercial, modifiable)`; anything not
listed is `("unknown","unknown")`. Summary (the dict is the source of truth):

| Family | commercial | modifiable |
|---|---|---|
| Apache-2.0, MIT, BSD, CC0, CC-BY | yes | yes |
| CC-BY-NC, CC-BY-NC-SA | no | yes *(result stays non-commercial)* |
| CC-BY-ND | yes | no |
| CC-BY-NC-ND | no | no |
| OpenRAIL family, Llama, Gemma | conditional | conditional |
| GPL/LGPL/AGPL, CC-BY-SA, MPL (copyleft / share-alike) | conditional | conditional |
| anything else | unknown | unknown |

`conditional` always surfaces as ⚠️ when the user requires the right. To add a license,
extend the dict **and** a test; review the license histogram from the data-quality report
for common unmapped values. Rights come from the *declared* license: not legal advice.

### 4.3 Languages (D6, D18)

- Source: `cardData.language`. Spellings are normalised (`hin`→`hi`, `hi-IN`→`hi`,
  `eng`→`en`); unrecognised codes are kept verbatim, never guessed.
- Empty list → `language_status: unknown`.
- A card that says `multilingual` is **not** a language: it sets `multilingual: true` and
  `language_status: unknown`, so the Hindi check is ⚠️, never a false ❌.
- **Multilingual map** (`MULTILINGUAL_MODELS`): models known to cover Indic languages
  without tagging them (XLM-R, Whisper, …). The covered languages are merged into
  `languages`. *Procedure to add an entry:* open the model card, copy its language list,
  keep only languages we filter on, add the entry with a code comment naming the source.
  Target ~20 entries; the current seed has XLM-R and the Whisper family.
  **Owner: the data lead (A).** Every entry is a `MultilingualEntry(languages, source, checked)`:
  `source` must say where the list came from, and `checked` stays `False` until someone has
  compared the Indic ten against that source (a test enforces the source, not the check).

### 4.4 Translation direction (D18)

Only the Helsinki-NLP naming pattern states a direction: `opus-mt-<src>-<tgt>` (also with
3-letter codes, which are normalised). The model gets `directions: ["src-tgt"]` and
`direction_source: "model_name"`, and the UI says "direction from model name". Everything else
stays ⚠️ unknown. Deliberate limits: `opus-mt-tc-…` ids are excluded (their tokens are not
language codes), the name must *start* with `opus-mt-`, and a reversed request is still
⚠️ (the pattern is one-directional but we don't mark a model ❌ for a direction it doesn't
advertise). A third-party fine-tune that keeps the name is assumed to keep the direction;
spot-check a few in Phase 1 (task 1.5).

### 4.5 Lineage and parameters (D14)

`base_model` is the first declared base (a card may list several, e.g. merges); absent →
`lineage_status: unknown`. `param_count` comes from the Hub's safetensors metadata and is
omitted when absent. Base-model ids are compared as written, so the same base spelled two
ways is counted twice unless canonicalised: `ingest.canonicalize` asks the Hub API for each
`base_model` and stores the id it returns (legacy `xlm-roberta-base` → `FacebookAI/xlm-roberta-base`),
and `snapshot.build` applies the map. **Assumption to verify on one real model in Phase 1 (task 1.5)**: that
the API returns the current id for a legacy one. Ids that aren't Hub ids (local paths, URLs) map to
themselves. Check coverage of both in the data-quality report; if
`base_model` coverage is low, drop lineage from the demo.

## 5. Cleaning and chunking (D20, D8)

- Cleaning removes YAML front matter, fenced code, HTML, images and badges; keeps link
  text; drops tables longer than `cleaning.max_table_rows`.
- `doc_quality = minimal` when the cleaned text (placeholders and bare headings removed) is
  shorter than `cleaning.min_card_chars` (200). Such models get one **fallback chunk**
  built from metadata (id, task, languages, base model, tags) so they stay retrievable.
- Chunking splits on markdown headings, then on paragraphs, then on words, so every chunk
  fits `embedding.max_section_tokens` (450; the e5 limit is ~507).
- `tokens.approx_tokens` (also importable from `index`) is a cheap estimate (1.5 × words). Indic scripts may take more
  tokens per word than that; verify with the real tokenizer (E-IDX-4) and adjust.

## 6. Indexing

- Vector id `<model_id>::<i>`; metadata is identical on every chunk of a model plus its
  `section` and `text`; `None` values are dropped.
- Build experiments in `exp-<name>` and promote to `prod` deliberately (D21).
- **Orphan caveat:** upserting over existing ids does not remove chunks that no longer
  exist (a shrunk card leaves `::3` behind). For a rebuild, create a fresh namespace
  rather than upserting over an old one.
- Changing the embedding model or dimension requires a full re-index.

## 7. Data-quality report (Phase 2 deliverable, task 2.4)

Produce these counts from the snapshot and keep them in [data-notes.md](data-notes.md):

| Measure | Why it matters |
|---|---|
| Models per task and total vs the 5–8k estimate | D6 sizing |
| % `size_status = unknown`, **by reason** (`weights_missing_size`, `adapter_only`, `weights_only_in_subfolder`, `gguf_only`, `weights_with_other_name`, `no_weight_files`) | how often the size constraint can only answer ⚠️, and whether the D20 name rule should be widened (`weights_with_other_name` is the one to watch) |
| % `commercial` / `modifiable` = unknown, and the top-30 license strings not in the map | extend the license map |
| % `language_status = unknown`; histogram of raw `language` values | extend the spelling aliases |
| % `multilingual`, and which models | multilingual map coverage |
| % with `base_model`; % with `param_count` | whether lineage / memory are worth showing |
| % `doc_quality = minimal` | retrieval quality of the long tail |
| % cards with `model-index` | whether D24 is worth showing |
| Share of Indic-tagged models among all | validates the D6 sampling |
| Failed fetches (`failed.jsonl`) | completeness |
