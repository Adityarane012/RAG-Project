"""Re-verify every hard constraint in code: pass / fail / unknown (D2, D3, D18).

The LLM never decides whether a model satisfies a constraint, and card text never
changes a result (D17). `verify` returns a row only for constraints the user asked
for, so the UI never shows a ✅ for something nobody requested.

Constraints dict (output of llm.extract_constraints, editable in the UI):
    task, langs, direction, max_size_mb, size_word, commercial, modifiable, soft_query
"""

from __future__ import annotations

from src.config import CFG

PASS, FAIL, UNKNOWN = "pass", "fail", "unknown"
ICON = {PASS: "✅", FAIL: "❌", UNKNOWN: "⚠️"}

# D18: vague size words -> thresholds. The LLM only picks a key; code supplies the number.
SIZE_WORDS_MB: dict[str, float] = dict(CFG["size_words_mb"])


def resolve_max_size_mb(max_size_mb: float | None, size_word: str | None) -> float | None:
    """An explicit number from the user wins; otherwise look the word up in the table."""
    if max_size_mb is not None:
        return max_size_mb
    if size_word:
        return SIZE_WORDS_MB.get(size_word.strip().lower())
    return None


def check_task(meta: dict, task: str | None) -> str:
    if not meta.get("task"):
        return UNKNOWN
    return PASS if meta["task"] == task else FAIL


def check_languages(meta: dict, langs: list[str]) -> str:
    """All requested languages must be supported (e.g. hi AND mr)."""
    have = meta.get("languages") or []
    if not have or meta.get("language_status") == "unknown":
        return UNKNOWN
    if all(lang in have for lang in langs):
        return PASS
    # A multilingual model's list may be partial (the card says "multilingual"), so absence is not proof.
    return UNKNOWN if meta.get("multilingual") else FAIL


def check_direction(meta: dict, direction: list[str]) -> str:
    """Translation direction [source, target]. Never `fail`, never claimed from the
    language list alone: a model listing hi and mr may not translate both ways, so
    direction is unknown unless the card states it (`directions`, written only then)."""
    stated = meta.get("directions") or []
    return PASS if f"{direction[0]}-{direction[1]}" in stated else UNKNOWN


def check_size(meta: dict, max_size_mb: float) -> str:
    if meta.get("size_status") != "known" or "size_mb" not in meta:
        return UNKNOWN
    return PASS if meta["size_mb"] <= max_size_mb else FAIL


def check_right(meta: dict, field: str) -> str:
    """`commercial` or `modifiable`. "conditional" needs a human to read the terms,
    so it is never a clean pass."""
    status = meta.get(field, "unknown")
    if status == "yes":
        return PASS
    if status == "no":
        return FAIL
    return UNKNOWN


def verify(meta: dict, constraints: dict) -> dict[str, str]:
    """Per-constraint result for one model, for the constraints that were requested."""
    results: dict[str, str] = {}
    if constraints.get("task"):
        results["task"] = check_task(meta, constraints["task"])
    if constraints.get("langs"):
        results["languages"] = check_languages(meta, constraints["langs"])
    if constraints.get("direction"):
        results["direction"] = check_direction(meta, constraints["direction"])
    size_limit = resolve_max_size_mb(constraints.get("max_size_mb"), constraints.get("size_word"))
    if size_limit is not None:
        results["size"] = check_size(meta, size_limit)
    if constraints.get("commercial"):
        results["commercial"] = check_right(meta, "commercial")
    if constraints.get("modifiable"):
        results["modifiable"] = check_right(meta, "modifiable")
    return results


def notes(meta: dict, constraints: dict) -> list[str]:
    """Caveats shown next to a ✅ (D18, D20). They never change a result."""
    out: list[str] = []
    if constraints.get("langs") and meta.get("multilingual"):
        wanted = ", ".join(constraints["langs"])
        out.append(f"multilingual, not specific to {wanted}")
    direction = constraints.get("direction")
    if direction and meta.get("direction_source") == "model_name" and f"{direction[0]}-{direction[1]}" in (meta.get("directions") or []):
        out.append("direction from model name")
    if meta.get("doc_quality") == "minimal":
        out.append("minimal documentation")
    return out


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
    """Sort key: full passes first, then fewest unknowns (D12). Python's sort is
    stable, so the reranker's order is kept within each group."""
    n_unknown = sum(1 for v in results.values() if v == UNKNOWN)
    return (_RANK[overall(results)], n_unknown)
