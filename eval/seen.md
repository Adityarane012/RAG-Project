# Evaluation queries used while debugging ("seen")

The tuning policy (implementation-plan §5) lets bug fixes follow failure analysis **if every evaluation query
used to debug is listed**. These are the ones. Report results on them as "seen" in the write-up; the rest of
`eval/queries.jsonl` was never inspected individually before the freeze.

| Query ids | What was looked at | Change it led to |
|---|---|---|
| q016, q017, q018, q020, q025, q043 | v1 results: translation queries had no fully verified model although `Helsinki-NLP/opus-mt-en-hi` exists | verify pool 25 -> 100 models before the top-5 cut (`retrieval.verify_pool`) |
| q099, q100 | Santali was not a known language name, so the language constraint was dropped (3,469 "passes") | Indic language names added to `guide.LANG_NAMES` |
| q004, q038, q050, q066, q093 | A named permissive license ("Apache or MIT", "permissive license") never became a constraint | `_PERMISSIVE` rule in `llm.backstop_constraints`; three **new** extraction cases (x21 to x23) written with different wording |
| q021 | Its parse changed when the permissive-license rule was added (Apache-2.0 now also sets modifiable) | none beyond the rule above |
| q046 | Inspected the candidate pool for the README example ("Marathi NER ... under 500 MB ..."): the relevant L3Cube models are over 500 MB and correctly fail; the rest of the pool is thin. No change made | none (the demo uses a different Marathi NER query) |
| q024, q045 | Read only: both ask a clarifying question (no single language; language identification has no task mapping). Not changed | none (reported as limitations) |

Not evaluation queries (made up for smoke tests, free to use): "small Gujarati text classification model with a
permissive license", "Marathi named entity recognition model I can use commercially", "Hindi to English translation
model under 300 MB", "Tamil speech recognition that I can fine-tune, small", "Kannada sentiment classifier with an MIT
license", "Odia named entity recognition model for news text, free to modify", "Assamese speech recognition, small
and commercial", "Nepali sentence similarity model I can modify", "Sinhala speech recognition model, commercial use",
"image segmentation model for medical scans", "I need an image classifier I can use commercially", "object detection model for traffic cameras",
"image classification model for plant diseases", "segment satellite images", "small language model for text generation I can fine-tune",
"summarization model for news articles, commercial use", "question answering model over a passage, under 500 MB", "a chatbot model I can modify",
"classify photos of food", "text to image diffusion model".

Two design findings came from smoke queries, not from evaluation queries:
1. The hosted reranker rejected Indic chunks longer than 1,024 tokens (`parameters.truncate = END`).
2. The extractor's `soft_query` can lose the topic ("permissive license"), so retrieval and reranking now use the
   user's own words for every system.

Backstop false-positive check (2026-10-21): re-parsing all 100 evaluation queries with the new backstop changed exactly 7 parses
(q004, q021, q038, q050, q066, q093 for the permissive-license rule; q099 for Santali), all intended.
