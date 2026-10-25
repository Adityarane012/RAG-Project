"""Replay every query in demo/plan.json from demo/cache/ and check it, with no network and no LLM.

    REPLAY=1 python -m scripts.rehearse_demo

This is an automated check that the recording is complete and sensible. It is NOT a human rehearsal. Exits non-zero if any
step is missing from the cache or lacks the outcome the plan expects.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from src.replay import ReplayGraph


def check_step(step: dict, ours: ReplayGraph, naive: ReplayGraph) -> list[str]:
    """Replay one plan step; return a list of problems (empty means fine)."""
    problems = []
    request = {"query": step["query"], "overrides": {}}
    state = ours.invoke(request)
    line = f"  ours: {state['outcome']}"
    if step.get("clarify_choice"):
        if state["outcome"] != "clarify":
            problems.append(f"expected a clarifying question, got {state['outcome']}")
        else:
            follow = ours.invoke({"query": step["query"], "overrides": {state["question"]["field"]: step["clarify_choice"]},
                                  "clarifications_asked": state.get("clarifications_asked", 1)})
            state, line = follow, line + f" -> after choosing {step['clarify_choice']}: {follow['outcome']}"
    if state["outcome"] == "answer":
        counts = Counter(r["overall"] for r in state["results"])
        line += f" | {len(state['results'])} models {dict(counts)} | fully verified: {state.get('fully_verified')}"
        if not state["results"]:
            problems.append("answer with no models")
    elif not step.get("clarify_choice"):
        problems.append(f"unexpected outcome {state['outcome']}")
    print(line)
    if step.get("compare"):
        other = naive.invoke(request)
        counts = Counter(r["overall"] for r in other.get("results", []))
        print(f"  naive: {len(other.get('results', []))} models {dict(counts)}")
        if not other.get("results"):
            problems.append("naive comparison is empty")
    return problems


def main() -> int:
    plan = json.loads(Path("demo/plan.json").read_text(encoding="utf-8"))
    ours, naive = ReplayGraph(mode="replay", variant="ours"), ReplayGraph(mode="replay", variant="naive")
    failures = 0
    for i, step in enumerate(plan["steps"], 1):
        print(f"Step {i}: {step['name']}\n  query: {step['query']!r}")
        try:
            problems = check_step(step, ours, naive)
        except Exception as e:      # a step that was never recorded raises here
            problems = [f"{type(e).__name__}: {e}"]
        for p in problems:
            print(f"  PROBLEM: {p}")
        failures += bool(problems)
    print(f"\n{len(plan['steps']) - failures} of {len(plan['steps'])} steps replayed cleanly from demo/cache/ (no network used).")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
