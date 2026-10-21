import json

import pytest

from eval.metrics import (abstention_accuracy, clarification_rate, latency_summary, load_queries,
                          modifiable_correctness, unknown_rate_at_k, violation_rate_at_k)

OK, BAD, UNK = {"size": "pass"}, {"size": "fail", "commercial": "unknown"}, {"size": "unknown"}


def test_violation_and_unknown_are_exclusive_and_respect_k():
    queries = [[OK, BAD, UNK, OK], [BAD, OK]]
    assert violation_rate_at_k(queries, k=5) == pytest.approx(2 / 6)
    assert unknown_rate_at_k(queries, k=5) == pytest.approx(1 / 6)
    assert violation_rate_at_k(queries, k=1) == pytest.approx(1 / 2)  # only first of each query
    assert violation_rate_at_k([]) == 0.0


def test_abstention_and_clarification():
    assert abstention_accuracy(["abstain", "relax", "answer", "answer"]) == 0.5
    assert clarification_rate(["clarify", "answer"]) == 0.5


def test_modifiable_correctness_and_latency():
    assert modifiable_correctness([("mit", "yes"), ("cc-by-nd-4.0", "yes")]) == 0.5
    assert latency_summary([1.0, 3.0, 2.0]) == {"median": 2.0, "worst": 3.0}


def test_load_queries_validates(tmp_path):
    good = {"id": "q1", "query": "x", "kind": "vague", "source": "teammate"}
    p = tmp_path / "q.jsonl"
    p.write_text(json.dumps(good) + "\n\n")
    assert load_queries(p) == [good]
    p.write_text(json.dumps({**good, "kind": "weird"}) + "\n")
    with pytest.raises(ValueError):
        load_queries(p)
