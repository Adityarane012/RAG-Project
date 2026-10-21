import json
from pathlib import Path

from src.checker import check_model, facts, find_model
from src.snapshot import collect_records

FX = Path(__file__).resolve().parent / "fixtures" / "hub"
RECORDS = collect_records(FX)


def test_finds_exact_and_case_insensitive_ids_and_nothing_for_blank_or_unknown():
    assert find_model("openai/whisper-tiny", RECORDS)["model_id"] == "openai/whisper-tiny"
    assert find_model("  OpenAI/Whisper-Tiny ", RECORDS)["model_id"] == "openai/whisper-tiny"
    assert find_model("", RECORDS) is None and find_model("nobody/nothing", RECORDS) is None


def test_a_model_outside_the_snapshot_gets_an_honest_message_not_a_guess():
    r = check_model("nobody/nothing", RECORDS)
    assert r["found"] is False and "not in our snapshot" in r["message"] and "snapshot only" in r["message"]


def test_rights_facts_and_table_for_a_real_model():
    r = check_model("facebook/nllb-200-distilled-600M", RECORDS, {"commercial": True, "modifiable": True, "max_size_mb": 3000})
    assert r["found"] and r["facts"]["Commercial use"] == "no" and r["facts"]["Modification"] == "yes"
    assert r["table"] == {"size": "pass", "commercial": "fail", "modifiable": "pass"}
    assert any("non-commercial" in n for n in r["report"]["rights"]["notes"])


def test_no_requirements_means_an_empty_table_and_unknowns_are_shown_as_unknown():
    r = check_model("cardiffnlp/twitter-xlm-roberta-base-sentiment", RECORDS)
    assert r["table"] == {} and r["facts"]["Commercial use"] == "unknown" and r["facts"]["Languages"] == "unknown"
    t = check_model("hf-internal-testing/tiny-random-bert", RECORDS)
    assert t["facts"]["Task"] == "unknown" and t["facts"]["Based on"] == "not declared"


def test_build_on_report_has_memory_estimate_and_task_guide():
    r = check_model("openai/whisper-tiny", RECORDS)
    assert r["report"]["memory"]["status"] == "pass" and r["report"]["task_guide"].startswith("https://")
    assert facts({"model_id": "x"})["Size"] == "unknown"
