# Security and limitations

For the viva and the write-up: what we defend against, how, and what we do not claim.
Design: D2 (code verifies), D17 (card text is data), D22 (non-goals).

## 1. Threat model

| Asset | Threat | Defence | Residual risk |
|---|---|---|---|
| The ✅/❌/⚠️ table | A model card or LLM tries to make a model look compliant | Verification reads only metadata and never LLM output or card text (D2) | None from text. Wrong *metadata* is a data-quality problem (§2) |
| Explanation text | Indirect prompt injection from card text ("ignore previous instructions…") | Chunks wrapped in `<card_section>` with escaped attributes; literal tags in the text neutralised; system prompt marks the content as data; citations restricted to candidate ids | Delimiters **reduce but do not eliminate** the risk: an explanation's *wording* can still be influenced. The table cannot |
| Constraint extraction | The user's own query contains instructions, or the LLM returns junk | `clean_constraints` coerces every field to the schema; the parsed intent is shown to the user | An extraction miss silently drops a constraint; the shown intent is the safety net |
| "Try it" snippet | A model id containing quotes/newlines injected into generated code | Snippets come from fixed templates; ids are validated against `^[\w.-]+(/[\w.-]+)?$` and rejected otherwise | None known |
| Secrets | API keys committed or logged | `.env` gitignored; `.env.example` has names only; no key is ever echoed | Team discipline; run the secret scanner before pushing |
| Shared index | A teammate's experiment corrupts demo data | Namespaces `prod` / `exp-<name>`; promote deliberately | Anyone with the key can write `prod` |
| Demo availability | Rate limits, Wi-Fi | LLM cache, rehearsed Ollama switch | Pinecone and query embedding still need the network until replay mode exists |

## 2. What the system does **not** claim

These are the non-goals and honest limits. Say them before a reviewer does.

- **Not legal advice.** Rights come from the *declared* license, mapped by us. A card can be
  wrong, a license can have exceptions, and `conditional` means "read the terms".
- **Declared ≠ true.** Size, languages, base model and license are as accurate as the card
  and Hub metadata. We mark gaps as unknown; we cannot detect lies.
- **A sample of the Hub, not the Hub.** ~5–8k models over five tasks, as of the snapshot
  date shown in the UI. Newer or off-scope models (e.g. `text-generation`) are absent.
- **Not a leaderboard.** Author-reported `model-index` scores are shown as *unverified* and
  never used for ranking (D24).
- **Size is a rule, not a measurement.** It counts the main weight files per D20. Quantized
  and ONNX variants are excluded (non-goal), and models with unusual file names show as
  unknown size.
- **Memory estimates are lower bounds.** They exclude activations, optimizer quirks and
  framework overhead. Treat "fits on a T4" as "might fit".
- **Translation direction is not inferred.** A model listing Hindi and Marathi may not
  translate both ways, so direction is ⚠️ unless the card states it.
- **Multilingual models** (XLM-R, Whisper) are matched through a hand-made map and flagged
  "multilingual, not specific to <language>"; the map is incomplete by construction.
- **Lineage counts are "in our snapshot"**, not on the Hub, and the same base spelled two
  ways is counted twice.
- **LLM variability.** Extraction and explanations come from a model: temperature 0 and a
  cache make runs repeatable, not correct.
- **Not for edge/quantized deployment, not for LLM chatbots** (D22).

## 3. Operational security notes

- Keep `HF_TOKEN`, `PINECONE_API_KEY`, `GROQ_API_KEY` only in `.env` or your shell; do not
  paste them into issues, logs or the write-up.
- The LLM cache stores prompts, which include card excerpts. Treat `.cache/` as local
  scratch; it is gitignored.
- Card text is rendered by Streamlit via `st.write`/`st.code`; do not switch any of it to
  `unsafe_allow_html`.
- Model ids are interpolated into URLs and code only after validation (`guide.try_it_snippet`);
  keep it that way if you add new templates.
