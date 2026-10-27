# Literature Survey

## Introduction to the overall topic

The topic joins four areas: retrieval-augmented generation [@lewis2020; @guu2020; @izacard2021; @borgeaud2022; @asai2024; @gao2023rag], retrieval and ranking [@karpukhin2020; @reimers2019; @robertson2009; @nogueira2019; @chen2024bge; @wang2024me5; @johnson2021; @malkov2020; @gollapudi2023], language models that use tools [@yao2023; @gao2023pal; @shen2023] and the documentation of models and licences [@mitchell2019; @gebru2021; @jiang2023; @longpre2024], with two cross-cutting concerns: Indic-language coverage [@kakwani2020; @doddapaneni2023; @gala2023; @radford2023; @conneau2020] and trustworthy evaluation and security [@es2024; @zheng2023; @thakur2021; @liu2024; @ji2023; @greshake2023; @cohen1960; @landis1977].

## Survey of the literature

**Retrieval-augmented generation.** Lewis *et al.* [@lewis2020] coupled a sequence-to-sequence generator with a dense retriever over Wikipedia, fine-tuned them together and set the state of the art on open-domain question answering, with the advantage that the knowledge base can be updated by replacing the index; the retrieved items are free text, so nothing can require them to satisfy a structured condition. REALM [@guu2020] put a latent retriever into pre-training and beat earlier knowledge-augmented models by four to sixteen points. Fusion-in-Decoder [@izacard2021] encodes each passage with the question and lets the decoder attend to all of them, so accuracy keeps improving as more passages are read, which supports retrieving wide. RETRO [@borgeaud2022] retrieved from a two-trillion-token database and matched models with 25 times more parameters, showing that a store can replace parameters. Self-RAG [@asai2024] learns when to retrieve and critiques its own output, but the critique is a learned judgement and not a guarantee. The survey of Gao *et al.* [@gao2023rag] names naive, advanced and modular RAG; the system here is modular RAG plus a verification stage.

**Retrieval, ranking and filtered search.** Dense retrieval beat BM25 by nine to nineteen points of top-20 accuracy [@karpukhin2020]; Sentence-BERT cut the search for the most similar pair among 10,000 sentences from about 65 hours to five seconds [@reimers2019]; BM25 remains the standard lexical baseline [@robertson2009]; and a BERT cross-encoder improved MS MARCO re-ranking by 27% (relative) [@nogueira2019], which is why a re-ranker follows the vector search here. BGE-M3 and multilingual E5 map more than a hundred languages into one space [@chen2024bge; @wang2024me5]. Filtered-DiskANN [@gollapudi2023] builds label filters into the graph index but assumes every item has its labels; production metadata filters simply drop items that lack the field, so missing data must be handled by the application.

**Tools and model selection.** ReAct interleaves reasoning with actions [@yao2023], and PAL has the model write a program that an interpreter runs [@gao2023pal]; the latter is the precedent for letting code compute what a model should only request. HuggingGPT [@shen2023] lets a language model choose Hub models by reading their descriptions, with no verification of size, licence or language.

**Documentation, licences and Indic resources.** Model cards and datasheets [@mitchell2019; @gebru2021] are conventions, not schemas. A study of Hugging Face model reuse found missing attributes, claimed-versus-actual discrepancies and model risks [@jiang2023], and an audit of 1,800+ datasets found licences omitted in over 70% of cases and wrong in over 50% on hosting sites [@longpre2024]. Indic corpora, benchmarks and models [@kakwani2020; @doddapaneni2023] and translation for all 22 scheduled languages [@gala2023] exist as research artefacts, and no cited work helps choose among the thousands of community fine-tunes derived from them.

**Evaluation and security.** RAGAs defines reference-free faithfulness [@es2024]; strong LLM judges agree with humans more than 80% of the time but have biases [@zheng2023]; BM25 is a robust zero-shot baseline [@thakur2021]. Retrieved text can carry instructions that hijack an application [@greshake2023], which is why verdicts here never depend on the language model. Agreement between graders is reported with Cohen's kappa [@cohen1960] and Landis and Koch's bands [@landis1977].

## Comparison of the surveyed work

::: table compare size=8 cols=3.2,3.4,1.3,1.4,3
Comparison of selected related work with the requirements of constraint-verified model finding.
| Work | Provides | Hard constraints guaranteed | Missing metadata | Gap for this problem |
|:--|:--|:-:|:-:|:--|
| RAG, REALM, FiD, RETRO [@lewis2020; @guu2020; @izacard2021; @borgeaud2022] | Retrieval plus generation over text | no | no | Relevance only |
| Self-RAG [@asai2024] | Adaptive retrieval, self-critique | no | no | Critique is a model judgement |
| Dense, BM25, re-ranking [@karpukhin2020; @robertson2009; @nogueira2019] | Retrieval and ordering | no | n/a | No constraint semantics |
| Filtered ANN [@gollapudi2023] | Search with label filters | for labelled items | assumes present | Unknowns not modelled |
| ReAct, PAL [@yao2023; @gao2023pal] | Reasoning with tools or code | partly | no | Not a selection method |
| HuggingGPT [@shen2023] | LLM picks Hub models | no | no | Selection by text |
| Reuse study, licence audit [@jiang2023; @longpre2024] | Evidence of missing, wrong data | n/a | identified | No tool |
| **This work** | LLM parses, code verifies | **yes** | **yes** | Evaluated on 100 queries |
:::

## Gap analysis and problem definition

Five gaps remain: (1) no selection method guarantees hard constraints; (2) missing metadata is not modelled and needs a verdict of "the data does not say"; (3) licences are displayed, not interpreted as rights; (4) the Indic long tail and untagged multilingual models are invisible to popularity-ranked and tag-filtered search; and (5) RAG metrics measure faithfulness and relevance, not how often a recommendation breaks a stated requirement. They lead to the problem of Section 1.3, with objectives to parse requests into validated constraints, verify each in code with three verdicts, retrieve while keeping unknowns, interpret licences and sizes by fixed rules, serve beginners, and evaluate against three baselines on queries fixed before tuning.
