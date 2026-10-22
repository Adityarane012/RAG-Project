"""Generate the explanations that are scored by hand for faithfulness (D11).

    python -m scripts.make_faithfulness_set [--n 30]

Runs the full system (with explanations) on `--n` of the queries in the blind relevance sheet, picks one explained model
per query at random (seeded), and writes `eval/labels/faithfulness_sheet.csv`: the explanation next to the exact card
passages the model was given, so a reader can check each claim against them. The LLM cache makes a rerun free, and the
same explanations are what the demo recording reuses. Costs about 3,000 Groq tokens per query.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path

from eval.metrics import load_queries
from src import pipeline
from src.evidence import select_evidence

OUT = Path("eval/labels/faithfulness_sheet.csv")


def query_ids_from_sheet(path: Path = Path("eval/labels/relevance_sheet.csv")) -> list[str]:
    with open(path, encoding="utf-8", newline="") as f:
        return sorted({r["query_id"] for r in csv.DictReader(f)})


def pick(explanations: list[dict], rng: random.Random) -> dict | None:
    usable = [e for e in explanations if (e.get("text") or "").strip()]
    return rng.choice(sorted(usable, key=lambda e: e["model_id"])) if usable else None


def evidence_text(state: dict, model_id: str, query: str) -> str:
    """The passages the explainer was shown for this model (the selection is deterministic)."""
    shown = [r for r in state["results"] if r["overall"] != "fail"]
    for e in select_evidence(shown, query):
        if e["model_id"] == model_id:
            return "\n\n".join(f"[{p['section']}]\n{p['text']}" for p in e["passages"])
    return ""


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30)
    args = ap.parse_args(argv)
    queries = {q["id"]: q for q in load_queries("eval/queries.jsonl")}
    ids = query_ids_from_sheet()
    rng = random.Random(2026)
    chosen = sorted(rng.sample(ids, min(args.n, len(ids))))
    graph = pipeline.build_pipeline("ours")
    rows = []
    for i, qid in enumerate(chosen, 1):
        q = queries[qid]["query"]
        state = graph.invoke({"query": q})
        e = pick(state.get("explanations") or [], rng) if state.get("outcome") == "answer" else None
        print(f"{i}/{len(chosen)} {qid}: {'explained ' + e['model_id'] if e else 'no explanation (' + str(state.get('explain_error') or state.get('outcome')) + ')'}")
        if e:
            rows.append({"item_id": f"{qid}|{e['model_id']}", "request": q, "model_id": e["model_id"], "explanation": e["text"],
                         "cited_sections": json.dumps(e.get("cited_sections") or [], ensure_ascii=False),
                         "evidence": evidence_text(state, e["model_id"], q)})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["item_id", "request", "model_id", "explanation", "cited_sections", "evidence"])
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} items to {OUT}")


if __name__ == "__main__":
    main()
