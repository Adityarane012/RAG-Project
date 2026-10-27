from dg import *

def a_verify():
    fig, ax = canvas(6.6, 7.0, ylim=100)
    term(ax, 30, 93.5, 40, 4.5, "verify(meta, constraints)")
    steps = ["task requested?  \u2192 check_task: no task in metadata \u2192 UNKNOWN; equal \u2192 PASS; else FAIL",
             "languages requested?  \u2192 check_languages: none/unknown \u2192 UNKNOWN; all present \u2192 PASS;\n    else UNKNOWN if the model is multilingual (list may be partial), else FAIL",
             "direction requested?  \u2192 check_direction: PASS only if the card states it (opus-mt name); else UNKNOWN",
             "size limit (number, or word via size_words_mb)?  \u2192 check_size: size unknown \u2192 UNKNOWN;\n    size_mb \u2264 limit \u2192 PASS; else FAIL",
             "commercial / modifiable requested?  \u2192 check_right: yes \u2192 PASS; no \u2192 FAIL;\n    conditional or unknown \u2192 UNKNOWN"]
    y = 89
    prev = 93.5
    for s_ in steps:
        h = 8.0 if "\n" in s_ else 5.6
        arrow(ax, (50, prev), (50, y), lw=0.9)
        box(ax, 3, y - h, 94, h, s_, "code", 6.9, align="left")
        prev = y - h; y = y - h - 3.0
    arrow(ax, (50, prev), (50, prev - 3.0), lw=0.9)
    label(ax, 3, prev - 5.6, "One result per requested constraint; constraints nobody asked for get no row. Then:", 7.0, MUTED, italic=True)
    cy = 24
    diamond(ax, 19, cy, 33, 13, "any result\n= FAIL ?", "unk", 7.2)
    diamond(ax, 57, cy, 33, 13, "any result\n= UNKNOWN ?", "unk", 7.0)
    arrow(ax, (35.5, cy), (40.5, cy)); label(ax, 38, cy + 2, "no", 6.8, MUTED, ha="center")
    arrow(ax, (73.5, cy), (77, cy)); label(ax, 75.3, cy + 2, "no", 6.8, MUTED, ha="center")
    box(ax, 77, cy - 4.5, 21, 9, "overall = PASS\n(fully verified)", "pass", 6.8, bold=True)
    arrow(ax, (19, cy - 6.5), (19, 12.5)); label(ax, 20.5, 15, "yes", 6.8, MUTED)
    arrow(ax, (57, cy - 6.5), (57, 12.5)); label(ax, 58.5, 15, "yes", 6.8, MUTED)
    box(ax, 3, 4, 32, 8.5, "overall = FAIL\n(never recommended)", "fail", 6.8, bold=True)
    box(ax, 41, 4, 32, 8.5, "overall = UNKNOWN\n(shown, flagged)", "unk", 6.8, bold=True)
    label(ax, 77, 8.2, "rank_key = (PASS < UNKNOWN\n< FAIL, #unknown rows);\nstable sort keeps the\nreranker order in a group", 6.2, MUTED, italic=True)
    save(fig, "fig_a_verify")

def a_filter():
    fig, ax = canvas(6.6, 4.6, ylim=100)
    term(ax, 30, 93, 40, 5, "build_filter(constraints)")
    rows = [("task", "{ task: { $eq: task } }"),
            ("size limit", "{ $or: [ { size_mb: { $lte: limit } },\n         { size_status: { $eq: \"unknown\" } } ] }"),
            ("commercial / modifiable", "{ commercial: { $in: [yes, conditional, unknown] } }\n(only a definite \"no\" is removed)"),
            ("each language", "{ $or: [ { languages: { $in: [lang] } },\n         { language_status: { $eq: \"unknown\" } },\n         { multilingual: { $eq: true } } ] }")]
    y = 84
    for k, (name, txt) in enumerate(rows):
        h = 11 if "\n" in txt else 7
        if txt.count("\n") == 2: h = 15
        box(ax, 3, y - h, 24, h, f"if {name}\nrequested", "ui", 7.0)
        box(ax, 32, y - h, 65, h, txt, "code", 6.9, align="left")
        arrow(ax, (27, y - h / 2), (32, y - h / 2), lw=0.9)
        y -= h + 3.5
    box(ax, 3, y - 9, 94, 9, "no clause → {}  (search unfiltered)   |   one clause → that clause   |   several → { $and: [ ... ] }", "data", 7.2, bold=True)
    label(ax, 3, y - 15, "Every clause keeps a model whose field is unknown; verify() later marks it UNKNOWN and ranks it lower, so the", 6.9, MUTED, italic=True)
    label(ax, 3, y - 20, "filter is a loose pre-selection and never decides pass or fail.", 6.9, MUTED, italic=True)
    save(fig, "fig_a_filter")

