"""Real Hub responses saved on 2026-10-21 (tests/fixtures/hub). They pin what `normalize_record` does with
real data, so a change to the rules shows up here, and they document facts the design depends on."""
import json
from pathlib import Path

import pytest

from src.normalize import normalize_record
from src.verify import FAIL, PASS, UNKNOWN, verify

FX = Path(__file__).resolve().parent / "fixtures" / "hub"


def rec(model_id):
    raw = json.loads((FX / (model_id.replace("/", "__") + ".json")).read_text(encoding="utf-8"))
    return raw, normalize_record(raw)


def test_responses_have_the_fields_normalize_expects():
    for path in FX.glob("*.json"):
        raw = json.loads(path.read_text(encoding="utf-8"))
        assert raw["siblings"] and all("size" in s for s in raw["siblings"]), path.name   # blobs=true gives sizes
        assert {"id", "downloads"} <= raw.keys()


def test_nllb_is_non_commercial_so_demo_query_2_premise_holds():
    _, m = rec("facebook/nllb-200-distilled-600M")
    assert (m["commercial"], m["modifiable"]) == ("no", "yes")
    assert verify(m, {"commercial": True})["commercial"] == FAIL


def test_whisper_tiny_is_small_apache_and_multilingual():
    raw, m = rec("openai/whisper-tiny")
    assert m["size_status"] == "known" and 140 < m["size_mb"] < 160
    assert m["param_count"] == 37_760_640 and (m["commercial"], m["modifiable"]) == ("yes", "yes")
    assert m["multilingual"] is True and {"hi", "mr", "ta"} <= set(m["languages"])
    assert verify(m, {"task": "automatic-speech-recognition", "langs": ["hi"], "max_size_mb": 500,
                      "commercial": True}) == {"task": PASS, "languages": PASS, "size": PASS, "commercial": PASS}


def test_opus_mt_gets_direction_and_languages_from_its_name():
    _, m = rec("Helsinki-NLP/opus-mt-hi-en")
    assert m["directions"] == ["hi-en"] and set(m["languages"]) == {"hi", "en"} and m["language_status"] == "known"
    ok = {"task": "translation", "langs": ["hi", "en"], "direction": ["hi", "en"]}
    assert verify(m, ok)["direction"] == PASS
    assert verify(m, {**ok, "direction": ["en", "hi"]})["direction"] == UNKNOWN      # reverse is not claimed


def test_license_missing_means_unknown_not_a_guess():
    _, m = rec("cardiffnlp/twitter-xlm-roberta-base-sentiment")
    assert (m["commercial"], m["modifiable"]) == ("unknown", "unknown")
    assert m["multilingual"] is True and m["language_status"] == "unknown"            # card just says "multilingual"
    assert verify(m, {"langs": ["hi"], "commercial": True}) == {"languages": UNKNOWN, "commercial": UNKNOWN}


def test_explicit_language_list_plus_multilingual_still_passes_a_listed_language():
    _, m = rec("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    assert m["language_status"] == "known" and m["multilingual"] is True
    assert "hi" in m["languages"] and verify(m, {"langs": ["hi"]})["languages"] == PASS


def test_a_readme_that_the_raw_endpoint_forbids_is_still_fetched_via_resolve():
    """ai4bharat/IndicNER: /raw/main/README.md answers 403, /resolve/main/README.md answers 200."""
    card = (FX / "ai4bharat__IndicNER.md").read_text(encoding="utf-8")
    assert len(card) > 1000
    _, m = rec("ai4bharat/IndicNER")
    assert {"hi", "mr", "ta"} <= set(m["languages"]) and (m["commercial"], m["modifiable"]) == ("yes", "yes")


def test_a_repo_with_no_card_and_no_pipeline_tag_normalizes_without_error():
    _, m = rec("hf-internal-testing/tiny-random-bert")
    assert m["task"] is None and m["languages"] == [] and m["commercial"] == "unknown"
    assert m["size_status"] == "known"


@pytest.mark.parametrize("model_id, weight_file", [("openai/whisper-tiny", "model.safetensors"),
                                                    ("ai4bharat/IndicNER", "pytorch_model.bin")])
def test_size_is_exactly_the_main_weight_file_not_the_whole_repo(model_id, weight_file):
    raw, m = rec(model_id)
    sizes = {s["rfilename"]: s["size"] for s in raw["siblings"]}
    assert m["size_mb"] == sizes[weight_file] / 1_000_000
    assert m["size_mb"] < sum(sizes.values()) / 1_000_000          # other files (tokenizer, config...) are excluded
