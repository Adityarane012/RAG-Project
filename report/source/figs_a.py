from dg import *

def request():
    fig, ax = canvas(6.6, 3.5, ylim=100)
    box(ax, 4, 78, 92, 14, "“A Marathi NER model under 500 MB, usable commercially,\nthat works well on noisy social-media text.”", "ui", 9.4, bold=True)
    box(ax, 4, 22, 52, 42, "", "code", 8)
    label(ax, 6.5, 59.5, "Hard constraints", 9.4, INK, bold=True)
    label(ax, 6.5, 53.5, "verified by code: pass / fail / unknown", 7.6, MUTED, italic=True)
    for i, t in enumerate(["task = token-classification (NER)", "language = Marathi (mr)", "size ≤ 500 MB", "commercial use = required"]):
        label(ax, 8.2, 45.5 - i * 6.4, "•  " + t, 8.4, INK)
    box(ax, 60, 22, 36, 42, "", "llm", 8)
    label(ax, 62.5, 59.5, "Soft preference", 9.4, INK, bold=True)
    label(ax, 62.5, 53.5, "ranked by meaning, explained", 7.6, MUTED, italic=True)
    label(ax, 64.2, 44.5, "•  works well on noisy\n    social-media text", 8.4, INK)
    arrow(ax, (30, 78), (30, 64.5)); arrow(ax, (78, 78), (78, 64.5))
    label(ax, 4, 12, "Keyword search cannot do the soft part; the Hub's license filter matches a string, not a right;", 7.6, MUTED)
    label(ax, 4, 6.5, "plain RAG ignores the hard part and recommends whatever sounds relevant.", 7.6, MUTED)
    save(fig, "fig_request")

def related():
    fig, ax = canvas(6.6, 4.9, ylim=100)
    col = [(2, "Retrieval-augmented generation", "Lewis et al.; REALM; FiD; RETRO;\nSelf-RAG; Gao et al. survey"),
           (35, "Dense retrieval and ranking", "DPR; SBERT; BM25; BERT re-ranking;\nBGE-M3; mE5; FAISS; HNSW;\nFiltered-DiskANN"),
           (68, "LLMs that use tools", "ReAct; PAL (program-aided);\nHuggingGPT (LLM picks Hub models)")]
    label(ax, 2, 94, "Six strands of prior work (Chapter 2) and the gap between them", 8.6, INK, bold=True)
    for x, h, t in col:
        box(ax, x, 62, 30, 24, "", "code", 8)
        label(ax, x + 1.5, 82, h, 8.2, INK, bold=True)
        label(ax, x + 1.5, 71.5, t, 7.4, INK)
    for x, h, t in [(2, "Hubs, cards and licensing", "Model cards; datasheets; reuse on the\nHub (Jiang et al.); dataset license audit"),
                    (35, "Evaluation and trust", "RAGAS; LLM-as-judge; BEIR;\nlost-in-the-middle; hallucination survey;\nindirect prompt injection"),
                    (68, "Indic language resources", "IndicNLPSuite; IndicXTREME;\nIndicTrans2; XLM-R; Whisper")]:
        box(ax, x, 33, 30, 24, "", "data", 8)
        label(ax, x + 1.5, 53, h, 8.2, INK, bold=True)
        label(ax, x + 1.5, 42.5, t, 7.4, INK)
    box(ax, 12, 3, 76, 22, "", "unk", 8)
    label(ax, 14, 21, "The gap this work addresses", 8.8, INK, bold=True)
    label(ax, 14, 11.5, "No system returns models that provably satisfy size, license rights, language and task,\nshows honest “unknown” where metadata is missing, and covers the Indic long tail.", 7.7, INK)
    for x in (17, 50, 83):
        arrow(ax, (x, 33), (50, 25.5))
    save(fig, "fig_related")

def pipeline():
    fig, ax = canvas(6.6, 3.9, ylim=100)
    W, H = 27, 15
    xs = [2, 36, 70]
    top = [("Hugging Face Hub API", "11 tasks; top 1,000 by downloads\n(+ Indic-tagged for language tasks)\n15,991 models", "data"),
           ("ingest (resumable)", "cached card + metadata,\nbackoff on rate limits,\ncanonical base-model ids", "code"),
           ("normalize + clean", "size rule, license rights,\nlanguages, doc quality;\nunknown fields marked", "code")]
    bot = [("index + snapshot", "Pinecone prod / local index;\nsha256-checksummed snapshot\n(48,179 vectors)", "data"),
           ("embed (cached)", "multilingual-e5-large, 1,024-d;\ncontent-hash cache;\n4.05 M hosted tokens in all", "code"),
           ("chunk by section", "drop boilerplate sections;\n≤ 4 chunks per model\n(3.0 per model)", "code")]
    for (t, d, k), x in zip(top, xs):
        box(ax, x, 52, W, H + 8, "", k, 8); label(ax, x + 1.3, 70, t, 8.2, INK, bold=True); label(ax, x + 1.3, 59.5, d, 7.2, INK)
    for (t, d, k), x in zip(bot, xs):
        box(ax, x, 10, W, H + 8, "", k, 8); label(ax, x + 1.3, 28, t, 8.2, INK, bold=True); label(ax, x + 1.3, 17.5, d, 7.2, INK)
    arrow(ax, (29, 63), (36, 63)); arrow(ax, (63, 63), (70, 63))
    arrow(ax, (83.5, 52), (83.5, 33), None)
    arrow(ax, (70, 21), (63, 21)); arrow(ax, (36, 21), (29, 21))
    label(ax, 2, 90, "Offline data pipeline (run once per snapshot; every stage is resumable and cached)", 8.6, INK, bold=True)
    save(fig, "fig_pipeline")

