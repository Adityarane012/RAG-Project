"""An in-process vector index with Pinecone's `query` / `upsert` interface and metadata-filter semantics.

Why it exists: Pinecone (D4) is the production store, but the pipeline, the evaluation and the demo
recording must also run where Pinecone's data plane is unreachable. With ~30k vectors, exact brute-force
cosine search is instant, so this is a faithful stand-in, not an approximation: it is MORE exact than
Pinecone's approximate search. The filter evaluator implements the subset of Pinecone's filter language that
`retrieve.build_filter` emits: $and, $or, $eq, $in, $lte (plus $gte, $lt, $gt, $ne, $nin for completeness).

Pinecone semantics reproduced here (they matter, see D12):
  * a comparison against a field the record does not have is FALSE (so a record without `size_mb` never
    matches {"size_mb": {"$lte": 500}}, which is why the explicit `$or ... size_status unknown` exists);
  * `$in` on a list-valued field matches if ANY element is in the given set;
  * `$eq` on a list-valued field matches if the list CONTAINS the value.
Results are labelled `index_backend = "local"` in evaluation output so a comparison with Pinecone is explicit.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

_OPS = {"$eq", "$ne", "$in", "$nin", "$lt", "$lte", "$gt", "$gte", "$exists"}


def matches_filter(meta: dict, flt: dict | None) -> bool:
    """Does one record's metadata satisfy a Pinecone-style filter?"""
    if not flt:
        return True
    for key, cond in flt.items():
        if key == "$and":
            if not all(matches_filter(meta, c) for c in cond):
                return False
        elif key == "$or":
            if not any(matches_filter(meta, c) for c in cond):
                return False
        else:
            if not _field_ok(meta, key, cond):
                return False
    return True


def _field_ok(meta: dict, field: str, cond) -> bool:
    if not isinstance(cond, dict):          # {"field": value} is shorthand for $eq
        cond = {"$eq": cond}
    present = field in meta
    value = meta.get(field)
    for op, arg in cond.items():
        if op not in _OPS:
            raise ValueError(f"unsupported filter operator {op!r}")
        if op == "$exists":
            ok = present == bool(arg)
        elif not present:
            ok = False                       # a missing field matches nothing (D12), not even $ne / $nin
        elif op == "$eq":
            ok = arg in value if isinstance(value, list) else value == arg
        elif op == "$ne":
            ok = arg not in value if isinstance(value, list) else value != arg
        elif op == "$in":
            ok = any(v in arg for v in value) if isinstance(value, list) else value in arg
        elif op == "$nin":
            ok = not any(v in arg for v in value) if isinstance(value, list) else value not in arg
        else:                                 # numeric comparisons: only numbers compare
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                ok = False
            else:
                ok = {"$lt": value < arg, "$lte": value <= arg, "$gt": value > arg, "$gte": value >= arg}[op]
        if not ok:
            return False
    return True


class LocalIndex:
    """Pinecone-compatible: `.upsert(vectors, namespace)`, `.query(vector, top_k, filter, namespace, include_metadata)`."""

    def __init__(self):
        self._ns: dict[str, dict] = {}       # namespace -> {"ids": [...], "meta": [...], "vecs": np.ndarray (n, d), "pos": {id: row}}

    # -- writes ---------------------------------------------------------------------------------------------
    def upsert(self, vectors: list[dict], namespace: str = "") -> None:
        ns = self._ns.setdefault(namespace, {"ids": [], "meta": [], "vecs": np.zeros((0, 0), np.float32), "pos": {}})
        new_rows = []
        for v in vectors:
            vec = np.asarray(v["values"], dtype=np.float32)
            n = float(np.linalg.norm(vec))
            vec = vec / n if n else vec      # cosine == dot product on unit vectors
            if v["id"] in ns["pos"]:         # upsert replaces
                row = ns["pos"][v["id"]]
                ns["vecs"][row] = vec
                ns["meta"][row] = v.get("metadata", {})
            else:
                new_rows.append((v["id"], v.get("metadata", {}), vec))
        if new_rows:
            ids, metas, vecs = zip(*new_rows)
            stack = np.stack(vecs)
            ns["vecs"] = stack if ns["vecs"].size == 0 else np.vstack([ns["vecs"], stack])
            for i in ids:
                ns["pos"][i] = len(ns["ids"])
                ns["ids"].append(i)
            ns["meta"] += list(metas)

    def delete_namespace(self, namespace: str) -> None:
        self._ns.pop(namespace, None)

    def count(self, namespace: str = "") -> int:
        return len(self._ns.get(namespace, {}).get("ids", []))

    # -- reads ----------------------------------------------------------------------------------------------
    def query(self, vector, top_k: int = 10, filter: dict | None = None, namespace: str = "",
              include_metadata: bool = False, **_ignored) -> dict:
        ns = self._ns.get(namespace)
        if not ns or not ns["ids"]:
            return {"matches": [], "namespace": namespace}
        q = np.asarray(vector, dtype=np.float32)
        n = float(np.linalg.norm(q))
        q = q / n if n else q
        if filter:
            rows = np.array([i for i, m in enumerate(ns["meta"]) if matches_filter(m, filter)], dtype=int)
        else:
            rows = np.arange(len(ns["ids"]))
        if rows.size == 0:
            return {"matches": [], "namespace": namespace}
        scores = ns["vecs"][rows] @ q
        order = np.argsort(-scores, kind="stable")[:top_k]    # stable: ties keep insertion order (deterministic)
        matches = []
        for o in order:
            r = int(rows[o])
            m = {"id": ns["ids"][r], "score": float(scores[o])}
            if include_metadata:
                m["metadata"] = ns["meta"][r]
            matches.append(m)
        return {"matches": matches, "namespace": namespace}

    # -- persistence (so a built index loads in seconds) ---------------------------------------------------
    def save(self, directory: str | Path, namespace: str) -> Path:
        d = Path(directory)
        d.mkdir(parents=True, exist_ok=True)
        ns = self._ns[namespace]
        tmp = d / f"{namespace}.tmp.npz"
        np.savez(tmp, vecs=ns["vecs"])
        tmp.replace(d / f"{namespace}.npz")
        (d / f"{namespace}.meta.json").write_text(json.dumps({"ids": ns["ids"], "meta": ns["meta"]}, ensure_ascii=False), encoding="utf-8")
        return d / f"{namespace}.npz"

    @classmethod
    def load(cls, directory: str | Path, namespace: str) -> "LocalIndex":
        d = Path(directory)
        with np.load(d / f"{namespace}.npz") as z:
            vecs = z["vecs"].astype(np.float32)
        info = json.loads((d / f"{namespace}.meta.json").read_text(encoding="utf-8"))
        idx = cls()
        idx._ns[namespace] = {"ids": info["ids"], "meta": info["meta"], "vecs": vecs, "pos": {i: n for n, i in enumerate(info["ids"])}}
        return idx
