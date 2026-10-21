import json

import pytest

from src.rerank import LocalReranker
from src.replay import MissingRecording, ReplayGraph, mode_from_env, run_key


def match(mid, score, text="t"):
    return {"id": f"{mid}::0", "score": score, "metadata": {"model_id": mid, "text": text}}


def test_reranker_replaces_scores_and_sorts_best_first():
    seen = {}

    def scorer(pairs):
        seen["pairs"] = pairs
        return [0.1, 0.9, 0.5]

    out = LocalReranker(scorer=scorer)("my query", [match("a", 0.99, "x"), match("b", 0.2, "y"), match("c", 0.5, "z")])
    assert [m["id"] for m in out] == ["b::0", "c::0", "a::0"]
    assert [m["score"] for m in out] == [0.9, 0.5, 0.1]            # the contract: scores are REPLACED
    assert out[2]["retrieval_score"] == 0.99                       # original kept for debugging
    assert seen["pairs"][0] == ("my query", "x")


def test_reranker_handles_empty_and_does_not_mutate_input():
    assert LocalReranker(scorer=lambda p: [])("q", []) == []
    original = [match("a", 0.3)]
    LocalReranker(scorer=lambda p: [0.8])("q", original)
    assert original[0]["score"] == 0.3


def test_run_key_is_stable_and_sensitive_to_everything_that_changes_a_run():
    base = {"query": "q", "overrides": {"task": "translation", "x": 1}}
    assert run_key(base) == run_key({"overrides": {"x": 1, "task": "translation"}, "query": " q "})
    assert run_key(base) != run_key({**base, "query": "q2"})
    assert run_key(base) != run_key({**base, "overrides": {}})
    assert run_key(base) != run_key({**base, "clarifications_asked": 1})
    assert run_key(base) != run_key({**base, "relax_count": 1})
    assert run_key(base) == run_key({**base, "clarifications_asked": 0})   # absent == 0


class FakeGraph:
    def __init__(self):
        self.calls = 0

    def invoke(self, inp):
        self.calls += 1
        return {"outcome": "answer", "intent": "मराठी", "n": self.calls}


def test_record_then_replay_needs_no_graph_and_keeps_unicode(tmp_path):
    inp = {"query": "Marathi NER", "overrides": {}}
    graph = FakeGraph()
    recorded = ReplayGraph(graph, "record", tmp_path).invoke(inp)
    assert graph.calls == 1 and len(list(tmp_path.glob("*.json"))) == 1
    replayed = ReplayGraph(mode="replay", directory=tmp_path).invoke(inp)   # no graph at all
    assert replayed == recorded and graph.calls == 1
    assert "मराठी" in next(tmp_path.glob("*.json")).read_text(encoding="utf-8")
    assert not list(tmp_path.glob("*.tmp"))


def test_replay_of_an_unrecorded_query_fails_loudly(tmp_path):
    with pytest.raises(MissingRecording, match="RECORD=1"):
        ReplayGraph(mode="replay", directory=tmp_path).invoke({"query": "never recorded"})


def test_clarify_then_answer_sequence_replays_step_by_step(tmp_path):
    rec = ReplayGraph(FakeGraph(), "record", tmp_path)
    first = rec.invoke({"query": "hindi model"})
    second = rec.invoke({"query": "hindi model", "overrides": {"task": "x"}, "clarifications_asked": 1})
    rep = ReplayGraph(mode="replay", directory=tmp_path)
    assert rep.invoke({"query": "hindi model"}) == first
    assert rep.invoke({"query": "hindi model", "overrides": {"task": "x"}, "clarifications_asked": 1}) == second
    assert first != second


def test_live_mode_passes_through_and_modes_are_validated(tmp_path):
    g = FakeGraph()
    ReplayGraph(g, "live", tmp_path).invoke({"query": "q"})
    assert g.calls == 1 and not list(tmp_path.glob("*.json"))
    with pytest.raises(ValueError):
        ReplayGraph(mode="record")            # recording needs a graph
    with pytest.raises(ValueError):
        ReplayGraph(g, "weird")


def test_mode_from_env(monkeypatch):
    monkeypatch.delenv("REPLAY", raising=False)
    monkeypatch.delenv("RECORD", raising=False)
    assert mode_from_env() == "live"
    monkeypatch.setenv("RECORD", "1")
    assert mode_from_env() == "record"
    monkeypatch.setenv("REPLAY", "1")
    assert mode_from_env() == "replay"       # replay wins: never hit the network by accident
