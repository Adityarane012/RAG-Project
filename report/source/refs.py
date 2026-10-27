"""Verified reference data. Authors with more than six names are written 'First et al.' (IEEE). Venue facts were checked
against arXiv, the ACL Anthology, PMLR, NeurIPS proceedings, Crossref and the publisher pages (Oct 2026)."""
R = {}
def add(key, text):
    R[key] = text

# ---- retrieval-augmented generation
add("lewis2020", "P. Lewis *et al.*, \"Retrieval-augmented generation for knowledge-intensive NLP tasks,\" in *Advances in Neural Information Processing Systems*, vol. 33, 2020, pp. 9459–9474.")
add("guu2020", "K. Guu, K. Lee, Z. Tung, P. Pasupat, and M.-W. Chang, \"Retrieval augmented language model pre-training,\" in *Proc. 37th Int. Conf. Machine Learning (ICML)*, PMLR vol. 119, 2020, pp. 3929–3938.")
add("izacard2021", "G. Izacard and E. Grave, \"Leveraging passage retrieval with generative models for open domain question answering,\" in *Proc. 16th Conf. European Chapter of the Association for Computational Linguistics (EACL)*, 2021, pp. 874–880.")
add("borgeaud2022", "S. Borgeaud *et al.*, \"Improving language models by retrieving from trillions of tokens,\" in *Proc. 39th Int. Conf. Machine Learning (ICML)*, PMLR vol. 162, 2022, pp. 2206–2240.")
add("asai2024", "A. Asai, Z. Wu, Y. Wang, A. Sil, and H. Hajishirzi, \"Self-RAG: Learning to retrieve, generate, and critique through self-reflection,\" in *Proc. 12th Int. Conf. Learning Representations (ICLR)*, 2024. arXiv:2310.11511.")
add("gao2023rag", "Y. Gao *et al.*, \"Retrieval-augmented generation for large language models: A survey,\" arXiv:2312.10997, Dec. 2023.")
add("karpukhin2020", "V. Karpukhin *et al.*, \"Dense passage retrieval for open-domain question answering,\" in *Proc. Conf. Empirical Methods in Natural Language Processing (EMNLP)*, 2020, pp. 6769–6781.")
# ---- dense retrieval, ranking, indexing
add("reimers2019", "N. Reimers and I. Gurevych, \"Sentence-BERT: Sentence embeddings using Siamese BERT-networks,\" in *Proc. Conf. Empirical Methods in Natural Language Processing and 9th Int. Joint Conf. Natural Language Processing (EMNLP-IJCNLP)*, 2019, pp. 3982–3992.")
add("robertson2009", "S. Robertson and H. Zaragoza, \"The probabilistic relevance framework: BM25 and beyond,\" *Found. Trends Inf. Retr.*, vol. 3, no. 4, pp. 333–389, Dec. 2009.")
add("nogueira2019", "R. Nogueira and K. Cho, \"Passage re-ranking with BERT,\" arXiv:1901.04085, Jan. 2019.")
add("chen2024bge", "J. Chen, S. Xiao, P. Zhang, K. Luo, D. Lian, and Z. Liu, \"M3-Embedding: Multi-linguality, multi-functionality, multi-granularity text embeddings through self-knowledge distillation,\" in *Findings of the Association for Computational Linguistics: ACL 2024*, 2024, pp. 2318–2335.")
add("wang2024me5", "L. Wang, N. Yang, X. Huang, L. Yang, R. Majumder, and F. Wei, \"Multilingual E5 text embeddings: A technical report,\" arXiv:2402.05672, Feb. 2024.")
add("johnson2021", "J. Johnson, M. Douze, and H. Jégou, \"Billion-scale similarity search with GPUs,\" *IEEE Trans. Big Data*, vol. 7, no. 3, pp. 535–547, 2021.")
add("malkov2020", "Y. A. Malkov and D. A. Yashunin, \"Efficient and robust approximate nearest neighbor search using hierarchical navigable small world graphs,\" *IEEE Trans. Pattern Anal. Mach. Intell.*, vol. 42, no. 4, pp. 824–836, Apr. 2020.")
add("gollapudi2023", "S. Gollapudi *et al.*, \"Filtered-DiskANN: Graph algorithms for approximate nearest neighbor search with filters,\" in *Proc. ACM Web Conf. 2023 (WWW '23)*, 2023, pp. 3406–3416.")
add("devlin2019", "J. Devlin, M.-W. Chang, K. Lee, and K. Toutanova, \"BERT: Pre-training of deep bidirectional transformers for language understanding,\" in *Proc. Conf. North American Chapter of the Association for Computational Linguistics: Human Language Technologies (NAACL-HLT)*, 2019, pp. 4171–4186.")
add("vaswani2017", "A. Vaswani *et al.*, \"Attention is all you need,\" in *Advances in Neural Information Processing Systems*, vol. 30, 2017, pp. 5998–6008.")
add("conneau2020", "A. Conneau *et al.*, \"Unsupervised cross-lingual representation learning at scale,\" in *Proc. 58th Annu. Meeting of the Association for Computational Linguistics (ACL)*, 2020, pp. 8440–8451.")
# ---- LLMs that use tools
add("yao2023", "S. Yao *et al.*, \"ReAct: Synergizing reasoning and acting in language models,\" in *Proc. 11th Int. Conf. Learning Representations (ICLR)*, 2023. arXiv:2210.03629.")
add("gao2023pal", "L. Gao *et al.*, \"PAL: Program-aided language models,\" in *Proc. 40th Int. Conf. Machine Learning (ICML)*, PMLR vol. 202, 2023, pp. 10764–10799.")
add("shen2023", "Y. Shen, K. Song, X. Tan, D. Li, W. Lu, and Y. Zhuang, \"HuggingGPT: Solving AI tasks with ChatGPT and its friends in Hugging Face,\" in *Advances in Neural Information Processing Systems*, vol. 36, 2023. arXiv:2303.17580.")
# ---- evaluation and trust
add("es2024", "S. Es, J. James, L. Espinosa-Anke, and S. Schockaert, \"RAGAs: Automated evaluation of retrieval augmented generation,\" in *Proc. 18th Conf. European Chapter of the Association for Computational Linguistics: System Demonstrations*, 2024, pp. 150–158.")
add("zheng2023", "L. Zheng *et al.*, \"Judging LLM-as-a-judge with MT-Bench and Chatbot Arena,\" in *Advances in Neural Information Processing Systems*, vol. 36, Datasets and Benchmarks Track, 2023. arXiv:2306.05685.")
add("thakur2021", "N. Thakur, N. Reimers, A. Rücklé, A. Srivastava, and I. Gurevych, \"BEIR: A heterogenous benchmark for zero-shot evaluation of information retrieval models,\" in *Proc. 35th Conf. Neural Information Processing Systems, Datasets and Benchmarks Track*, 2021. arXiv:2104.08663.")
add("liu2024", "N. F. Liu *et al.*, \"Lost in the middle: How language models use long contexts,\" *Trans. Assoc. Comput. Linguist.*, vol. 12, pp. 157–173, 2024.")
add("ji2023", "Z. Ji *et al.*, \"Survey of hallucination in natural language generation,\" *ACM Comput. Surv.*, vol. 55, no. 12, pp. 1–38, Mar. 2023.")
add("greshake2023", "K. Greshake, S. Abdelnabi, S. Mishra, C. Endres, T. Holz, and M. Fritz, \"Not what you've signed up for: Compromising real-world LLM-integrated applications with indirect prompt injection,\" in *Proc. 16th ACM Workshop on Artificial Intelligence and Security (AISec '23)*, 2023, pp. 79–90.")
add("cohen1960", "J. Cohen, \"A coefficient of agreement for nominal scales,\" *Educ. Psychol. Meas.*, vol. 20, no. 1, pp. 37–46, Apr. 1960.")
add("landis1977", "J. R. Landis and G. G. Koch, \"The measurement of observer agreement for categorical data,\" *Biometrics*, vol. 33, no. 1, pp. 159–174, Mar. 1977.")
# ---- hubs, cards, licences
add("mitchell2019", "M. Mitchell *et al.*, \"Model cards for model reporting,\" in *Proc. Conf. Fairness, Accountability, and Transparency*, 2019, pp. 220–229.")
add("gebru2021", "T. Gebru *et al.*, \"Datasheets for datasets,\" *Commun. ACM*, vol. 64, no. 12, pp. 86–92, Dec. 2021.")
add("jiang2023", "W. Jiang *et al.*, \"An empirical study of pre-trained model reuse in the Hugging Face deep learning model registry,\" in *Proc. IEEE/ACM 45th Int. Conf. Software Engineering (ICSE)*, 2023, pp. 2463–2475.")
add("longpre2024", "S. Longpre *et al.*, \"A large-scale audit of dataset licensing and attribution in AI,\" *Nat. Mach. Intell.*, vol. 6, no. 8, pp. 975–987, Aug. 2024.")
# ---- Indic languages and models used
add("kakwani2020", "D. Kakwani *et al.*, \"IndicNLPSuite: Monolingual corpora, evaluation benchmarks and pre-trained multilingual language models for Indian languages,\" in *Findings of the Association for Computational Linguistics: EMNLP 2020*, 2020, pp. 4948–4961.")
add("doddapaneni2023", "S. Doddapaneni *et al.*, \"Towards leaving no Indic language behind: Building monolingual corpora, benchmark and models for Indic languages,\" in *Proc. 61st Annu. Meeting of the Association for Computational Linguistics (ACL), Vol. 1: Long Papers*, 2023, pp. 12402–12426.")
add("gala2023", "J. Gala *et al.*, \"IndicTrans2: Towards high-quality and accessible machine translation models for all 22 scheduled Indian languages,\" arXiv:2305.16307, May 2023.")
add("radford2023", "A. Radford, J. W. Kim, T. Xu, G. Brockman, C. McLeavey, and I. Sutskever, \"Robust speech recognition via large-scale weak supervision,\" in *Proc. 40th Int. Conf. Machine Learning (ICML)*, PMLR vol. 202, 2023, pp. 28492–28518.")
add("wolf2020", "T. Wolf *et al.*, \"Transformers: State-of-the-art natural language processing,\" in *Proc. Conf. Empirical Methods in Natural Language Processing: System Demonstrations*, 2020, pp. 38–45.")
add("openai2025", "OpenAI, \"gpt-oss-120b & gpt-oss-20b model card,\" arXiv:2508.10925, Aug. 2025.")
add("qwen2024", "Qwen Team, \"Qwen2.5 technical report,\" arXiv:2412.15115, Dec. 2024.")
# ---- web documentation (accessed 27 Oct 2026)
add("pineconefilter", "Pinecone Systems, Inc., \"Filter by metadata,\" Pinecone Documentation. [Online]. Available: https://docs.pinecone.io/guides/search/filter-by-metadata (accessed Oct. 27, 2026).")
add("pineconee5", "Pinecone Systems, Inc., \"multilingual-e5-large,\" Pinecone Documentation. [Online]. Available: https://docs.pinecone.io/models/multilingual-e5-large (accessed Oct. 27, 2026).")
add("pineconererank", "Pinecone Systems, Inc., \"bge-reranker-v2-m3,\" Pinecone Documentation. [Online]. Available: https://docs.pinecone.io/models/bge-reranker-v2-m3 (accessed Oct. 27, 2026).")
add("langgraph", "LangChain, Inc., \"LangGraph documentation.\" [Online]. Available: https://langchain-ai.github.io/langgraph/ (accessed Oct. 27, 2026).")
add("streamlit", "Snowflake Inc., \"Streamlit documentation.\" [Online]. Available: https://docs.streamlit.io/ (accessed Oct. 27, 2026).")
add("groqlimits", "Groq, Inc., \"Rate limits,\" GroqDocs. [Online]. Available: https://console.groq.com/docs/rate-limits (accessed Oct. 27, 2026).")
add("hfhub", "Hugging Face, Inc., \"Hub API endpoints,\" Hugging Face Hub Documentation. [Online]. Available: https://huggingface.co/docs/hub/api (accessed Oct. 27, 2026).")
add("hfcards", "Hugging Face, Inc., \"Model Cards,\" Hugging Face Hub Documentation. [Online]. Available: https://huggingface.co/docs/hub/model-cards (accessed Oct. 27, 2026).")
# ---- standards
add("ieee29148", "*Systems and Software Engineering — Life Cycle Processes — Requirements Engineering*, ISO/IEC/IEEE Standard 29148:2018, 2018.")
add("ieee1016", "*IEEE Standard for Information Technology — Systems Design — Software Design Descriptions*, IEEE Standard 1016-2009, 2009.")
add("ieee1012", "*IEEE Standard for System, Software, and Hardware Verification and Validation*, IEEE Standard 1012-2016, 2016.")
add("ieee29119", "*Software and Systems Engineering — Software Testing — Part 3: Test Documentation*, ISO/IEC/IEEE Standard 29119-3:2021, 2021.")
add("ieee7000", "*IEEE Standard Model Process for Addressing Ethical Concerns During System Design*, IEEE Standard 7000-2021, 2021.")
