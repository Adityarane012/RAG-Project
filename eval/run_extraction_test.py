"""Run the extraction test against one model:  python -m eval.run_extraction_test [--model openai/gpt-oss-20b]

Scores the LLM alone and the LLM plus the deterministic backstop side by side (the second pass is free:
responses are cached by llm.complete). Writes eval/results/extraction_<model>.json."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

from eval.extraction import load_cases, score_case, summarise


def run(llm, backstop: bool) -> dict:
    results, failures, rows = [], 0, []
    for case in load_cases():
        try:
            got = llm.extract_constraints(case["query"], backstop=backstop)
        except ValueError as e:                         # not JSON: counted in the parse-success metric
            failures += 1
            rows.append({"id": case["id"], "query": case["query"], "error": str(e)[:120]})
            continue
        r = score_case(case["expect"], got)
        results.append(r)
        rows.append({"id": case["id"], "query": case["query"], "got": got, "expect": case["expect"],
                     "ok": r["all_correct"], "wrong": [f for f, ok in r["correct"].items() if not ok],
                     "silent_drops": r["silent_drops"], "invented": r["invented"]})
    return {"summary": summarise(results, failures), "cases": rows}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", help="override the pinned model for this run (GROQ_MODEL / OLLAMA_MODEL)")
    args = ap.parse_args()
    from src import llm

    if args.model:
        os.environ["OLLAMA_MODEL" if os.getenv("LLM_PROVIDER") == "ollama" else "GROQ_MODEL"] = args.model
    report = {label: run(llm, backstop) for label, backstop in (("llm_only", False), ("with_backstop", True))}
    name = re.sub(r"[^\w.-]+", "_", args.model or "pinned")
    out = Path("eval/results") / f"extraction_{name}.json"
    out.write_text(json.dumps({"model": args.model or "pinned", **report}, indent=1, ensure_ascii=False), encoding="utf-8")
    for label, rep in report.items():
        s = rep["summary"]
        print(f"{label:14s} parse={s['json_parse_success']:.0%} exact-match={s['exact_match_all_fields']:.0%} "
              f"silent-drops={s['silent_drops']} invented={s['invented_constraints']}")
        for r in rep["cases"]:
            if not r.get("ok", False):
                print("   MISS", r["id"], r["query"][:55], "->", r.get("wrong") or r.get("error"))


if __name__ == "__main__":
    main()
