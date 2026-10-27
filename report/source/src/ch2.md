# Literature survey

This chapter places the project in the literature. Section 2.1 introduces the overall topic with more than fifteen references. Section 2.2 is a paragraph-style survey of the individual papers that bear most directly on the problem, grouped by theme and read in the order of the reference list. Section 2.3 compares them in a table, and Sections 2.4 and 2.5 identify the gap that is left and state the problem that follows from it.

## Introduction to the overall topic

The topic sits at the meeting point of four areas, shown in @fig:related. The first is **retrieval-augmented generation**, which grounds a language model in documents fetched at question time [@lewis2020; @guu2020; @izacard2021; @borgeaud2022; @asai2024; @gao2023rag]. The second is **retrieval itself**: dense passage retrievers [@karpukhin2020], sentence encoders [@reimers2019], the lexical BM25 baseline [@robertson2009], cross-encoder re-ranking [@nogueira2019], multilingual embedding models [@chen2024bge; @wang2024me5], and the approximate nearest-neighbour indexes and filtered search methods on which production vector stores are built [@johnson2021; @malkov2020; @gollapudi2023]. The third is the use of **language models as controllers** of tools and other models [@yao2023; @gao2023pal; @shen2023]. The fourth is the **documentation and governance of models**: model cards, datasheets, empirical studies of reuse and audits of licensing [@mitchell2019; @gebru2021; @jiang2023; @longpre2024].

Two cross-cutting concerns complete the picture. The first is **language coverage**: Indic-language corpora, benchmarks and models [@kakwani2020; @doddapaneni2023; @gala2023], speech and multilingual encoders that cover many languages without tagging each one [@radford2023; @conneau2020]. The second is **trustworthy evaluation and security**: reference-free RAG metrics [@es2024], language models as judges [@zheng2023], zero-shot retrieval benchmarks [@thakur2021], the limits of long contexts [@liu2024], hallucination [@ji2023], indirect prompt injection [@greshake2023] and the statistics of rater agreement [@cohen1960; @landis1977].

::: fig related w=14.5
fig_related.png
Six strands of prior work surveyed in this chapter and the gap between them.
:::

Taken together, this body of work shows how to *retrieve* documents by meaning, how to let a language model *use* a tool, and how to *document* a model. It does not show how to *select a model that provably satisfies a set of stated requirements* when the metadata that would prove it is incomplete. That is the question this project asks.

## Exhaustive literature survey

### Retrieval-augmented generation

**Lewis *et al.* [@lewis2020]** introduced the name and the recipe. Their RAG models couple a pre-trained sequence-to-sequence generator with a dense retriever that queries a vector index of Wikipedia, and they study two formulations: one in which the same retrieved passages condition the whole output, and one that may use different passages for each token. The retriever and generator are fine-tuned together. The models set the state of the art on several open-domain question-answering benchmarks and produced more specific and more factual text than a parametric-only generator, with the practical advantage that the knowledge base can be updated by replacing the index. For the present problem the lesson is architectural: the retrieval index is a separate, replaceable component. The limitation is that the retrieved items are free-text passages and nothing in the method can require that a retrieved item satisfy a structured condition.

**Guu *et al.* [@guu2020]** (REALM) brought retrieval into pre-training. A masked language model is trained with a latent retriever that attends over a large corpus, and gradients flow through the retrieval step over millions of documents. On open-domain question answering the approach outperformed earlier explicit and implicit knowledge-augmented models by four to sixteen points of absolute accuracy. REALM shows that retrieval quality is learnable, but it still treats relevance as the only property of a retrieved document.

**Izacard and Grave [@izacard2021]** (Fusion-in-Decoder) addressed how a generator should read many retrieved passages. Each passage is encoded independently together with the question and the decoder attends over all the encodings at once, so the cost grows linearly with the number of passages and the answer quality keeps improving as more passages are supplied. This supports the design choice made here of retrieving a *wide* candidate set before narrowing it.

**Borgeaud *et al.* [@borgeaud2022]** (RETRO) scaled the retrieval database to about two trillion tokens and conditioned a transformer on chunks retrieved by similarity to the preceding text, using chunked cross-attention. A model with 25 times fewer parameters matched much larger models on language-modelling benchmarks. RETRO makes the point that a good retrieval store can substitute for parameters, which motivates keeping model facts (size, licence) in a store rather than expecting an LLM to recall them.

