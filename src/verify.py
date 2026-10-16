"""Re-verify every hard constraint in code: pass / fail / unknown (D2, D3).

The LLM never decides whether a model satisfies a constraint; these functions do.
"""

from __future__ import annotations

PASS, FAIL, UNKNOWN = "pass", "fail", "unknown"
ICON = {PASS: "✅", FAIL: "❌", UNKNOWN: "⚠️"}


def check_size(meta: dict, max_size_mb: float | None) -> str:
    if max_size_mb is None:
        return PASS
    if meta.get("size_status") != "known" or "size_mb" not in meta:
        return UNKNOWN
    return PASS if meta["size_mb"] <= max_size_mb else FAIL


def check_commercial(meta: dict, need_commercial: bool | None) -> str:
    if not need_commercial:
        return PASS
    status = meta.get("commercial", "unknown")
    if status == "yes":
        return PASS
    if status == "no":
        return FAIL
    # "conditional" needs a human to read the terms, so it is not a clean pass.
    return UNKNOWN


def check_languages(meta: dict, langs: list[str] | None) -> str:
    """All requested languages must be supported (e.g. hi AND mr for hi->mr)."""
    if not langs:
        return PASS
    have = meta.get("languages") or []
    if not have:
        return UNKNOWN
    return PASS if all(lang in have for lang in langs) else FAIL


def check_task(meta: dict, task: str | None) -> str:
    if not task:
        return PASS
    if not meta.get("task"):
        return UNKNOWN
    return PASS if meta["task"] == task else FAIL


def verify(meta: dict, constraints: dict) -> dict[str, str]:
    """Per-constraint result table for one model.

    `constraints` is the output of llm.extract_constraints():
        {task, langs, max_size_mb, commercial, soft_query}
    """
    return {
        "task": check_task(meta, constraints.get("task")),
        "languages": check_languages(meta, constraints.get("langs")),
        "size": check_size(meta, constraints.get("max_size_mb")),
        "commercial": check_commercial(meta, constraints.get("commercial")),
    }


def overall(results: dict[str, str]) -> str:
    """fail if anything fails, else unknown if anything is unknown, else pass."""
    values = results.values()
    if FAIL in values:
        return FAIL
    if UNKNOWN in values:
        return UNKNOWN
    return PASS


_RANK = {PASS: 0, UNKNOWN: 1, FAIL: 2}


def rank_key(results: dict[str, str]) -> tuple[int, int]:
    """Sort key: full passes first, then fewest unknowns (D12). Stable sort keeps
    the reranker's order within each group."""
    n_unknown = sum(1 for v in results.values() if v == UNKNOWN)
    return (_RANK[overall(results)], n_unknown)
