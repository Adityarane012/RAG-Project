"""Check-a-model mode (D23): paste a model id, get its rights, facts and build-on report: no retrieval.

Covers models in our snapshot only (the live-fetch extension was cut, D23). Reuses `verify` and
`adapt.model_report`, so the answer is computed by the same code as a search result.
"""

from __future__ import annotations

from src.adapt import build_lineage_index, model_report
from src.verify import verify


def find_model(model_id: str, records: list[dict]) -> dict | None:
    """Exact id first, then case-insensitively (the Hub treats ids case-insensitively)."""
    wanted = (model_id or "").strip()
    if not wanted:
        return None
    for r in records:
        if r["model_id"] == wanted:
            return r
    low = wanted.lower()
    return next((r for r in records if r["model_id"].lower() == low), None)


def facts(meta: dict) -> dict:
    """Plain-language facts about a model; every value is unknown rather than guessed when missing."""
    size = f"{meta['size_mb']:.0f} MB" if meta.get("size_status") == "known" and "size_mb" in meta else "unknown"
    return {
        "Task": meta.get("task") or "unknown",
        "Languages": ", ".join(meta.get("languages") or []) or "unknown",
        "Size": size,
        "Parameters": f"{meta['param_count']:,}" if meta.get("param_count") else "unknown",
        "Commercial use": meta.get("commercial", "unknown"),
        "Modification": meta.get("modifiable", "unknown"),
        "Based on": meta.get("base_model") or "not declared",
        "Documentation": meta.get("doc_quality", "unknown"),
    }


def check_model(model_id: str, records: list[dict], requirements: dict | None = None, lineage: dict | None = None) -> dict:
    """{"found": False, ...} or the facts, a verdict table for `requirements` (same keys as search constraints),
    and the build-on report."""
    meta = find_model(model_id, records)
    if meta is None:
        return {"found": False, "message": f"{model_id!r} is not in our snapshot of {len(records)} models. "
                                           "Check-a-model covers the snapshot only."}
    requirements = requirements or {}
    index = lineage if lineage is not None else build_lineage_index(records)
    return {"found": True, "meta": meta, "facts": facts(meta), "table": verify(meta, requirements),
            "report": model_report(meta, index, requirements.get("langs"))}