**Asai *et al.* [@asai2024]** (Self-RAG) trained a model to decide *when* to retrieve and to critique its own output with special reflection tokens. It outperformed ChatGPT and retrieval-augmented Llama-2 chat on several tasks and improved factuality and citation accuracy in long-form generation. Self-RAG is the closest prior work in spirit to a system that checks its answers, but the critique is itself a learned judgement of the language model and therefore not a guarantee; in the present project the checks that matter are exact comparisons performed in code.

**Gao *et al.* [@gao2023rag]** surveyed the field and organised it into naive RAG (retrieve, then generate), advanced RAG (pre-retrieval and post-retrieval processing such as query rewriting and re-ranking) and modular RAG (components that can be recomposed and routed). The system built here is a modular RAG with an additional stage, *verification*, that the survey's taxonomy does not name.

### Retrieval, ranking and filtered search

**Karpukhin *et al.* [@karpukhin2020]** showed that a dual-encoder trained on a modest number of question-passage pairs can outperform BM25 by nine to nineteen points of top-20 accuracy in passage retrieval, which established dense retrieval as the default first stage for RAG. **Reimers and Gurevych [@reimers2019]** (Sentence-BERT) made semantically meaningful sentence embeddings cheap to compare: finding the most similar pair among ten thousand sentences dropped from about 65 hours with a BERT cross-encoder to about five seconds. **Robertson and Zaragoza [@robertson2009]** review the probabilistic relevance framework behind BM25 and BM25F, which remains the standard lexical baseline; the keyword baseline in this project is a BM25 index. **Nogueira and Cho [@nogueira2019]** applied BERT as a cross-encoder to re-rank passages and improved the previous state of the art on MS MARCO by 27% (relative) in MRR@10, which is the reason a re-ranker follows the vector search here.

**Chen *et al.* [@chen2024bge]** (BGE M3-Embedding) supports more than one hundred languages, three retrieval functions (dense, multi-vector and sparse) and inputs up to 8,192 tokens, trained with self-knowledge distillation; the re-ranker used in this project, bge-reranker-v2-m3, belongs to the same family. **Wang *et al.* [@wang2024me5]** describe the multilingual E5 models, trained by contrastive pre-training on one billion multilingual text pairs and then fine-tuned on labelled data; the *large* member is the embedding model of this project, chosen because queries and cards may be in Hindi, Marathi or English.

**Gollapudi *et al.* [@gollapudi2023]** (Filtered-DiskANN) tackle the problem that matters most for constrained search: how to combine nearest-neighbour search with attribute filters. Filtering before the search is exact but slow for selective filters, and filtering afterwards can return nothing; their graph index is built with the labels in mind and gives a better accuracy-throughput trade-off than either. The work assumes that every item *has* its labels. Production vector stores expose a simpler model, a metadata filter that keeps only items matching a condition, and with that model an item that lacks the field is silently excluded. How to treat missing fields is left to the application, and it is a central design question here. Underneath such stores are the index structures of Johnson *et al.* [@johnson2021] (billion-scale brute-force and compressed search on GPUs) and Malkov and Yashunin [@malkov2020] (hierarchical navigable small-world graphs), which this project uses indirectly through the hosted service and directly through an exact local index with the same filter semantics.

### Language models that use tools

**Yao *et al.* [@yao2023]** (ReAct) let a language model alternate between reasoning traces and actions such as calling a search API, which reduced hallucination on question answering and improved success on interactive decision-making benchmarks. **Gao *et al.* [@gao2023pal]** (PAL) go a step further in separating roles: the model writes a program as its reasoning and a Python interpreter executes it, and this beat chain-of-thought prompting with a much larger model on arithmetic reasoning. PAL is the clearest precedent for the principle adopted here: where an answer is a computation, the language model should write the *question* and code should compute the *answer*.

**Shen *et al.* [@shen2023]** (HuggingGPT) is the closest prior work on the *task*. A language model acts as a controller that plans a request into sub-tasks, selects an expert model from the Hugging Face Hub for each, runs them and summarises the results. Model selection is done by giving the language model textual descriptions of candidate models. There is therefore no verification of size, licence or language: the choice is a judgement of the language model over text, and the approach has no way to report that a fact is missing.

### Model documentation, reuse and licensing

