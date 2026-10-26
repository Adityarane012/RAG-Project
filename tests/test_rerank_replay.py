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
    # chunks are scored best-by-vector-score first: a (0.99), c (0.5), b (0.2) -> 0.1, 0.9, 0.5
    assert [m["id"] for m in out] == ["c::0", "b::0", "a::0"]
    assert [m["score"] for m in out] == [0.9, 0.5, 0.1]            # the contract: scores are REPLACED
    assert out[2]["retrieval_score"] == 0.99                       # original kept for debugging
    assert seen["pairs"][0] == ("my query", "x")


def test_local_reranker_scores_only_max_docs_and_keeps_the_rest_below():
    out = LocalReranker(scorer=lambda pairs: [0.5] * len(pairs), max_docs=2)("q", [match("a", 0.9), match("b", 0.8), match("c", 0.7)])
    assert [m["id"] for m in out] == ["a::0", "b::0", "c::0"] and out[2]["score"] < out[1]["score"]


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


# ---- hosted reranker -------------------------------------------------------------------------------------------
from src.rerank import HostedReranker, RerankQuotaExceeded, load_reranker


class RR:
    def __init__(self, status=200, payload=None, text=""):
        self.status_code, self._p, self.text = status, payload, text

    def json(self):
        return self._p


def hosted(tmp_path, responses):
    it, sent = iter(responses), []

    def post(url, json=None, headers=None, timeout=None):
        sent.append((url, json, headers))
        return next(it)

    return HostedReranker(api_key="k", cache_dir=tmp_path, post=post, sleep=lambda s: None), sent


def rows(*scores):
    return RR(200, {"data": [{"index": i, "score": s} for i, s in enumerate(scores)], "usage": {"rerank_units": 1}})


def m(i, score, text="t"):
    return {"id": f"m{i}::0", "score": score, "metadata": {"model_id": f"m{i}", "text": text}}


def test_hosted_rerank_replaces_scores_sorts_best_first_and_keeps_the_original_score(tmp_path):
    h, sent = hosted(tmp_path, [rows(0.1, 0.9, 0.5)])
    ms = [m(0, 0.99, "x"), m(1, 0.50, "y"), m(2, 0.70, "z")]
    out = h("q", ms)
    # documents are sent best-by-vector-score first: m0 (0.99), m2 (0.70), m1 (0.50) -> scores 0.1, 0.9, 0.5
    assert [o["id"] for o in out] == ["m2::0", "m1::0", "m0::0"] and [o["score"] for o in out] == [0.9, 0.5, 0.1]
    assert out[2]["retrieval_score"] == 0.99
    url, body, headers = sent[0]
    assert url.endswith("/rerank") and body["model"] == "bge-reranker-v2-m3" and headers["X-Pinecone-API-Version"] == "2024-10"
    assert [d["text"] for d in body["documents"]] == ["x", "z", "y"] and ms[0]["score"] == 0.99    # input untouched


def test_hosted_rerank_asks_the_service_to_truncate_long_pairs(tmp_path):
    # live finding: a long Gujarati chunk exceeded the 1,024-token pair limit and failed the whole request
    h, sent = hosted(tmp_path, [rows(0.5)])
    h("q", [m(0, 0.9)])
    assert sent[0][1]["parameters"] == {"truncate": "END"}


def test_hosted_rerank_is_cached_so_a_rerun_costs_nothing_and_usage_is_logged(tmp_path):
    h, sent = hosted(tmp_path, [rows(0.2, 0.8)])
    ms = [m(0, 0.9), m(1, 0.8)]
    first = h("q", ms)
    again = h("q", ms)
    assert first == again and len(sent) == 1 and h.cache_hits == 1 and h.units_total() == 1
    h2, sent2 = hosted(tmp_path, [rows(0.3, 0.1)])
    h2("a different query", ms)
    assert len(sent2) == 1 and h2.units_total() == 2           # a new query is a new request


def test_hosted_rerank_caps_documents_and_keeps_the_rest_below_the_reranked_ones(tmp_path):
    h, sent = hosted(tmp_path, [rows(0.9, 0.1)])
    h.max_docs = 2
    out = h("q", [m(0, 0.9), m(1, 0.8), m(2, 0.7)])
    assert len(sent[0][1]["documents"]) == 2 and [o["id"] for o in out][:2] == ["m0::0", "m1::0"]
    assert out[2]["id"] == "m2::0" and out[2]["score"] < out[1]["score"]


def test_hosted_rerank_errors_are_clear(tmp_path):
    h, _ = hosted(tmp_path, [RR(429, text="Monthly rerank quota exceeded")])
    with pytest.raises(RerankQuotaExceeded):
        h("q", [m(0, 0.5)])
    h, _ = hosted(tmp_path / "b", [RR(404, text="not found")])
    with pytest.raises(RuntimeError, match="HTTP 404"):
        h("q", [m(0, 0.5)])
    h, sent = hosted(tmp_path / "c", [RR(503, text=""), rows(0.5)])
    assert len(h("q", [m(0, 0.5)])) == 1 and len(sent) == 2     # a 503 is retried
    assert HostedReranker(cache_dir=tmp_path)("q", []) == []


def test_load_reranker_selection(monkeypatch):
    monkeypatch.delenv("RERANKER", raising=False)
    assert isinstance(load_reranker("pinecone"), HostedReranker) and isinstance(load_reranker("local"), LocalReranker)
    assert load_reranker("none")("q", [1, 2]) == [1, 2]
    with pytest.raises(ValueError):
        load_reranker("cohere")


def test_variants_are_recorded_separately_but_ours_keeps_its_original_key():
    inp = {"query": "q", "overrides": {}}
    assert run_key(inp) == run_key(inp, "ours") != run_key(inp, "naive")


def test_the_side_by_side_view_replays_each_variant_from_its_own_recording(tmp_path):
    inp = {"query": "Marathi NER"}
    for variant, tag in (("ours", "A"), ("naive", "B")):
        g = FakeGraph()
        g.invoke = lambda i, tag=tag: {"outcome": "answer", "who": tag}
        ReplayGraph(g, "record", tmp_path, variant=variant).invoke(inp)
    assert ReplayGraph(mode="replay", directory=tmp_path, variant="ours").invoke(inp)["who"] == "A"
    assert ReplayGraph(mode="replay", directory=tmp_path, variant="naive").invoke(inp)["who"] == "B"
