# Literature Survey

## What others have done

**RAG.** Lewis *et al.* [@lewis2020] joined a text generator to a search system over Wikipedia, so the model could look things up. It gave better and more factual answers and the knowledge could be updated by changing the search index. But the retrieved items are plain text, so nothing forces them to satisfy a rule such as "under 500 MB". Gao *et al.* [@gao2023rag] review the whole family of RAG methods and group them into simple, advanced and modular designs. Our system is a modular RAG with one extra step: checking.

**Searching and ranking.** Karpukhin *et al.* [@karpukhin2020] showed that searching by meaning (dense retrieval) beats BM25 by 9 to 19 points on question answering. Robertson and Zaragoza [@robertson2009] describe BM25, the standard word-matching method, which we use as a baseline. Nogueira and Cho [@nogueira2019] used a BERT model to re-order search results and improved a standard benchmark by 27%; this is why we re-rank after searching. Wang *et al.* [@wang2024me5] built multilingual embeddings for about a hundred languages, and we use their model so that Hindi and Marathi requests work.

**Choosing models with a language model.** HuggingGPT [@shen2023] lets a language model read descriptions of Hugging Face models and pick some for a job. It decides from text only, so it never checks size, licence or language.

**Data quality.** Jiang *et al.* [@jiang2023] interviewed practitioners who reuse models from Hugging Face and found three problems: missing information, claims that do not match real performance, and risks. Longpre *et al.* [@longpre2024] checked more than 1,800 datasets and found licences missing in over 70% of cases and wrong in over 50% on popular hosting sites. This is why our tool says "unknown" and why it says that rights come from the *declared* licence.

**Safety and testing.** Greshake *et al.* [@greshake2023] showed that text fetched from the web can contain hidden instructions that take over a language model. Model cards can be written by anyone, so our checks never depend on what the language model says. Zheng *et al.* [@zheng2023] found that strong language models can grade other models' answers and agree with people more than 80% of the time, but have biases; we use this idea for grading and say so openly.

## Comparison

::: table compare size=8.5 cols=3.4,3.4,1.5,3
Related work compared with what this project needs.
| Work | What it gives | Checks hard rules? | Gap for this problem |
|:--|:--|:-:|:--|
| RAG [@lewis2020; @gao2023rag] | Search plus generation over text | no | Only checks relevance |
| Dense search, BM25, re-ranking [@karpukhin2020; @robertson2009; @nogueira2019] | Finding and ordering results | no | No idea of rules |
| HuggingGPT [@shen2023] | A language model picks Hub models | no | Picks from text, no checks |
| Reuse study, licence audit [@jiang2023; @longpre2024] | Shows data is missing or wrong | n/a | No tool |
| **This work** | Code checks every rule; "unknown" allowed | **yes** | Tested on 100 questions |
:::

## What is missing

Four gaps remain. (1) No method guarantees that suggested models follow the user's hard rules. (2) Missing data is not handled: the system needs to be able to say "the data does not say". (3) Licences are shown but not turned into rights such as "commercial use: yes or no". (4) Indian-language models, which are many but rarely downloaded, are hard to find. Our project fills these four gaps.