def graph():
    fig, ax = canvas(6.6, 4.2, ylim=100)
    y = 56
    nodes = [("extract", 2, "llm"), ("retrieve", 21, "code"), ("rerank", 40, "code"), ("verify", 59, "code"), ("enrich", 78, "code")]
    for t, x, k in nodes:
        box(ax, x, y, 15, 10, t, k, 8.4, bold=True)
    for a, b in [(17, 21), (36, 40), (55, 59), (74, 78)]:
        arrow(ax, (a, y + 5), (b, y + 5))
    label(ax, 2, 94, "START \u2192 extract. Branches off the straight path:", 7.6, MUTED, italic=True)
    box(ax, 2, 76, 20, 12, "clarify  (\u2264 2)\nask for a missing\ntask or language", "ui", 7.4, bold=False)
    box(ax, 28, 76, 22, 12, "out_of_scope\nimage, OCR or speech\nsynthesis request", "fail", 7.4)
    arrow(ax, (7, y + 10), (7, 76))
    arrow(ax, (13, y + 10), (35, 76))
    label(ax, 52, 82, "\u2192 END (refusal;\n    no search)", 7.2, MUTED)
    # explain
    box(ax, 78, 34, 15, 10, "explain", "llm", 8.4, bold=True)
    arrow(ax, (85.5, y), (85.5, 44))
    label(ax, 85.5, 28, "\u2192 END: answer", 7.2, MUTED, ha="center")
    # branches from verify
    box(ax, 30, 30, 20, 11, "relax  (\u2264 1)\noffer to loosen\none constraint", "ui", 7.4)
    box(ax, 58, 8, 17, 11, "abstain\n(no model)", "fail", 7.6, bold=True)
    arrow(ax, (62, y), (46, 41))
    label(ax, 50, 49, "no viable model,\nrelaxation exists", 7, MUTED, ha="right")
    arrow(ax, (67, y), (67, 19))
    label(ax, 65.5, 38, "no viable model,\nnothing to relax", 7, MUTED, ha="right")
    label(ax, 2, 24, "Clarify and relax end the run. The UI shows the question, then calls the graph again\nwith the user's answer in `overrides` and the counters carried over.", 7.2, MUTED)
    label(ax, 2, 14.5, "viable = at least one result that is not FAIL", 7.2, MUTED, italic=True)
    legend(ax, 2, 2, [("llm", "LLM node"), ("code", "code node"), ("ui", "waits for the user"), ("fail", "ends with no model")], dx=22)
    save(fig, "fig_graph")

def verification():
    fig, ax = canvas(6.6, 3.9, ylim=100)
    box(ax, 2, 62, 28, 28, "", "data", 8)
    label(ax, 3.5, 86, "Model metadata", 8.4, INK, bold=True)
    label(ax, 3.5, 72.5, "task, languages,\nlanguage_status, size_mb,\nsize_status, commercial,\nmodifiable, directions", 7.3, INK)
    box(ax, 2, 18, 28, 36, "", "ui", 8)
    label(ax, 3.5, 50, "Requested constraints", 8.4, INK, bold=True)
    label(ax, 3.5, 35, "only what the user asked:\ntask, languages, direction,\nmax size (or size word),\ncommercial, modifiable", 7.3, INK)
    box(ax, 38, 38, 26, 52, "", "code", 8)
    label(ax, 39.5, 86, "check_*()", 8.4, INK, bold=True)
    label(ax, 39.5, 59, "one row per requested\nconstraint:\n\npass  → meets it\nfail   → definitely not\nunknown → metadata\n               does not say", 7.2, INK)
    arrow(ax, (30, 76), (38, 76)); arrow(ax, (30, 36), (38, 52))
    box(ax, 72, 70, 26, 20, "any fail →\nFAIL\n(never recommended)", "fail", 7.8, bold=True)
    box(ax, 72, 44, 26, 20, "else any unknown →\nUNKNOWN\n(shown, flagged)", "unk", 7.8, bold=True)
    box(ax, 72, 18, 26, 20, "else\nPASS\n(fully verified)", "pass", 7.8, bold=True)
    arrow(ax, (64, 64), (72, 80)); arrow(ax, (64, 64), (72, 54)); arrow(ax, (64, 64), (72, 28))
    label(ax, 38, 28, "rank_key = (PASS < UNKNOWN < FAIL,\nfewest unknowns); sort is stable,\nso the reranker order breaks ties", 7.3, MUTED)
    label(ax, 2, 6, "“Conditional” rights (e.g. share-alike, revenue thresholds) and a language list that may be partial are never a clean pass.", 7.2, MUTED, italic=True)
    save(fig, "fig_verification")

