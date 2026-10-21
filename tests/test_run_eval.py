import csv
import json

from eval.run_eval import (evaluate, export_label_sheet, feasibility, outcome_from_hub, outcome_from_state, render_markdown,
                           sample_for_labelling, system_metrics)
from src.verify import FAIL, PASS, UNKNOWN

C = {"task": "text-classification", "langs": ["hi"], "max_size_mb": 500, "commercial": True, "soft_query": "hindi sentiment"}


def meta(**k):
    return {"model_id": "m", "task": "text-classification", "languages": ["hi"], "language_status": "known", "size_status": "known",
            "size_mb": 100.0, "commercial": "yes", "modifiable": "yes", **k}


def result(mid, overall, table=None, **m):
    return {"model_id": mid, "overall": overall, "table": table or {"size": overall}, "meta": meta(**m)}


def test_ours_recommends_only_non_failing_models_and_nothing_when_it_asks_or_abstains():
    state = {"outcome": "answer", "results": [result("a", PASS), result("b", UNKNOWN), result("c", FAIL)], "fully_verified": True}
    assert [m["model_id"] for m in outcome_from_state("ours", state, C)["top"]] == ["a", "b"]
    assert outcome_from_state("naive", state, C)["top"][-1]["model_id"] == "c"             # a baseline recommends its whole top-k
    for oc in ("clarify", "relax", "abstain"):
        assert outcome_from_state("ours", {"outcome": oc, "results": [result("a", PASS)], "question": {"field": "task"}}, C)["top"] == []
    assert outcome_from_state("ours", state, C, k=1)["top"] == outcome_from_state("ours", state, C)["top"][:1]


def test_hub_results_are_judged_with_our_rules_and_unresolvable_models_are_counted_not_guessed():
    metas = {"x/ok": meta(), "x/big": meta(size_mb=9000.0)}
    o = outcome_from_hub(["x/ok", "x/big", "x/gone"], C, metas.get)
    assert [(m["model_id"], m["overall"]) for m in o["top"]] == [("x/ok", PASS), ("x/big", FAIL)] and o["unresolved"] == 1


def top(*specs):
    return {"outcome": "answer", "latency_s": 1.0, "top": [{"model_id": i, "overall": o, "table": t} for i, o, t in specs]}


def test_metrics_count_violations_unknowns_answers_and_break_down_by_constraint():
    rows = [top(("a", PASS, {"size": PASS, "commercial": PASS}), ("b", FAIL, {"size": FAIL, "commercial": PASS}), ("c", UNKNOWN, {"size": UNKNOWN, "commercial": PASS})),
            {"outcome": "clarify", "latency_s": 3.0, "top": []}]
    m = system_metrics(rows)
    assert m["queries"] == 2 and m["answered_pct"] == 50.0 and m["recommendations"] == 3
    assert (m["violation_pct"], m["unknown_pct"], m["fully_verified_pct"]) == (33.3, 33.3, 33.3)
    assert m["violation_by_constraint_pct"] == {"commercial": 0.0, "size": 33.3} and m["latency_median_s"] == 2.0
    empty = system_metrics([])
    assert empty["violation_pct"] is None and empty["latency_median_s"] is None          # no division by zero


def test_feasibility_counts_models_that_could_answer_a_request():
    recs = [meta(), meta(size_mb=9000.0), meta(size_status="unknown", size_mb=None), meta(commercial="no")]
    recs[2].pop("size_mb")
    assert feasibility(recs, C) == {"full_pass": 1, "not_fail": 2}
    assert feasibility(recs, {"task": "translation"}) == {"full_pass": 0, "not_fail": 0}   # nothing has that task


QS = [{"id": "q1", "query": "hindi sentiment", "kind": "normal"}, {"id": "q2", "query": "I want a Hindi model", "kind": "vague"},
      {"id": "q3", "query": "tiny impossible", "kind": "impossible"}, {"id": "q4", "query": "hello", "kind": "normal"}]