**Mitchell *et al.* [@mitchell2019]** proposed model cards as short documents that accompany a trained model and state its intended use, evaluation conditions and limitations; **Gebru *et al.* [@gebru2021]** proposed datasheets for datasets on the same principle. Both are the reason Hub metadata exists at all and both are the source of the data used here, but both are conventions, not schemas, so the fields a recommender needs are present only when authors choose to write them.

**Jiang *et al.* [@jiang2023]** studied how practitioners reuse pre-trained models on the Hugging Face registry. From interviews with twelve practitioners and measurements of the registry they identified three recurring challenges: missing attributes, discrepancies between claimed and actual performance, and model risks. The first of these is what the *unknown* verdict in this project represents. **Longpre *et al.* [@longpre2024]** audited more than 1,800 text datasets and found frequent mis-categorisation of licences on widely used hosting sites, with licences omitted in more than 70% of cases and errors in more than 50%. Although the audit concerns datasets, it shows that a licence shown on a hub page cannot be taken at face value, which is why this project reports rights as *declared* and states that it is not legal advice.

### Indic-language resources

**Kakwani *et al.* [@kakwani2020]** (IndicNLPSuite) released monolingual corpora, evaluation benchmarks and pre-trained models for Indian languages. **Doddapaneni *et al.* [@doddapaneni2023]** extended this to IndicCorp v2, with 20.9 billion tokens in 24 languages, the IndicXTREME benchmark of nine tasks over 20 languages, and the IndicBERT v2 model. **Gala *et al.* [@gala2023]** (IndicTrans2) released parallel corpora, an n-way benchmark and open translation models covering all 22 scheduled Indian languages. **Radford *et al.* [@radford2023]** (Whisper) trained speech models on 680,000 hours of multilingual supervised data and showed that they generalise to standard benchmarks without fine-tuning, and **Conneau *et al.* [@conneau2020]** (XLM-R) trained a cross-lingual encoder at scale for around one hundred languages. These are the foundations on which the Indic models in the Hub are built, but they are research artefacts. The thousands of community fine-tunes derived from them are what a developer actually downloads, and no cited work helps a developer choose among them.

### Evaluation, trust and security

**Es *et al.* [@es2024]** (RAGAs) defined reference-free measures for RAG, notably *faithfulness* (are the claims in the answer supported by the retrieved context) and context relevance; the explanation-faithfulness study in this project follows the same idea but is carried out by grading the claims directly. **Zheng *et al.* [@zheng2023]** examined language models as judges, documented position, verbosity and self-enhancement biases, and showed that strong judges agree with human preferences more than 80% of the time, which is the justification, and also the caveat, for the judged relevance study in Chapter 4. **Thakur *et al.* [@thakur2021]** (BEIR) found that BM25 is a robust zero-shot baseline that dense retrievers often fail to beat, which is why BM25 with the same filters is one of the baselines here. **Liu *et al.* [@liu2024]** showed that language models use information in the middle of long contexts poorly, and **Ji *et al.* [@ji2023]** surveyed hallucination in generated text; together they motivate keeping prompts short and keeping verdicts out of generated text.

**Greshake *et al.* [@greshake2023]** showed that when an application retrieves text that an adversary can write, instructions hidden in that text can take control of the language model, an attack they call indirect prompt injection. Model cards are exactly such text: anyone can publish one. The defence adopted in this work (delimiting and escaping card text, filtering citations, and above all making the verdict independent of the language model) responds directly to this paper. Finally, **Cohen [@cohen1960]** defined the kappa coefficient of chance-corrected agreement and **Landis and Koch [@landis1977]** gave the conventional interpretation of its values; both are used to report agreement between the two grading passes.

## Comparison of the surveyed work

@tab:compare compares the main works against the properties that this project needs. A "yes" means the work provides the property as part of its method; "no" means it does not, which is not a criticism of work with a different aim.

