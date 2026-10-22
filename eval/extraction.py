"""Constraint-extraction accuracy test (D7): does the LLM turn a request into the right constraints?

A miss silently drops a constraint (the model then returns things that violate it), so besides
per-field accuracy we count *silent drops*: the query states something and the output is empty.
Gold cases live in eval/extraction_test.jsonl and are deliberately disjoint from eval/queries.jsonl,
so tuning the extraction prompt on them cannot contaminate the evaluation set.
"""

from __future__ import annotations

import json
from pathlib import Path

FIELDS = ("task", "langs", "direction", "max_size_mb", "size_word", "commercial", "modifiable")
EMPTY = {"task": None, "langs": [], "direction": None, "max_size_mb": None, "size_word": None,
         "commercial": None, "modifiable": None}


def load_cases(path: str | Path = "eval/extraction_test.jsonl") -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def _norm(field: str, value):
    if field == "langs":
        return sorted(value or [])
    return value


def score_case(expected: dict, got: dict) -> dict:
    """Per-field correctness for one case. Unlisted expected fields mean 'must be empty'."""
    want = {**EMPTY, **expected}
    correct = {f: _norm(f, got.get(f)) == _norm(f, want[f]) for f in FIELDS}
    # direction implies its languages, so a stated direction is not wrong just because langs echo it
    dropped = [f for f in FIELDS if want[f] not in (None, []) and got.get(f) in (None, [])]
    invented = [f for f in FIELDS if want[f] in (None, []) and got.get(f) not in (None, [])]
    return {"correct": correct, "all_correct": all(correct.values()), "silent_drops": dropped, "invented": invented}


def summarise(results: list[dict], parse_failures: int = 0) -> dict:
    n = len(results) + parse_failures
    per_field = {f: sum(r["correct"][f] for r in results) / max(len(results), 1) for f in FIELDS}
    return {
        "cases": n,
        "json_parse_success": (len(results)) / n if n else 0.0,
        "exact_match_all_fields": sum(r["all_correct"] for r in results) / n if n else 0.0,
        "per_field_accuracy": per_field,
        "silent_drops": sum(len(r["silent_drops"]) for r in results),
        "invented_constraints": sum(len(r["invented"]) for r in results),
    }