PARSED = {"q1": C, "q2": {"task": None, "langs": ["hi"], "soft_query": "hindi"}, "q3": {**C, "max_size_mb": 1},
          "q4": {"task": None, "langs": [], "soft_query": "hello"}}


def test_evaluate_reports_clarification_abstention_and_flags_queries_with_nothing_extracted():
    ours = {"q1": top(("a", PASS, {"size": PASS})), "q2": {"outcome": "clarify", "latency_s": 1, "top": []},
            "q3": {"outcome": "abstain", "latency_s": 1, "top": []}, "q4": {"outcome": "clarify", "latency_s": 1, "top": []}}
    naive = {"q1": top(("a", FAIL, {"size": FAIL})), "q2": top(("b", PASS, {"language": PASS})), "q3": top(("c", FAIL, {"size": FAIL})), "q4": top()}
    res = evaluate(QS, PARSED, {"ours": ours, "naive": naive}, records=[meta()])
    assert res["no_constraint_queries"] == ["q4"]                                         # E-MET-3
    assert res["systems"]["ours"]["clarification_rate_pct"] == 100.0 and res["systems"]["ours"]["abstention_pct"] == 100.0
    assert res["systems"]["naive"]["normal"]["violation_pct"] == 100.0 and res["systems"]["ours"]["normal"]["violation_pct"] == 0.0
    assert res["systems"]["ours"]["normal"]["answered_pct"] == 50.0                       # q4 asked a question
    assert res["feasibility"]["q3"] == {"full_pass": 0, "not_fail": 0}
    meta_ = {"tag": "t", "date": "d", "git": "g", "config_sha": "c" * 40, "llm": "m", "store": "local", "embedding": "e", "reranker": "r",
             "n_queries": 4, "kinds": {}, "impossible_ids": ["q3"]}
    md = render_markdown(res, meta_)
    assert "| ours |" in md and "| naive |" in md and "verifiably impossible" in md


def test_label_sheet_is_blind_deduplicated_per_query_and_keyed_separately(tmp_path):
    outcomes = {"ours": {"q1": top(("a", PASS, {}), ("b", PASS, {}))}, "naive": {"q1": top(("b", PASS, {}), ("c", PASS, {}))}}
    info = export_label_sheet([QS[0]], PARSED, outcomes, ["ours", "naive"], lambda mid: f"card of {mid}", tmp_path)
    rows = list(csv.DictReader(open(tmp_path / "relevance_sheet.csv", encoding="utf-8")))
    assert info == {"queries": 1, "pairs": 3} and sorted(r["model_id"] for r in rows) == ["a", "b", "c"]      # b appears once
    assert "ours" not in open(tmp_path / "relevance_sheet.csv", encoding="utf-8").read() and all(r["grade_0_1_2"] == "" for r in rows)
    key = json.loads((tmp_path / "_key.json").read_text(encoding="utf-8"))
    assert sorted(key["q1|b"]) == ["naive", "ours"] and key["q1|a"] == ["ours"]
    assert rows[0]["soft_preference"] == "hindi sentiment" and rows[0]["snippet"].startswith("card of")


def test_the_labelling_sample_is_stratified_by_task_reproducible_and_normal_only():
    qs = [{"id": f"q{i:03d}", "query": f"q{i}", "kind": "normal" if i <= 20 else "vague"} for i in range(1, 31)]
    parsed = {q["id"]: {"task": ["a", "b"][int(q["id"][1:]) % 2]} for q in qs}
    s1, s2 = sample_for_labelling(qs, parsed, 8), sample_for_labelling(qs, parsed, 8)
    assert s1 == s2 and len(s1) == 8 and all(q["kind"] == "normal" for q in s1)
    assert sorted(parsed[q["id"]]["task"] for q in s1) == ["a"] * 4 + ["b"] * 4
