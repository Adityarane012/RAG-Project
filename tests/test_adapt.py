from src.adapt import build_lineage_index, lineage, memory_estimate, model_report, reported_metrics, rights_notes
from src.verify import FAIL, PASS, UNKNOWN


def test_memory_estimate_is_labelled_lower_bound_per_method():
    m = memory_estimate(1_000_000_000)  # 1B params
    assert m["methods"]["inference"]["gb"] == 2.0
    assert m["methods"]["full"]["gb"] == 16.0 and m["methods"]["full"]["fits"] == PASS  # <= 16 GB T4
    assert 2.0 < m["methods"]["lora"]["gb"] < 3.0
    assert memory_estimate(3_000_000_000)["methods"]["full"]["fits"] == FAIL
    assert memory_estimate(3_000_000_000)["methods"]["lora"]["fits"] == PASS


def test_memory_unknown_without_param_count():
    assert memory_estimate(None)["status"] == UNKNOWN


def test_lineage_counts_other_finetunes_and_language_subset():
    recs = [{"model_id": "a", "base_model": "xlmr", "languages": ["mr"]},
            {"model_id": "b", "base_model": "xlmr", "languages": ["hi"]},
            {"model_id": "c", "base_model": "xlmr", "languages": ["mr", "hi"]},
            {"model_id": "d", "languages": ["mr"]}]
    idx = build_lineage_index(recs)
    out = lineage(recs[0], idx, ["mr"])
    assert out == {"status": PASS, "base_model": "xlmr", "other_finetunes": 2, "other_finetunes_in_language": 1}
    assert lineage(recs[3], idx)["status"] == UNKNOWN


def test_rights_notes():
    assert any("non-commercial" in n for n in rights_notes({"commercial": "no", "modifiable": "yes"}))
    assert any("No derivatives" in n for n in rights_notes({"commercial": "yes", "modifiable": "no"}))
    assert any("Extra terms" in n for n in rights_notes({"commercial": "conditional", "modifiable": "conditional"}))
    assert rights_notes({"commercial": "yes", "modifiable": "yes"}) == []


def test_reported_metrics_are_labelled_unverified():
    card = {"model-index": [{"results": [{"dataset": {"name": "wnut"},
                                          "metrics": [{"type": "f1", "value": 0.8}, {"type": "x", "value": None}]}]}]}
    out = reported_metrics(card)
    assert out == [{"dataset": "wnut", "metric": "f1", "value": 0.8, "label": "reported by the author, not verified"}]
    assert reported_metrics(None) == []


def test_model_report_works_for_a_single_model_without_retrieval():
    r = model_report({"model_id": "a/b", "task": "translation", "commercial": "no", "modifiable": "yes"})
    assert r["rights"]["commercial"] == "no" and r["lineage"]["status"] == UNKNOWN
    assert r["memory"]["status"] == UNKNOWN and r["task_guide"].startswith("https://")
