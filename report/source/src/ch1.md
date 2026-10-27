# Introduction

A model repository is only useful if the right model can be found in it. The Hugging Face Hub now hosts more than a million pre-trained models, yet a developer who needs "a small Marathi named-entity model that I can use in a commercial product" must still translate that sentence into a task tag, a language tag, a licence filter and a size check, then read model cards one by one to find out which candidates actually qualify. This report describes **HF Model Finder**, a system that performs that translation and the checking automatically, and that is built so that its answers can be trusted on the points where trust matters most: size, licence rights, language and task.

The report is organised as follows. This chapter gives the background, motivation, problem statement and contributions of the work. Chapter 2 surveys the literature on retrieval-augmented generation, dense retrieval, language models that use tools, model documentation and Indic-language resources, and ends with the gap this project addresses. Chapter 3 describes the design and implementation: the block diagram, the hardware and software environment, the data pipeline, the query pipeline and its algorithms. Chapter 4 presents screenshots of the working application and the results of the evaluation, with a discussion. Chapter 5 lists the core source code, and Chapter 6 concludes and gives the scope for future work. The appendices contain the soft-code flowcharts, the data sheets, the list of components and the list of papers.

## Background of the project topic

**Retrieval-augmented generation.** Large language models store a great deal of knowledge in their parameters, but that knowledge is frozen at training time, cannot be inspected and is sometimes simply wrong. Retrieval-augmented generation (RAG) addresses this by fetching relevant documents from an external store at question time and giving them to the model as context. Lewis *et al.* combined a pre-trained sequence-to-sequence generator with a dense retriever over Wikipedia and showed gains on knowledge-intensive tasks [@lewis2020]. REALM trained the retriever and the language model together during pre-training [@guu2020], Fusion-in-Decoder let the generator read many retrieved passages at once [@izacard2021], RETRO retrieved from a database of trillions of tokens [@borgeaud2022], and Self-RAG taught a model to decide when to retrieve and to critique its own output [@asai2024]. The survey by Gao *et al.* organises this growing family into naive, advanced and modular RAG [@gao2023rag].

**Retrieval and ranking.** Modern RAG rests on a few retrieval building blocks. Dense passage retrieval encodes questions and passages into vectors and finds neighbours by similarity [@karpukhin2020]; sentence encoders such as Sentence-BERT make such embeddings cheap to compute [@reimers2019]; the probabilistic BM25 function remains a strong lexical baseline [@robertson2009]; and a cross-encoder can re-rank a short list of candidates more accurately than the first-stage retriever [@nogueira2019]. For a multilingual audience, embedding models such as BGE-M3 and multilingual E5 map more than a hundred languages into one vector space [@chen2024bge; @wang2024me5]. Large vector collections are searched with approximate nearest-neighbour indexes such as GPU-accelerated brute force [@johnson2021] and hierarchical navigable small-world graphs [@malkov2020], and the problem of combining vector search with attribute filters has its own literature [@gollapudi2023].

**Language models as controllers.** All of these methods rest on the Transformer architecture [@vaswani2017] and on pre-trained encoders and generators such as BERT [@devlin2019]. A second line of work uses a language model not as the source of answers but as a controller that calls other components: ReAct interleaves reasoning with actions [@yao2023], program-aided language models hand arithmetic to an interpreter instead of computing it in text [@gao2023pal], and HuggingGPT lets a language model choose models from the Hugging Face Hub to solve multi-step tasks [@shen2023]. The principle that the model should *plan* and a deterministic component should *compute* is central to this project.

**Model repositories, documentation and licences.** Model cards [@mitchell2019] and datasheets [@gebru2021] were proposed so that the people who reuse a model or dataset can learn what it is for and how it behaves. In practice, documentation on a public hub is uneven: an empirical study of pre-trained-model reuse on the Hugging Face registry reports that missing or inconsistent documentation and attributes make selection difficult [@jiang2023], and an audit of dataset licences found that licence information on hosting sites is frequently omitted or mis-categorised [@longpre2024]. Licences also differ in kind: a permissive licence allows commercial use and modification, a non-commercial licence does not, and responsible-AI and community licences attach conditions that follow the model into derivatives. A tool that recommends models therefore has to *interpret* licences, not just display them.

