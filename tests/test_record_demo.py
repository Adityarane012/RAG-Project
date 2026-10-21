import json
from pathlib import Path

from scripts.record_demo import run_plan
from src.replay import ReplayGraph


class G:
    def __init__(self, script):
        self.script, self.seen = script, []

    def invoke(self, req):
        self.seen.append(req)
        return self.script(req)


def test_plan_file_is_valid_and_every_step_has_a_name_and_query():
    plan = json.loads((Path(__file__).resolve().parent.parent / "demo" / "plan.json").read_text(encoding="utf-8"))
    assert len(plan["steps"]) >= 5 and all(s["name"] and s["query"] for s in plan["steps"])
    assert any(s.get("clarify_choice") for s in plan["steps"]) and any(s.get("accept_relax") for s in plan["steps"])


def test_records_first_runs_naive_comparisons_and_the_followups_a_presenter_would_click(tmp_path):
    def ours(req):
        if req["overrides"].get("task"):
            return {"outcome": "answer", "results": []}
        if "tiny" in req["query"] and not req["overrides"]:
            return {"outcome": "relax", "relax_offer": {"field": "max_size_mb", "new_value": 500}, "relax_count": 1}
        if "vague" in req["query"]:
            return {"outcome": "clarify", "question": {"field": "task"}, "clarifications_asked": 1}
        return {"outcome": "answer", "results": []}

    plan = {"steps": [{"name": "a", "query": "plain", "compare": True},
                      {"name": "b", "query": "vague", "clarify_choice": "translation"},
                      {"name": "c", "query": "tiny", "accept_relax": True}]}
    go, gn = G(ours), G(lambda r: {"outcome": "answer", "results": [1]})
    report = run_plan(plan, {"ours": go, "naive": gn}, tmp_path, log=lambda *a: None)
    assert [r["recorded"] for r in report] == [["answer", "naive"], ["clarify", "answer"], ["relax", "answer"]]
    assert go.seen[2] == {"query": "vague", "overrides": {"task": "translation"}, "clarifications_asked": 1}      # counters carried
    assert go.seen[4]["overrides"] == {"max_size_mb": 500} and go.seen[4]["relax_count"] == 1
    # everything recorded can be replayed with no graph at all, per variant
    assert ReplayGraph(mode="replay", directory=tmp_path).invoke({"query": "plain", "overrides": {}})["outcome"] == "answer"
    assert ReplayGraph(mode="replay", directory=tmp_path, variant="naive").invoke({"query": "plain", "overrides": {}})["results"] == [1]
    assert ReplayGraph(mode="replay", directory=tmp_path).invoke(
        {"query": "vague", "overrides": {"task": "translation"}, "clarifications_asked": 1})["outcome"] == "answer"


def test_a_step_that_does_not_produce_the_expected_followup_is_flagged_not_silently_skipped(tmp_path):
    plan = {"steps": [{"name": "x", "query": "q", "clarify_choice": "translation"}, {"name": "y", "query": "q2", "accept_relax": True}]}
    report = run_plan(plan, {"ours": G(lambda r: {"outcome": "answer", "results": []})}, tmp_path, log=lambda *a: None)
    assert all("warning" in r for r in report) and "expected a 'clarify'" in report[0]["warning"]
