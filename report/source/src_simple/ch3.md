# Methodology and Implementation

## What the system must do

::: table requirements size=9 cols=1.0,7.5,3
The main requirements and how each was checked.
| ID | The system must | Checked by |
|:--|:--|:--|
| R1 | show, in plain words, how it understood the request, and let the user edit it | Screenshots |
| R2 | turn the request into rules (task, language, size, licence rights) and validate them | Unit tests; 29 test requests |
| R3 | ask a follow-up question if the task or language pair is missing (at most two) | 15 vague queries |
| R4 | decide pass, fail or unknown for each rule, in code, from metadata only | Unit tests; violation rate |
| R5 | never suggest a model that fails a rule the user gave | 75 normal queries |
| R6 | show "unknown" when data is missing, never guess | Unknown rate |
| R7 | say clearly when no suggested model is fully checked | 12-query test |
| R8 | keep model-card text from changing any verdict | Poisoned-card test |
:::

## Block diagram

@fig:block shows the two halves of the system. The **offline** half runs once: it downloads model information from Hugging Face, cleans it, and stores it in a searchable index. The **online** half runs for every question: it reads the request, searches the index, checks the rules in code, and shows the best five models with a short explanation. The two halves meet only at the index.

::: fig block w=11.5
fig_block.png
Block diagram. Left: preparing the data once. Right: answering a question. Orange boxes use a language model.
:::

## Hardware and software

No special hardware is needed. We worked in a cloud computer with 4 CPUs and 16 GB of memory, and no GPU. Embeddings and re-ranking come from Pinecone's hosted models (`multilingual-e5-large` and `bge-reranker-v2-m3`), and the index lives in Pinecone. The language model is `gpt-oss-20b` on Groq's free plan. The code is Python, the question pipeline uses LangGraph, the web page uses Streamlit, and 335 automatic tests check the code. One settings file holds all numbers that affect results. Pinecone's free re-ranking limit (500 requests a month) ran out on 25 October 2026, so new searches after that are not re-ranked; the page says so and the pass or fail checks are not affected.

## Preparing the data

We collected 15,991 models from eleven tasks: for each task the 1,000 most downloaded models, plus all models tagged with ten Indian languages for the language tasks. Then we turned the raw information into facts that code can check:

- **Size** is the exact total of the main weight files. If we cannot tell, the size is *unknown* (29.5% of models).
- **Rights.** A table of 54 licences says whether each allows commercial use and modification: yes, no, conditional (extra terms apply) or unknown. A "conditional" licence is never counted as a clean pass.
- **Languages** are cleaned to standard codes. A few well-known multilingual models are added by hand with a source.
- **Translation direction** is known only for models named `opus-mt-<from>-<to>` (380 models); for all others it is unknown.

Model pages are cut into chunks of at most 450 tokens (roughly 300 words; at most four per model), turned into embeddings and stored in the index (48,179 chunks). A checksummed snapshot keeps the data fixed so results can be repeated.

## Answering a question

@fig:graph shows the steps. (1) **Extract:** requests for things we do not cover (image generation, OCR, speech synthesis) are refused. Otherwise the language model writes the rules as JSON, code validates them, and a small rule-based backstop adds anything obvious the model missed, such as "under 500 MB". (2) **Clarify:** if the task is missing we ask, with clickable choices. (3) **Search:** we search with the user's own words, and the filter keeps models whose data is unknown. (4) **Re-rank:** a second model orders the results. (5) **Verify:** code checks the first 100 models and keeps the best 5. (6) **Explain:** the language model writes a short explanation from the model card text, plus the page adds a code snippet and fine-tuning advice. We check 100 but show 5 because search by meaning cannot see size or licence; this raised fully checked answers from 72.3% to 83.3%.

::: fig graph w=12
fig_graph.png
The question pipeline. Clarify and relax stop a run; the page then calls it again with the user's answer.
:::

## The checking rule

@alg:verify is the only place where pass, fail or unknown is decided. A rule can fail only when the data is known and breaks the request, so a shown model can never break a rule the user gave, whatever the search or the language model does.

::: algo verify cap="How one model is checked"
task:       UNKNOWN if no task in data; PASS if equal; else FAIL
languages:  UNKNOWN if list empty/unknown; PASS if all requested present;
            else UNKNOWN if model is multilingual; else FAIL
direction:  PASS if the name states it; else UNKNOWN   (never FAIL)
size:       UNKNOWN if size unknown; PASS if size <= limit; else FAIL
commercial, modifiable:  PASS if yes; FAIL if no; else UNKNOWN
OVERALL = FAIL if any FAIL; else UNKNOWN if any UNKNOWN; else PASS
Sort the 100 by (OVERALL, number of UNKNOWN), drop FAIL, show the first 5.
:::

## Safety and testing

Anyone can write a model card, so card text could contain tricks such as "ignore your instructions" [@greshake2023]. Our main protection is that checks never read model output or card text. In addition, card text is wrapped in tags and treated as data, and the language model is told not to state licence, size or language facts. We tested this with three hostile cards: the tables still came from metadata only.

To test the tool we wrote 100 questions before tuning: 75 normal, 15 vague and 10 meant to be impossible. Five systems answered them: ours, plain RAG (same index, no filters, no checks), BM25 keyword search with the same filters, and Hugging Face's filters in two forms. One shared set of rules judged all of them. Relevance was graded 0 to 2 on 686 blind (request, model) pairs, and explanations were checked claim by claim. **These grades were given by AI judges, not people.**

## How the project was built

Five students worked on this project between 16 and 27 October 2026, with an AI coding assistant (Claude Code) writing and running much of the code and tests under our direction. We made the design decisions and wrote them down as we went. We also fixed the testing rules in advance: the questions were committed first, every question used to fix a bug was listed, and nothing was changed after the results were frozen for grading.