**Indic languages.** India has twenty-two scheduled languages and many more spoken ones, but language technology for them is concentrated in a small number of resources: monolingual corpora, benchmarks and pre-trained models [@kakwani2020; @doddapaneni2023], a translation system covering all twenty-two scheduled languages [@gala2023], and multilingual models such as Whisper for speech [@radford2023]. Many community fine-tunes of these models are published on the Hub with little documentation and with low download counts, so they sit in the long tail of any popularity-ranked search. Multilingual encoders such as XLM-R cover Indic languages without carrying a tag for each of them [@conneau2020], which makes simple language filters unreliable.

**Evaluating and securing RAG systems.** Automatic evaluation of RAG has produced reference-free measures such as faithfulness and context relevance [@es2024], and strong language models are now widely used as judges of other systems' output, with measurable agreement with human raters [@zheng2023]. Retrieval benchmarks show that lexical baselines are hard to beat out of domain [@thakur2021], and long-context studies show that models use information in the middle of a long prompt poorly [@liu2024]. Generated text can contain unsupported claims [@ji2023], and when retrieved text is untrusted it can carry instructions that hijack the application, a threat known as indirect prompt injection [@greshake2023]. Agreement between graders is conventionally reported with Cohen's kappa [@cohen1960] and interpreted with the bands of Landis and Koch [@landis1977].

## Motivation and scope of the report

The request quoted above illustrates the motivation. It has one *soft* part, "works well on noisy social-media text", which is a matter of meaning and can be ranked, and several *hard* parts that are matters of fact (@fig:request). Each existing approach fails on one of them. Keyword search cannot read meaning. The Hub's own filters work on metadata, but its licence filter matches a licence identifier and does not know that a CC-BY-NC licence rules out commercial use or that a Llama-style licence imposes conditions on derivatives. A plain RAG pipeline retrieves models whose cards *sound* relevant and lets a language model recommend them; because vector similarity measures topical closeness and not logical compliance, such a pipeline recommends models that are too large, in the wrong language or non-commercial. In this project's own evaluation (Chapter 4), a naive RAG baseline recommended a model that fails at least one stated requirement for 50.4% of its recommendations.

::: fig request w=13.5
fig_request.png
A request combines hard constraints, which code can verify, with a soft preference, which only meaning can rank.
:::

Three further observations shape the scope. First, metadata on the Hub is often missing. About 27% of the models in the original five-task corpus have no determinable size, because their weights are only published in a format such as GGUF or under a non-standard file name; a system that silently drops such models loses good answers, and one that guesses invents facts. Second, the people who most need help are often beginners who do not know the vocabulary of tasks and licences and who, after finding a model, still need to run it and perhaps adapt it. Third, Indian-language models are numerous but poorly surfaced.

The scope of this report is therefore a *model finder*: given a natural-language request, return a short list of models from a snapshot of the Hub, each with a per-requirement verdict, a short cited explanation, a starter code snippet and information on whether the model can be adapted. It covers eleven tasks (automatic speech recognition, translation, text classification, token classification, sentence similarity, image classification, object detection, image segmentation, text generation, summarization and question answering). It does **not** run or chat with a model, does not provide legal advice (rights are read from the *declared* licence), does not rank by benchmark scores, and refuses requests for image or music generation, captioning, optical character recognition, text-to-speech and video, which are outside the tasks indexed.

## Problem statement

**To design, implement and evaluate a retrieval-augmented system that, given a natural-language request that mixes hard constraints (task, language, size, commercial-use and modification rights) with a soft preference, returns Hugging Face models such that every returned model is verified in code against every stated hard constraint; that represents missing metadata as an explicit *unknown* instead of a guess or a silent omission; that asks for clarification when the request is under-specified; and that is measurably better on constraint satisfaction than naive RAG, keyword search with filters and the Hub's own filters, with particular attention to Indian-language models.**

The problem decomposes into five questions, each answered by a measurement in Chapter 4: whether verification reduces constraint violations; whether it costs relevance; whether the system asks when it should and avoids false assurance when nothing fully qualifies; whether the generated explanations are grounded in the model cards; and whether it is better than using the Hub's filters directly.

