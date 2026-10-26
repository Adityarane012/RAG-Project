"""Record every planned demo query (and its follow-ups) so the demo can be replayed with REPLAY=1.

    RECORD is implied. Run against the final index; re-run after ANY index or config change (a recording is a
    snapshot of what the system did at that moment).
    python -m scripts.record_demo [--plan demo/plan.json] [--dir demo/cache]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.replay import ReplayGraph


def run_plan(plan: dict, graphs: dict, directory: Path, log=print) -> list[dict]:
    """`graphs`: {"ours": graph, "naive": graph}. Mirrors app.py exactly: same request shape, same carried counters."""
    ours = ReplayGraph(graphs["ours"], "record", directory, variant="ours")
    naive = ReplayGraph(graphs["naive"], "record", directory, variant="naive") if "naive" in graphs else None
    report = []
    for step in plan["steps"]:
        request = {"query": step["query"], "overrides": {}}
        state = ours.invoke(request)
        row = {"step": step["name"], "outcome": state["outcome"], "recorded": [state["outcome"]]}
        if step.get("compare") and naive is not None:
            naive.invoke(request)
            row["recorded"].append("naive")
        carried = lambda s: {k: s[k] for k in ("clarifications_asked", "relax_count") if k in s}     # noqa: E731
        if step.get("clarify_choice") and state["outcome"] == "clarify":
            request2 = {"query": step["query"], "overrides": {state["question"]["field"]: step["clarify_choice"]}, **carried(state)}
            state2 = ours.invoke(request2)
            row["recorded"].append(state2["outcome"])
        if step.get("accept_relax") and state["outcome"] == "relax" and state.get("relax_offer"):
            offer = state["relax_offer"]
            request2 = {"query": step["query"], "overrides": {offer["field"]: offer["new_value"]}, **carried(state)}
            state2 = ours.invoke(request2)
            row["recorded"].append(state2["outcome"])
        for expect, key in ((step.get("clarify_choice"), "clarify"), (step.get("accept_relax"), "relax")):
            if expect and key not in row["recorded"]:
                row["warning"] = f"expected a '{key}' outcome to follow up on, but the first run was {state['outcome']!r}"
        report.append(row)
        log(f"  {step['name']}: {row['recorded']}" + (f"  WARNING: {row['warning']}" if "warning" in row else ""))
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", default="demo/plan.json")
    ap.add_argument("--dir", default="demo/cache")
    ap.add_argument("--only", default="", help="comma-separated 1-based step numbers to record (others keep their recordings)")
    args = ap.parse_args()
    from src.pipeline import build_pipeline

    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    if args.only:
        keep = {int(n) for n in args.only.split(",") if n.strip()}
        plan = {**plan, "steps": [st for i, st in enumerate(plan["steps"], 1) if i in keep]}
    report = run_plan(plan, {"ours": build_pipeline("ours"), "naive": build_pipeline("naive", explain=False)}, Path(args.dir))
    bad = [r for r in report if "warning" in r]
    print(f"recorded {sum(len(r['recorded']) for r in report)} states into {args.dir}; {len(bad)} step(s) need attention")
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
