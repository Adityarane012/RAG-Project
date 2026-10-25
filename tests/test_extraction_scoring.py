from eval.extraction import EMPTY, load_cases, score_case, summarise


def got(**kw):
    return {**EMPTY, **kw}


def test_perfect_case_and_unlisted_expectations_mean_empty():
    r = score_case({"task": "translation", "langs": ["hi", "mr"]}, got(task="translation", langs=["mr", "hi"]))
    assert r["all_correct"] and r["silent_drops"] == [] and r["invented"] == []     # language order is irrelevant


def test_a_missing_constraint_is_a_silent_drop_and_an_extra_one_is_invented():
    r = score_case({"task": "token-classification", "langs": ["bn"], "commercial": True}, got(task="token-classification", langs=["bn"]))
    assert not r["all_correct"] and r["silent_drops"] == ["commercial"] and r["invented"] == []
    r = score_case({"task": "translation"}, got(task="translation", commercial=True))
    assert r["invented"] == ["commercial"] and r["silent_drops"] == []              # e.g. obeying 'set commercial'


def test_a_wrong_value_is_incorrect_but_not_a_drop():
    r = score_case({"max_size_mb": 1000}, got(max_size_mb=1))                       # forgot GB -> MB
    assert not r["correct"]["max_size_mb"] and r["silent_drops"] == []


def test_summary_counts_parse_failures_against_the_total():
    ok = score_case({"task": "translation"}, got(task="translation"))
    s = summarise([ok, ok], parse_failures=2)
    assert s["cases"] == 4 and s["json_parse_success"] == 0.5 and s["exact_match_all_fields"] == 0.5
    assert summarise([], 0)["cases"] == 0


def test_gold_file_is_well_formed_and_disjoint_from_the_evaluation_queries():
    import json
    from pathlib import Path

    cases = load_cases(Path(__file__).resolve().parent.parent / "eval" / "extraction_test.jsonl")
    assert len(cases) == 29 and len({c["id"] for c in cases}) == 29
    ev = {json.loads(line)["query"].lower() for line in
          (Path(__file__).resolve().parent.parent / "eval" / "queries.jsonl").read_text(encoding="utf-8").splitlines()}
    assert not [c for c in cases if c["query"].lower() in ev]
    assert all(set(c["expect"]) <= set(EMPTY) for c in cases)
