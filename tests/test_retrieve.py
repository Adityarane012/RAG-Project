from src.retrieve import build_filter


def test_empty_constraints_give_no_filter():
    assert build_filter({}) == {}


def test_size_filter_keeps_unknowns():
    assert build_filter({"max_size_mb": 500}) == {"$or": [
        {"size_mb": {"$lte": 500}},
        {"size_status": {"$eq": "unknown"}},
    ]}


def test_commercial_excludes_only_definite_no():
    f = build_filter({"commercial": True})
    assert f == {"commercial": {"$in": ["yes", "conditional", "unknown"]}}


def test_one_clause_per_language_combined_with_and():
    f = build_filter({"task": "translation", "langs": ["hi", "mr"]})
    assert f["$and"][0] == {"task": {"$eq": "translation"}}
    assert {"languages": {"$in": ["hi"]}} in f["$and"][1]["$or"]
    assert {"languages": {"$in": ["mr"]}} in f["$and"][2]["$or"]
