from src.retrieve import build_filter, fetch_chunks, group_by_model


def match(model_id, score, i=0):
    return {"id": f"{model_id}::{i}", "score": score, "metadata": {"model_id": model_id}}


def test_empty_constraints_give_no_filter():
    assert build_filter({}) == {}


def test_size_filter_keeps_unknowns_and_resolves_words():
    expected = {"$or": [{"size_mb": {"$lte": 500}}, {"size_status": {"$eq": "unknown"}}]}
    assert build_filter({"max_size_mb": 500}) == expected
    assert build_filter({"size_word": "small"}) == expected


def test_rights_exclude_only_definite_no():
    allowed = ["yes", "conditional", "unknown"]
    assert build_filter({"commercial": True}) == {"commercial": {"$in": allowed}}
    assert build_filter({"modifiable": True}) == {"modifiable": {"$in": allowed}}


def test_one_clause_per_language_combined_with_and():
    f = build_filter({"task": "translation", "langs": ["hi", "mr"]})
    assert f["$and"][0] == {"task": {"$eq": "translation"}}
    assert {"languages": {"$in": ["hi"]}} in f["$and"][1]["$or"]
    assert {"language_status": {"$eq": "unknown"}} in f["$and"][2]["$or"]


def test_grouping_scores_a_model_by_its_best_chunk_and_dedupes():
    matches = [match("a", 0.9, 0), match("a", 0.8, 1), match("a", 0.7, 2), match("b", 0.85), match("c", 0.5)]
    models = group_by_model(matches, top_n=2)
    assert [m["model_id"] for m in models] == ["a", "b"]
    assert models[0]["score"] == 0.9 and len(models[0]["chunks"]) == 3


def test_fetch_widens_k_until_enough_distinct_models():
    pool = [match("a", 0.9, i) for i in range(8)] + [match(c, 0.5 - i / 100) for i, c in enumerate("bcdef")]
    calls = []

    def fetch(flt, k):
        calls.append(k)
        return pool[:k]

    got = fetch_chunks(fetch, {}, top_n=5, k=4, k_max=64)
    assert len({m["metadata"]["model_id"] for m in got}) >= 5
    assert calls == sorted(calls) and calls[0] == 4 and len(calls) > 1


def test_fetch_stops_when_index_is_exhausted_or_capped():
    calls = []

    def fetch(flt, k):
        calls.append(k)
        return [match("a", 0.9)]  # fewer than k: nothing more to get

    fetch_chunks(fetch, {}, top_n=5, k=10, k_max=100)
    assert calls == [10]
