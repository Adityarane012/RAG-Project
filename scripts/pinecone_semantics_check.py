"""Live check of the Pinecone filter semantics the design relies on (D12; E-RET-9 to 12).

    python -m scripts.pinecone_semantics_check

Uses throwaway namespaces of a few vectors in the real index, builds the filters with our own `retrieve.build_filter`, and
removes the namespaces afterwards. Writes `eval/results/pinecone_semantics.json`. Costs a handful of read/write units.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from src import retrieve
from src.index import connect

DIM = 1024
NS_A, NS_B = "exp-semcheck-a", "exp-semcheck-b"


def vec(i: int) -> list[float]:
    v = [0.0] * DIM
    v[0], v[1 + i % 50] = 1.0, 0.1 * (1 + i)
    return v


def base(**k) -> dict:
    return {"task": "text-classification", "languages": ["hi"], "language_status": "known", "multilingual": False,
            "size_mb": 100.0, "size_status": "known", "commercial": "yes", "modifiable": "yes", "text": "t", **k}


def ids(res) -> set[str]:
    return {m["id"] for m in res["matches"]}


def query(index, ns: str, flt: dict) -> set[str]:
    for _ in range(30):                                   # serverless indexes are eventually consistent
        res = index.query(vector=vec(0), top_k=50, filter=flt or None, namespace=ns, include_metadata=False)
        if res["matches"]:
            return ids(res)
        time.sleep(2)
    return set()


def main() -> None:
    index = connect()
    rows = {
        "small": base(),                                                              # size 100: passes the size limit
        "big": base(size_mb=9000.0),                                                  # fails it
        "nosize": {k: v for k, v in base(size_status="unknown").items() if k != "size_mb"},   # unknown size: must be kept
        "mr_only": base(languages=["mr"]),
        "hi_mr": base(languages=["hi", "mr"]),
        "nolang": base(languages=[], language_status="unknown"),
        "noncommercial": base(commercial="no"),
        "conditional": base(commercial="conditional"),
        "translation": base(task="translation"),
        "multi": base(languages=[], language_status="unknown", multilingual=True),
    }
    index.upsert(vectors=[{"id": k, "values": vec(i), "metadata": m} for i, (k, m) in enumerate(rows.items())], namespace=NS_A)
    index.upsert(vectors=[{"id": "only_in_b", "values": vec(0), "metadata": base()}], namespace=NS_B)
    for _ in range(30):                                   # wait until everything is visible
        if len(query(index, NS_A, {})) == len(rows):
            break
        time.sleep(2)

    out: dict = {}
    c9 = query(index, NS_A, retrieve.build_filter({"task": "text-classification", "max_size_mb": 500}))
    out["E-RET-9 size $or keeps unknown-size, drops large"] = {"ok": "nosize" in c9 and "small" in c9 and "big" not in c9, "returned": sorted(c9)}
    c10 = query(index, NS_A, {"languages": {"$in": ["mr"]}})
    out["E-RET-10 $in on a list-valued field matches any element"] = {"ok": c10 == {"mr_only", "hi_mr"}, "returned": sorted(c10)}
    flt = retrieve.build_filter({"task": "text-classification", "langs": ["hi", "mr"], "max_size_mb": 500, "commercial": True})
    c11 = query(index, NS_A, flt)
    # both languages are required: a model must list hi AND mr, or have unknown languages, or be multilingual; conditional rights stay in
    expected = {"hi_mr", "nolang", "multi"}
    out["E-RET-11 $and of several $or clauses"] = {"ok": c11 == expected, "returned": sorted(c11), "expected": sorted(expected), "filter": flt}
    cb = query(index, NS_B, {})
    ca = query(index, NS_A, {})
    out["E-RET-12 namespaces never cross"] = {"ok": cb == {"only_in_b"} and "only_in_b" not in ca, "ns_b": sorted(cb)}
    for ns in (NS_A, NS_B):
        index.delete(delete_all=True, namespace=ns)
    out["all_ok"] = all(v["ok"] for v in out.values() if isinstance(v, dict))
    Path("eval/results/pinecone_semantics.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for k, v in out.items():
        print(k, "->", v["ok"] if isinstance(v, dict) else v)


if __name__ == "__main__":
    main()