## Salient contributions

The main contributions of this work are the following.

1. **A design principle, "the LLM parses, code verifies".** The language model is used only to turn the request into a constraint record and to write an explanation. Every pass, fail or unknown verdict is computed by plain functions from model metadata, so a verdict can never be changed by card text or model output.
2. **A three-valued treatment of missing data.** Each requested constraint evaluates to pass, fail or unknown. Retrieval filters are written so that models with unknown fields are kept, then verified and ranked below fully verified models, and the answer states when no returned model is fully verified.
3. **Rights, not licence strings.** A licence-to-rights map interprets 54 licence identifiers as commercial use and modification rights (yes, no, conditional or unknown), and a size rule (the sum of the main weight files) gives a reproducible model size.
4. **A verify-wide, show-narrow retrieval design.** Because semantic search cannot see size, direction or licence, the system verifies a pool of 100 models and shows five; this raised fully verified answers from 72.3% to 83.3% in the evaluation.
5. **A LangGraph pipeline with guided interaction.** Clarifying questions, an editable plain-language reading of the request, relax-and-retry and abstention paths, an out-of-scope refusal, ready-to-run snippets, fine-tuning memory estimates and a check-a-model mode make the tool usable by beginners.
6. **A prompt-injection defence.** Card text is wrapped as data, escaped, and its citations filtered; a poisoned-card test confirmed that verdict tables are unaffected.
7. **A reproducible evaluation.** One hundred queries written before tuning, five systems judged by one rule set, a blind relevance study with two grading passes, an explanation-faithfulness study, a poisoned-card test and a smoke test of the generated snippets, with the exact limits of each stated.
8. **A coverage extension to eleven tasks** that includes vision, text generation, summarization and question answering, with an honest record of which parts of the evaluation cover it.

## Organization of report

@tab:org lists the chapters and what each contains.

::: table org cols=2,8
Organization of the report.
| Chapter | Content |
|:--|:--|
| 1 Introduction | Background, motivation and scope, problem statement, contributions, organization, standards followed |
| 2 Literature survey | Background from 15 or more references; a survey of fourteen papers in paragraph form; a comparison table; the gap and the problem definition |
| 3 Methodology | Requirements, block diagram, hardware and software description, data pipeline, query pipeline, algorithms, user interface, security, evaluation method, testing |
| 4 Snapshots and results | Screenshots of the application; corpus statistics; quantitative results and discussion; threats to validity |
| 5 Source code | Listings of the core modules |
| 6 Conclusion and future scope | Summary of the work, conclusions, limitations and future work |
| Appendices A to D | Soft-code flowcharts; data sheets; list of components; list of papers presented and published |
:::

## Standards followed

The guidelines for this report ask that the IEEE standards followed in designing the project be named at appropriate places. The project is a student software system, not a certified product, so the standards below are used as *guides* for documentation and process, and the report does not claim formal compliance with any of them. @tab:standards states where each one informed the work.

::: table standards cols=3,4,4
IEEE and ISO/IEC/IEEE standards that informed the project, and where they are applied.
| Standard | Used for | Where in this report |
|:--|:--|:--|
| ISO/IEC/IEEE 29148:2018, requirements engineering [@ieee29148] | Writing requirements as uniquely identified, verifiable "shall" statements, with a stated source and a verification method | Section 3.1 (@tab:requirements) |
| IEEE 1016-2009, software design descriptions [@ieee1016] | Describing the design through several views: context, composition, logic and algorithm, interface and information | Sections 3.2 to 3.8 and Appendix A |
| IEEE 1012-2016, verification and validation [@ieee1012] | Planning verification activities and their evidence: unit tests, data checks, live-service checks and evaluation | Section 3.10 and Chapter 4 |
| ISO/IEC/IEEE 29119-3:2021, test documentation [@ieee29119] | Organising the test catalogue with identified cases, expected results and recorded outcomes | Section 3.10 |
| IEEE 7000-2021, ethical concerns in system design [@ieee7000] | Treating transparency, honesty about unknowns, user autonomy and non-misleading claims as design requirements | Sections 3.1, 3.9 and 4.8 |
:::
