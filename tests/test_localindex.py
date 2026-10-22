"""LocalIndex must behave like Pinecone for every filter retrieve.build_filter can emit. The scenario below
is the one run against real Pinecone as the Phase 1 check (tests/live) so the two can be compared directly."""
import numpy as np
import pytest

from src.localindex import LocalIndex, matches_filter
from src.retrieve import build_filter


def base(**k):
    return {"model_id": "m", "task": "translation", **k}


M = {
    "v1": base(size_mb=100.0, size_status="known", languages=["hi"], language_status="known", multilingual=False, commercial="yes", modifiable="yes"),
    "v2": base(size_mb=900.0, size_status="known", languages=["hi"], language_status="known", multilingual=False, commercial="yes", modifiable="yes"),
    "v3": base(size_status="unknown", languages=["hi"], language_status="known", multilingual=False, commercial="unknown", modifiable="unknown"),
    "v4": base(size_mb=300.0, size_status="known", languages=["mr", "hi"], language_status="known", multilingual=False, commercial="conditional", modifiable="conditional"),
    "v5": base(size_mb=300.0, size_status="known", languages=[], language_status="unknown", multilingual=False, commercial="yes", modifiable="no"),
    "v6": base(size_mb=300.0, size_status="known", languages=["ta"], language_status="known", multilingual=True, commercial="yes", modifiable="yes"),
    "v7": base(size_mb=300.0, size_status="known", languages=["ta"], language_status="known", multilingual=False, commercial="yes", modifiable="yes"),
    "v8": base(size_mb=300.0, size_status="known", languages=["hi"], language_status="known", multilingual=False, commercial="no", modifiable="yes"),
    "v9": base(task="automatic-speech-recognition", size_mb=300.0, size_status="known", languages=["hi"], language_status="known", multilingual=False, commercial="yes", modifiable="yes"),
    "v10": base(size_mb=500.0, size_status="known", languages=["hi"], language_status="known", multilingual=False, commercial="yes", modifiable="yes"),
}


def ids_for(constraints):
    flt = build_filter(constraints)
    return sorted(k for k, m in M.items() if matches_filter(m, flt))


def test_size_filter_keeps_unknown_size_and_drops_big_but_a_bare_lte_would_drop_the_unknown():
    assert ids_for({"task": "translation", "max_size_mb": 500}) == ["v1", "v10", "v3", "v4", "v5", "v6", "v7", "v8"]
    assert not matches_filter(M["v3"], {"size_mb": {"$lte": 500}})        # the silent drop D12 exists to prevent
    assert matches_filter(M["v10"], {"size_mb": {"$lte": 500}})            # boundary is inclusive


def test_language_filter_keeps_listed_unknown_and_multilingual_models():
    assert ids_for({"task": "translation", "langs": ["hi"]}) == ["v1", "v10", "v2", "v3", "v4", "v5", "v6", "v8"]   # not v7 (ta only)
    assert ids_for({"task": "translation", "langs": ["hi", "mr"]}) == ["v4", "v5", "v6"]


def test_rights_filters_drop_only_definite_no():
    assert "v8" not in ids_for({"task": "translation", "commercial": True}) and "v3" in ids_for({"task": "translation", "commercial": True})
    assert "v5" not in ids_for({"task": "translation", "modifiable": True})


def test_all_constraints_together_and_the_task_filter():
    assert ids_for({"task": "translation", "max_size_mb": 500, "langs": ["hi"], "commercial": True, "modifiable": True}) == ["v1", "v10", "v3", "v4", "v6"]
    assert ids_for({"task": "automatic-speech-recognition"}) == ["v9"]
    assert len(ids_for({})) == 10                                              # no filter keeps everything


