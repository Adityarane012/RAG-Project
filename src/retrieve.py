"""Filtered dense search, chunk -> model grouping (D4, D10, D12, D18).

Filters keep unknowns via an explicit $or so missing metadata is never silently
dropped; verify.py then marks those models ⚠️ and ranks them lower.
"""

from __future__ import annotations

from src.config import CFG
from src.verify import resolve_max_size_mb


def build_filter(constraints: dict) -> dict:
    """Pinecone metadata filter for the hard constraints in `constraints`."""
    clauses: list[dict] = []

    if constraints.get("task"):
        clauses.append({"task": {"$eq": constraints["task"]}})

    size_limit = resolve_max_size_mb(constraints.get("max_size_mb"), constraints.get("size_word"))
    if size_limit is not None:
        clauses.append({"$or": [
            {"size_mb": {"$lte": size_limit}},
            {"size_status": {"$eq": "unknown"}},
        ]})

    # Exclude only a definite "no"; conditional and unknown go on to verify.py.
    for right in ("commercial", "modifiable"):
        if constraints.get(right):
            clauses.append({right: {"$in": ["yes", "conditional", "unknown"]}})

    # Models from the multilingual map already have their covered languages merged into `languages`.
    for lang in constraints.get("langs") or []:
        clauses.append({"$or": [
            {"languages": {"$in": [lang]}},
            {"language_status": {"$eq": "unknown"}},
            {"multilingual": {"$eq": True}},     # list may be partial; verify decides (pass / unknown)
        ]})

    if not clauses:
        return {}
    return clauses[0] if len(clauses) == 1 else {"$and": clauses}


def group_by_model(matches: list[dict], top_n: int) -> list[dict]:
    """Collapse chunk matches to models, scored by their best chunk (D18).

    Each match is {"id", "score", "metadata": {...}}. Returns up to `top_n` models,
    best first, each with its best-scoring chunks under "chunks". Models are never
    re-sorted below the order of their best chunk, so a rerank carries through.
    """
    by_model: dict[str, dict] = {}
    for m in sorted(matches, key=lambda m: m["score"], reverse=True):
        model_id = m["metadata"]["model_id"]
        entry = by_model.setdefault(
            model_id, {"model_id": model_id, "score": m["score"], "meta": m["metadata"], "chunks": []}
        )
        entry["chunks"].append(m)
    return list(by_model.values())[:top_n]


def fetch_chunks(
    fetch_fn,
    constraints: dict,
    top_n: int | None = None,
    k: int | None = None,
    k_max: int | None = None,
) -> list[dict]:
    """Filtered chunk search, widening k until the chunks cover `top_n` distinct models (D18).

    `fetch_fn(filter, top_k) -> matches` wraps embed + index.query, so this loop is
    testable without Pinecone. Reranking only reorders chunks, so the distinct-model
    count can be checked before it.
    """
    top_n = top_n or CFG["retrieval"]["top_models"]
    k = k or CFG["retrieval"]["k_chunks"]
    k_max = k_max or CFG["retrieval"]["k_chunks_max"]
    flt = build_filter(constraints)
    while True:
        matches = fetch_fn(flt, k)
        distinct = {m["metadata"]["model_id"] for m in matches}
        # Stop when we have enough models, hit the cap, or the index has no more to give.
        if len(distinct) >= top_n or k >= k_max or len(matches) < k:
            return matches
        k = min(k * 2, k_max)


def pinecone_fetch(index, query_vector: list[float], namespace: str):
    """Build a `fetch_fn` over a Pinecone index. `query_vector` must come from the
    same embedding model used at index time (D8)."""
    def fetch(flt: dict, top_k: int) -> list[dict]:
        res = index.query(vector=query_vector, top_k=top_k, filter=flt or None,
                          namespace=namespace, include_metadata=True)
        return [{"id": m["id"], "score": m["score"], "metadata": m["metadata"]}
                for m in res["matches"]]
    return fetch