::: table compare size=8.5 cols=2.3,3.4,1.5,1.6,3.4
Comparison of selected related work against the requirements of constraint-verified model finding.
| Work | What it provides | Guaranteed hard constraints | Handles missing metadata | Gap for this problem |
|:--|:--|:-:|:-:|:--|
| RAG [@lewis2020] | Dense retrieval plus generation over a text corpus | no | no | Relevance only; no structured conditions |
| REALM, FiD, RETRO [@guu2020; @izacard2021; @borgeaud2022] | Learned retrieval; fusing many passages; very large stores | no | no | Same as RAG |
| Self-RAG [@asai2024] | Adaptive retrieval and self-critique | no (learned critique) | no | Critique is a model judgement |
| Dense retrieval and BM25 [@karpukhin2020; @robertson2009] | First-stage retrieval | no | n/a | No constraint semantics |
| Cross-encoder re-ranking [@nogueira2019] | More accurate ordering of a short list | no | n/a | Orders by relevance only |
| Filtered ANN [@gollapudi2023] | Search combined with label filters | yes, for labelled items | assumes labels present | Missing labels are not modelled |
| ReAct, PAL [@yao2023; @gao2023pal] | Reasoning with actions; code as reasoning | partly (code computes) | no | Not a selection method |
| HuggingGPT [@shen2023] | LLM selects Hub models by description | no | no | Selection by text; no verification |
| Model cards, datasheets [@mitchell2019; @gebru2021] | Documentation convention | n/a | n/a | Optional fields, no schema |
| Reuse study, licence audit [@jiang2023; @longpre2024] | Evidence that attributes and licences are missing or wrong | n/a | identifies the problem | No tool or remedy |
| Indic resources [@kakwani2020; @doddapaneni2023; @gala2023] | Corpora, benchmarks, models | n/a | n/a | Research artefacts, not a finder |
| RAGAs, LLM judges [@es2024; @zheng2023] | Reference-free metrics; judging | n/a | n/a | No measure of constraint violation |
| Indirect injection [@greshake2023] | Threat model for retrieved text | n/a | n/a | Motivates the defence |
| **This work** | Parse by LLM, verify in code, unknown as a verdict | **yes, by construction** | **yes** | Evaluated on 100 queries |
:::

## Gap analysis

Reading the literature against the problem of Chapter 1 leaves five gaps.

1. **No selection method guarantees hard constraints.** RAG and its variants optimise relevance, and the systems that let a language model choose a model [@shen2023] do so from descriptions. A recommendation that must be "under 500 MB and usable commercially" needs an exact comparison against metadata, which none of these provide.
2. **Missing metadata is not modelled.** Filtered search assumes the labels exist [@gollapudi2023]; production metadata filters drop items that lack the field; and the reuse and licensing studies [@jiang2023; @longpre2024] show that missing and wrong attributes are the normal case. A selection method needs a verdict for "the data does not say".
3. **Licences are displayed, not interpreted.** The documentation literature [@mitchell2019; @gebru2021] and the Hub filters treat a licence as a label; whether a licence permits commercial use or modification, or imposes conditions on derivatives, is left to the reader.
4. **The Indic long tail is under-served.** Corpora, benchmarks and flagship models exist [@kakwani2020; @doddapaneni2023; @gala2023], but community fine-tunes with few downloads and multilingual models that carry no language tag [@conneau2020; @radford2023] are invisible to popularity-ranked and tag-filtered search.
5. **Evaluation ignores constraint violation.** RAG metrics measure faithfulness and relevance [@es2024]; judges approximate preferences [@zheng2023]. Neither measures how often a recommended item breaks a stated requirement, which is the property a model finder must have.

## Problem definition

The gaps lead to the problem stated in Chapter 1 and to six objectives for the work:

1. Parse a natural-language request into a structured constraint record with a language model, and validate the result in code.
2. Verify every requested constraint in code against metadata, with the three verdicts pass, fail and unknown, and keep the verdict independent of any generated text.
3. Retrieve in a way that keeps models with unknown fields, rank fully verified models first, and state when none is fully verified.
4. Interpret licences as commercial-use and modification rights, and interpret size by a reproducible rule.
5. Cover the Indic long tail and multilingual models, ask clarifying questions for under-specified requests, and give beginners a starter snippet and adaptation information.
6. Evaluate the system against naive RAG, keyword search with filters and the Hub's own filters on queries fixed before tuning, with the limits of the evaluation stated.

## Summary

The literature supplies the components (dense and lexical retrieval, re-ranking, filtered search, tool-using language models, documentation conventions and evaluation methods) and the evidence that metadata on public hubs is incomplete and sometimes wrong. It does not supply a method that combines them into a model finder whose verdicts are exact and whose unknowns are explicit. The next chapter describes the design that fills that gap.
