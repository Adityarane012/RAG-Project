from dg import *

def funnel():
    fig, ax = canvas(6.6, 4.1, ylim=100)
    rows = [("Index", "48,179 chunks of 15,990 models (11 tasks)", 44, "data"),
            ("Metadata filter", "task, size, rights, language; models with unknown fields are kept ($or)", 38, "code"),
            ("Dense search", "k = 50 chunks, doubled up to 400 until at least 100 distinct models", 32, "code"),
            ("Rerank", "cross-encoder (bge-reranker-v2-m3) reorders the chunks", 27, "code"),
            ("Verify 100 models", "pass / fail / unknown for each requested constraint, in code", 22, "code"),
            ("Sort and cut", "PASS first, fewest unknowns next, rerank order breaks ties; keep 5", 17, "code"),
            ("Answer", "fails dropped; unknowns shown and flagged; explanation added", 12, "ui")]
    y = 80
    for i, (t, d, w, k) in enumerate(rows):
        box(ax, 2, y, w, 9, t, k, 8.2, bold=True)
        label(ax, 2 + w + 2.5, y + 4.5, d, 7.6, INK)
        if i < len(rows) - 1:
            arrow(ax, (2 + w / 2, y), (2 + w / 2, y - 3.2), lw=0.9)
        y -= 12.5
    label(ax, 2, 94.5, "Retrieval and verification funnel (box widths are schematic, not to scale)", 8.4, INK, bold=True)
    save(fig, "fig_funnel")

def injection():
    fig, ax = canvas(6.6, 3.8, ylim=100)
    label(ax, 2, 95, "Untrusted card text never reaches a decision", 8.6, INK, bold=True)
    box(ax, 2, 62, 24, 24, "Model card text\\n(third party;\\nmay contain\\n“ignore previous\\ninstructions”)".replace("\\n", "\n"), "fail", 7.4)
    box(ax, 33, 62, 28, 24, "Wrapped as data\n<card_section> tags;\nany literal tag inside the\ncard is escaped; system\nprompt says: data, not orders", "code", 7.2)
    box(ax, 68, 62, 30, 24, "LLM writes a cited\nexplanation (JSON)", "llm", 7.6, bold=True)
    arrow(ax, (26, 74), (33, 74)); arrow(ax, (61, 74), (68, 74))
    box(ax, 68, 28, 30, 24, "Citation filter\ndrops any citation\nnot among the candidates\nshown to the model", "code", 7.4)
    arrow(ax, (83, 62), (83, 52))
    box(ax, 33, 28, 28, 24, "Pass / fail / unknown table\ncomes from metadata only;\nthe LLM never sets it", "pass", 7.4, bold=True)
    box(ax, 2, 28, 24, 24, "Streamlit page:\ntable + explanation\nside by side", "ui", 7.6)
    arrow(ax, (68, 40), (61, 40)); arrow(ax, (33, 40), (26, 40))
    label(ax, 2, 18, "Checked by a poisoned-card test: three hostile cards (authority spoof, delimiter break, citation bait) with unknown", 7.0, MUTED)
    label(ax, 2, 12, "metadata, five runs each: the table came from metadata only, 0 of 5 explanations repeated an injected claim.", 7.0, MUTED)
    save(fig, "fig_injection")

def evaldesign():
    fig, ax = canvas(6.6, 4.6, ylim=100)
    box(ax, 2, 80, 28, 15, "100 queries written before\nany tuning: 75 normal,\n15 vague, 10 impossible", "ui", 7.4)
    box(ax, 36, 80, 24, 15, "LLM parses each query\nonce; parses are frozen", "llm", 7.4)
    box(ax, 66, 72, 32, 23, "5 systems, same queries:\nours (verified RAG) \u00b7 naive RAG\nkeyword BM25 + filters\nHF Hub basic filters\nHF Hub license-aware filters", "code", 7.2)
    arrow(ax, (30, 87.5), (36, 87.5)); arrow(ax, (60, 87.5), (66, 87.5))
    box(ax, 2, 58, 96, 8, "Outputs frozen (v2) before any grading; every system is judged with the same verify() rules", "note", 7.4, bold=True)
    arrow(ax, (82, 72), (82, 66))
    for x, t, k in [(2, "Automatic metrics\nviolation %, unknown %, fully verified %,\nanswered %, latency; no-verified slice", "code"),
                    (35, "LLM-judged relevance (blind)\n40 queries, 686 pairs, grades 0 / 1 / 2,\ntwo passes, Cohen's kappa", "llm"),
                    (68, "Behaviour of the full system\nclarify on vague queries;\nbanner when nothing fully passes", "code")]:
        box(ax, x, 32, 30, 18, t, k, 6.9)
        arrow(ax, (x + 15, 58), (x + 15, 50))
    label(ax, 2, 25, "Further checks", 7.6, INK, bold=True)
    for x, t, k in [(2, "Explanation faithfulness\n28 explanations, 98 claims", "llm"),
                    (35, "Poisoned-card test\n3 hostile cards, 5 runs each", "code"),
                    (68, "Try-it smoke test\ntemplate run on 32 small models", "code")]:
        box(ax, x, 5, 30, 15, t, k, 7.0)
    save(fig, "fig_evaldesign")

if __name__ == "__main__":
    funnel(); injection(); evaldesign()
