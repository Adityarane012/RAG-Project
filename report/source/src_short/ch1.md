# Introduction

A model repository is useful only if the right model can be found in it. The Hugging Face Hub hosts more than a million pre-trained models, yet a developer who needs "a small Marathi named-entity model that I can use in a commercial product" must still translate that sentence into task, language, licence and size checks and read model cards one by one. This report describes **HF Model Finder**, which does that translation and checking automatically and is built so that its answers can be trusted on size, licence rights, language and task. Chapter 1 gives the background, motivation, problem and contributions; Chapter 2 surveys the literature and the gap; Chapter 3 describes the design; Chapter 4 shows the application and the results; Chapter 5 lists core code; Chapter 6 concludes. The appendices hold flowcharts and a data sheet.

## Background of the project topic

Retrieval-augmented generation (RAG) fetches documents at question time and gives them to a language model as context: Lewis *et al.* combined a generator with a dense retriever [@lewis2020], REALM trained retriever and model together [@guu2020], Fusion-in-Decoder read many passages at once [@izacard2021], RETRO retrieved from trillions of tokens [@borgeaud2022] and Self-RAG learned when to retrieve [@asai2024]; a survey organises the family into naive, advanced and modular RAG [@gao2023rag]. Its building blocks are dense retrieval [@karpukhin2020], sentence encoders [@reimers2019], the lexical BM25 baseline [@robertson2009], cross-encoder re-ranking [@nogueira2019], multilingual embeddings [@chen2024bge; @wang2024me5] and approximate nearest-neighbour indexes with filters [@johnson2021; @malkov2020; @gollapudi2023]. Language models can also act as controllers that call tools or other models [@yao2023; @gao2023pal; @shen2023]. Model cards and datasheets document models [@mitchell2019; @gebru2021], but documentation on public hubs is uneven and licences are often missing or mis-categorised [@jiang2023; @longpre2024]. Indic-language resources are concentrated in a few corpora, benchmarks and models [@kakwani2020; @doddapaneni2023; @gala2023; @radford2023; @conneau2020], while most community fine-tunes sit in the low-download long tail.

## Motivation and scope

A request such as "a Marathi NER model under 500 MB, usable commercially, that works well on noisy social-media text" mixes one *soft* preference, which meaning can rank, with several *hard* constraints, which are facts. Keyword search cannot read meaning; the Hub's licence filter matches an identifier, not a right; and plain RAG recommends models whose cards *sound* relevant: in this project's evaluation a naive RAG baseline recommended a model that fails a stated requirement for 50.4% of its recommendations. Metadata is also often missing (about 27% of models in the original corpus have no determinable size). The scope is a *model finder* over a snapshot of 15,991 models in eleven tasks (speech recognition, translation, text and token classification, sentence similarity, image classification, object detection, image segmentation, text generation, summarization, question answering). It does not run models, give legal advice or rank by benchmark scores.

## Problem statement

**To design, implement and evaluate a retrieval-augmented system that returns Hugging Face models verified in code against every stated hard constraint (task, language, size, commercial and modification rights); that shows missing metadata as an explicit *unknown*; that asks for clarification when a request is under-specified; and that is measurably better on constraint satisfaction than naive RAG, keyword search with filters and the Hub's own filters, with attention to Indian-language models.**

## Salient contributions

1. **"The LLM parses, code verifies":** the language model only extracts constraints and writes explanations; every pass, fail or unknown verdict is computed from metadata.
2. **Unknown as a first-class verdict,** with retrieval filters that keep unknowns and a banner when nothing is fully verified.
3. **Rights, not licence strings** (a 54-licence map) and a reproducible size rule; a **verify-wide, show-narrow** design (100 verified, 5 shown).
4. A **LangGraph** pipeline with clarifying questions, editable reading of the request, a prompt-injection defence, snippets and fine-tuning estimates.
5. A **reproducible evaluation** on 100 queries fixed before tuning, with its limits stated.

## Organization of the report and standards followed

The chapters follow the order in the first paragraph. The project is a student system, so the standards below are used as guides and no formal compliance is claimed: requirements are written as identified, verifiable statements [@ieee29148]; the design is described in several views [@ieee1016]; verification activities and test documentation follow the practice of [@ieee1012] and [@ieee29119]; and transparency, honesty about unknowns and user autonomy are treated as requirements [@ieee7000].