def test_pinecone_semantics_for_missing_fields_lists_and_operators():
    assert not matches_filter({}, {"x": {"$ne": 1}})                  # missing field matches nothing, not even $ne
    assert matches_filter({"l": ["a", "b"]}, {"l": {"$in": ["b", "z"]}}) and not matches_filter({"l": ["a"]}, {"l": {"$in": ["z"]}})
    assert matches_filter({"l": ["a", "b"]}, {"l": {"$eq": "a"}}) and matches_filter({"l": ["a"]}, {"l": "a"})
    assert matches_filter({"n": 3}, {"n": {"$gte": 3, "$lt": 4}}) and not matches_filter({"n": True}, {"n": {"$lte": 5}})
    assert matches_filter({"a": 1}, {"$or": [{"a": 2}, {"a": 1}]}) and not matches_filter({"a": 1}, {"$and": [{"a": 1}, {"a": 2}]})
    assert matches_filter({"a": 1}, {"b": {"$exists": False}})
    with pytest.raises(ValueError):
        matches_filter({"a": 1}, {"a": {"$regex": "x"}})


def vec(*xs):
    v = np.zeros(8, dtype=np.float32)
    v[:len(xs)] = xs
    return v.tolist()


def test_query_ranks_by_cosine_applies_the_filter_and_returns_pinecone_shaped_matches():
    idx = LocalIndex()
    idx.upsert([{"id": "a", "values": vec(1, 0), "metadata": {"k": 1}}, {"id": "b", "values": vec(0.9, 0.1), "metadata": {"k": 2}},
                {"id": "c", "values": vec(0, 1), "metadata": {"k": 1}}], namespace="ns")
    res = idx.query(vec(1, 0), top_k=2, namespace="ns", include_metadata=True)
    assert [m["id"] for m in res["matches"]] == ["a", "b"] and res["matches"][0]["score"] == pytest.approx(1.0)
    assert res["matches"][0]["metadata"] == {"k": 1}
    res = idx.query(vec(1, 0), top_k=5, filter={"k": {"$eq": 1}}, namespace="ns")
    assert [m["id"] for m in res["matches"]] == ["a", "c"] and "metadata" not in res["matches"][0]
    assert idx.query(vec(1, 0), namespace="other")["matches"] == [] and idx.query(vec(1, 0), filter={"k": 99}, namespace="ns")["matches"] == []


def test_upsert_replaces_by_id_normalises_and_namespaces_are_isolated():
    idx = LocalIndex()
    idx.upsert([{"id": "a", "values": vec(5, 0), "metadata": {"v": 1}}], namespace="n1")
    idx.upsert([{"id": "a", "values": vec(0, 5), "metadata": {"v": 2}}, {"id": "b", "values": vec(1, 1)}], namespace="n1")
    idx.upsert([{"id": "z", "values": vec(1, 0)}], namespace="n2")
    assert idx.count("n1") == 2 and idx.count("n2") == 1 and idx.count("nope") == 0
    top = idx.query(vec(0, 1), top_k=1, namespace="n1", include_metadata=True)["matches"][0]
    assert top["id"] == "a" and top["metadata"] == {"v": 2} and top["score"] == pytest.approx(1.0)   # replaced + normalised
    idx.delete_namespace("n1")
    assert idx.count("n1") == 0 and idx.count("n2") == 1


def test_ties_are_broken_by_insertion_order_and_save_load_round_trips(tmp_path):
    idx = LocalIndex()
    idx.upsert([{"id": i, "values": vec(1, 0), "metadata": {"i": n}} for n, i in enumerate("pqr")], namespace="ns")
    assert [m["id"] for m in idx.query(vec(1, 0), top_k=3, namespace="ns")["matches"]] == ["p", "q", "r"]
    idx.save(tmp_path, "ns")
    again = LocalIndex.load(tmp_path, "ns")
    assert again.count("ns") == 3
    assert again.query(vec(1, 0), top_k=3, namespace="ns", include_metadata=True) == idx.query(vec(1, 0), top_k=3, namespace="ns", include_metadata=True)
    assert not list(tmp_path.glob("*.tmp*"))
