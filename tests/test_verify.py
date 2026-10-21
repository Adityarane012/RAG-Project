from src.verify import FAIL, PASS, UNKNOWN, notes, overall, rank_key, resolve_max_size_mb, verify

C = {"task": "token-classification", "langs": ["mr"], "max_size_mb": 500, "commercial": True}


def meta(**kw):
    base = {"task": "token-classification", "languages": ["mr"], "size_status": "known",
            "size_mb": 400, "commercial": "yes", "modifiable": "yes"}
    base.update(kw)
    return base


def test_all_pass():
    assert overall(verify(meta(), C)) == PASS


def test_only_requested_constraints_appear():
    assert set(verify(meta(), C)) == {"task", "languages", "size", "commercial"}
    assert verify(meta(commercial="no", size_mb=10_000), {}) == {}


def test_oversized_fails_and_boundary_passes():
    assert verify(meta(size_mb=900), C)["size"] == FAIL
    assert verify(meta(size_mb=500), C)["size"] == PASS


def test_missing_size_is_unknown_not_pass_or_fail():
    m = meta(size_status="unknown")
    del m["size_mb"]
    assert verify(m, C)["size"] == UNKNOWN


def test_rights_mapping():
    c = {"commercial": True, "modifiable": True}
    assert verify(meta(commercial="no"), c)["commercial"] == FAIL
    assert verify(meta(modifiable="no"), c)["modifiable"] == FAIL
    assert verify(meta(commercial="conditional"), c)["commercial"] == UNKNOWN
    assert verify(meta(modifiable="unknown"), c)["modifiable"] == UNKNOWN


def test_languages_need_all_requested():
    c = {"langs": ["hi", "mr"]}
    assert verify(meta(languages=["hi"]), c)["languages"] == FAIL
    assert verify(meta(languages=["hi", "mr", "en"]), c)["languages"] == PASS
    assert verify(meta(languages=[]), c)["languages"] == UNKNOWN


def test_direction_is_never_claimed_from_language_list_and_never_fails():
    c = {"task": "translation", "langs": ["hi", "mr"], "direction": ["hi", "mr"]}
    both_tagged = meta(task="translation", languages=["hi", "mr"])
    assert verify(both_tagged, c)["direction"] == UNKNOWN
    assert verify({**both_tagged, "directions": ["hi-mr"]}, c)["direction"] == PASS
    assert verify({**both_tagged, "directions": ["mr-hi"]}, c)["direction"] == UNKNOWN


def test_size_words_resolve_via_table_and_explicit_number_wins():
    assert resolve_max_size_mb(None, "small") == 500
    assert resolve_max_size_mb(None, "TINY") == 100
    assert resolve_max_size_mb(None, "medium") == 2000
    assert resolve_max_size_mb(300, "small") == 300
    assert resolve_max_size_mb(None, "huge") is None
    assert verify(meta(size_mb=600), {"size_word": "small"})["size"] == FAIL


def test_multilingual_and_minimal_doc_notes_never_change_results():
    m = meta(multilingual=True, doc_quality="minimal", languages=["hi", "mr"])
    c = {"langs": ["hi"]}
    assert verify(m, c)["languages"] == PASS
    assert notes(m, c) == ["multilingual, not specific to hi", "minimal documentation"]
    assert notes(meta(), {}) == []


def test_ranking_puts_unknowns_below_passes_and_fails_last():
    results = [verify(meta(commercial="no"), C), verify(meta(commercial="unknown"), C), verify(meta(), C)]
    assert [overall(r) for r in sorted(results, key=rank_key)] == [PASS, UNKNOWN, FAIL]


def test_missing_task_metadata_is_unknown_not_a_pass_or_fail():
    m = meta()
    del m["task"]
    assert verify(m, {"task": "translation"})["task"] == UNKNOWN


def test_a_zero_size_limit_fails_everything_with_a_known_size():
    assert verify(meta(size_mb=0.5), {"max_size_mb": 0})["size"] == FAIL


def test_equal_scores_keep_the_input_order():
    results = [verify(meta(), C), verify(meta(), C)]
    tagged = sorted(zip(["first", "second"], results), key=lambda t: rank_key(t[1]))
    assert [t[0] for t in tagged] == ["first", "second"]