def a_size():
    fig, ax = canvas(6.6, 4.0, ylim=100)
    term(ax, 3, 90, 34, 6, "size_mb(files)  (rule D20)")
    diamond(ax, 20, 72, 36, 15, "top-level .safetensors\nfiles exist?", "unk", 6.9)
    diamond(ax, 20, 46, 36, 15, "top-level .bin\nfiles exist?", "unk", 6.9)
    arrow(ax, (20, 90), (20, 79.5)); arrow(ax, (20, 64.5), (20, 53.5)); label(ax, 21.5, 59, "no", 6.8, MUTED)
    box(ax, 41, 66, 22, 12, "use those files", "code", 7.0); arrow(ax, (38, 72), (41, 72)); label(ax, 39.5, 75, "yes", 6.8, MUTED, ha="center")
    box(ax, 41, 40, 22, 12, "use those files", "code", 7.0); arrow(ax, (38, 46), (41, 46)); label(ax, 39.5, 49, "yes", 6.8, MUTED, ha="center")
    diamond(ax, 83, 59, 26, 18, "any chosen file\nwithout a\nrecorded size?", "unk", 6.3)
    arrow(ax, (63, 72), (70.5, 62)); arrow(ax, (63, 46), (70.5, 56))
    box(ax, 72, 80, 26, 12, "size UNKNOWN", "unk", 7.0, bold=True)
    arrow(ax, (83, 68), (83, 80)); label(ax, 84.5, 74, "yes", 6.8, MUTED)
    box(ax, 72, 28, 26, 14, "size_mb = bytes of the\nchosen files / 1,000,000\n(exact, unrounded)", "pass", 6.6, bold=True)
    arrow(ax, (83, 50), (83, 42)); label(ax, 84.5, 46, "no", 6.8, MUTED)
    arrow(ax, (20, 38.5), (20, 22)); label(ax, 21.5, 30, "no", 6.8, MUTED)
    box(ax, 3, 13, 34, 9, "size UNKNOWN", "unk", 7.0, bold=True)
    label(ax, 3, 7, "reason recorded: no weight files, GGUF only, weights under another name,", 6.5, MUTED, italic=True)
    label(ax, 3, 2.8, "weights only in a sub-folder, or adapter only", 6.5, MUTED, italic=True)
    save(fig, "fig_a_size")

def a_extract():
    fig, ax = canvas(6.6, 5.0, ylim=100)
    term(ax, 3, 92, 34, 5, "user request (text)")
    steps = [("out-of-scope check (regex): image, OCR or speech-synthesis request?\nyes \u2192 refuse with a message; no LLM call, no search", "fail", 9),
             ("LLM, JSON mode, reasoning effort low: task, langs, direction, size,\ncommercial, modifiable, soft_query", "llm", 9),
             ("clean_constraints: validate against the schema; anything off-schema\n(unknown task, bad number, non-boolean) becomes null", "code", 9),
             ("backstop_constraints: skipped if the query looks like an instruction (\"ignore ...\",\n\"set commercial to ...\"). Otherwise fills only what the LLM left empty:\nsize number (MB/GB), one size word, commercial / modifiable keywords,\npermissive-license phrase, exactly one task keyword, language names;\nrejects an unsupported text-generation guess", "code", 17),
             ("the user's edits (overrides) are laid over the result and validated again (None clears)", "code", 6),
             ("constraints \u2192 clarifying question if the task or languages are missing", "ui", 6)]
    prev, y = 92, 87.5
    for t, k, h in steps:
        arrow(ax, (50, prev), (50, y), lw=0.9)
        box(ax, 3, y - h, 94, h, t, k, 6.9, align="left")
        prev, y = y - h, y - h - 3.6
    save(fig, "fig_a_extract")

def a_llm():
    fig, ax = canvas(6.6, 4.4, ylim=100)
    term(ax, 3, 90, 30, 6, "complete(prompt, system)")
    diamond(ax, 20, 72, 34, 14, "answer cached for\n(provider, model,\nsystem, prompt)?", "unk", 6.4)
    box(ax, 41, 66, 24, 12, "return the stored\nresponse", "pass", 6.9, bold=True); arrow(ax, (37, 72), (41, 72)); label(ax, 39, 75, "yes", 6.8, MUTED, ha="center")
    arrow(ax, (18, 90), (20, 79)); arrow(ax, (20, 65), (20, 56)); label(ax, 21.5, 60.5, "no", 6.8, MUTED)
    box(ax, 3, 42, 34, 14, "TokenBudget.acquire(estimate)\nsleep until the last 60 s\nhave room (8,000 tokens/min)", "code", 6.7)
    arrow(ax, (20, 42), (20, 36))
    box(ax, 3, 24, 34, 12, "call the pinned model\n(gpt-oss-20b via Groq,\nor Ollama locally)", "llm", 6.7)
    arrow(ax, (37, 30), (45, 30))
    diamond(ax, 60, 30, 28, 16, "rate-limit\nerror?", "unk", 6.8)
    arrow(ax, (60, 38), (60, 52)); label(ax, 61.5, 45, "no", 6.8, MUTED)
    box(ax, 47, 52, 26, 12, "settle the budget with\nreal usage; cache the\nanswer; return it", "pass", 6.5, bold=True)
    arrow(ax, (74, 30), (79, 30)); label(ax, 76.5, 33, "yes", 6.8, MUTED, ha="center")
    box(ax, 79, 18, 19, 24, "retry-after \u2264 30 s:\nwait, retry once.\nElse (or if it fails\nagain): try the\nfallback model\ngpt-oss-120b once", "code", 6.3)
    label(ax, 3, 12, "Errors that are not rate limits are raised. The cache records which model really answered, so", 6.6, MUTED, italic=True)
    label(ax, 3, 7.5, "replayed runs (evaluation, demo) are deterministic and cost no tokens.", 6.6, MUTED, italic=True)
    save(fig, "fig_a_llm")

if __name__ == "__main__":
    a_verify(); a_filter(); a_size(); a_extract(); a_llm()
