"""Filtered dense search over Pinecone (D4, D10, D12).

Filters keep unknowns via an explicit $or so that missing metadata is never
silently dropped; verify.py then marks those models ⚠️ and ranks them lower.
"""

from __future__ import annotations


def build_filter(constraints: dict) -> dict:
    """Pinecone metadata filter for the hard constraints in `constraints`."""
    clauses: list[dict] = []

    task = constraints.get("task")
    if task:
        clauses.append({"task": {"$eq": task}})

    max_size_mb = constraints.get("max_size_mb")
    if max_size_mb is not None:
        clauses.append({"$or": [
            {"size_mb": {"$lte": max_size_mb}},
            {"size_status": {"$eq": "unknown"}},
        ]})

    if constraints.get("commercial"):
        # Exclude only definite "no"; conditional and unknown go to verify.py.
        clauses.append({"commercial": {"$in": ["yes", "conditional", "unknown"]}})

    for lang in constraints.get("langs") or []:
        clauses.append({"$or": [
            {"languages": {"$in": [lang]}},
            {"language_status": {"$eq": "unknown"}},
        ]})

    if not clauses:
        return {}
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def search(index, query_vector: list[float], constraints: dict, top_k: int = 50):
    """Filtered dense search. `query_vector` must come from the same embedding
    model used at index time (D8)."""
    return index.query(
        vector=query_vector,
        top_k=top_k,
        filter=build_filter(constraints) or None,
        include_metadata=True,
    )
