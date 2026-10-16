from src.verify import FAIL, PASS, UNKNOWN, overall, rank_key, verify

C = {"task": "token-classification", "langs": ["mr"], "max_size_mb": 500, "commercial": True}


def meta(**kw):
    base = {"task": "token-classification", "languages": ["mr"], "size_status": "known",
            "size_mb": 400, "commercial": "yes"}
    base.update(kw)
    return base


def test_all_pass():
    assert overall(verify(meta(), C)) == PASS


def test_oversized_fails():
    assert verify(meta(size_mb=900), C)["size"] == FAIL


def test_missing_size_is_unknown_not_pass_or_fail():
    m = meta(size_status="unknown")
    del m["size_mb"]
    assert verify(m, C)["size"] == UNKNOWN


def test_commercial_mapping():
    assert verify(meta(commercial="no"), C)["commercial"] == FAIL
    assert verify(meta(commercial="conditional"), C)["commercial"] == UNKNOWN
    assert verify(meta(commercial="unknown"), C)["commercial"] == UNKNOWN


def test_languages_need_all_requested():
    c = {**C, "langs": ["hi", "mr"]}
    assert verify(meta(languages=["hi"]), c)["languages"] == FAIL
    assert verify(meta(languages=["hi", "mr", "en"]), c)["languages"] == PASS
    assert verify(meta(languages=[]), c)["languages"] == UNKNOWN


def test_unconstrained_passes():
    assert overall(verify(meta(commercial="no", size_mb=10_000), {})) == PASS


def test_ranking_puts_unknowns_below_passes_and_fails_last():
    results = [
        verify(meta(commercial="no"), C),
        verify(meta(commercial="unknown"), C),
        verify(meta(), C),
    ]
    ranked = sorted(results, key=rank_key)
    assert [overall(r) for r in ranked] == [PASS, UNKNOWN, FAIL]
