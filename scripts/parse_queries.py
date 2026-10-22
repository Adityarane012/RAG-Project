"""Parse every evaluation query once (cached) and report extraction health WITHOUT changing any prompt or rule.
Writes eval/results/parsed_queries.json. Per the tuning policy, results here may only be reported, not tuned on."""
import json
import re
import time

from eval.metrics import load_queries
from src import llm
from src.guide import LANG_BY_NAME
from src.verify import SIZE_WORDS_MB

qs = load_queries("eval/queries.jsonl")
parsed, failures, t0 = {}, [], time.time()
for i, q in enumerate(qs, 1):
    try:
        parsed[q["id"]] = llm.extract_constraints(q["query"])
    except Exception as e:
        failures.append({"id": q["id"], "error": str(e)[:100]})
    if i % 20 == 0:
        print(f"  {i}/{len(qs)} parsed ({time.time() - t0:.0f}s)", flush=True)

# consistency checks between what the request says and what was extracted (reporting only)
issues = []
for q in qs:
    c = parsed.get(q["id"])
    if not c:
        continue
    text = q["query"].lower()
    words = [w.strip(".,;:!?()\"'").lower() for w in text.split()]
    named = {LANG_BY_NAME[w] for w in words if w in LANG_BY_NAME}
    if named - set(c["langs"]):
        issues.append((q["id"], "language named but not extracted", sorted(named - set(c["langs"]))))
    if re.search(r"\d\s*(gb|mb)\b", text) and c["max_size_mb"] is None:
        issues.append((q["id"], "explicit size not extracted", q["query"]))
    if any(re.search(rf"\b{w}\b", text) for w in SIZE_WORDS_MB) and c["max_size_mb"] is None and c["size_word"] is None:
        issues.append((q["id"], "size word not extracted", q["query"]))
    if q["kind"] == "normal" and c["task"] is None:
        issues.append((q["id"], "normal query without a task", q["query"]))
    if q["kind"] == "vague" and c["task"] is not None:
        issues.append((q["id"], "vague query that nevertheless got a task", (q["query"], c["task"])))
json.dump({"parsed": parsed, "failures": failures, "issues": issues}, open("eval/results/parsed_queries.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(f"parsed {len(parsed)}/{len(qs)}; failures {len(failures)}; consistency issues {len(issues)}")
for i in issues:
    print("  ", i)
