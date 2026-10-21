from src.normalize import (apply_multilingual_map, base_model, license_from_tags, license_rights,
                           normalize_languages, normalize_record, param_count, size_mb)


def test_license_rights_map():
    assert license_rights("Apache-2.0") == ("yes", "yes")
    assert license_rights("cc-by-nc-4.0") == ("no", "yes")      # modify yes, result non-commercial
    assert license_rights("cc-by-nd-4.0") == ("yes", "no")      # no derivatives
    assert license_rights("cc-by-nc-nd-4.0") == ("no", "no")
    assert license_rights("openrail") == ("conditional", "conditional")
    assert license_rights("gpl-3.0") == ("conditional", "yes")
    assert license_rights("some-custom-license") == ("unknown", "unknown")
    assert license_rights(None) == ("unknown", "unknown")


def test_license_from_tags():
    assert license_from_tags(["pytorch", "license:mit"]) == "mit"
    assert license_from_tags(["pytorch"]) is None


def test_languages():
    assert normalize_languages(["HI", "hi", " mr "]) == ["hi", "mr"]
    assert normalize_languages("en") == ["en"]
    assert normalize_languages(None) == []


def test_multilingual_map_merges_languages_and_flags():
    langs, multi = apply_multilingual_map("FacebookAI/xlm-roberta-base", [])
    assert multi and "hi" in langs and "mr" in langs
    assert apply_multilingual_map("someone/model", ["hi"]) == (["hi"], False)


def test_size_rule_prefers_safetensors_and_ignores_duplicate_formats():
    files = [("model.safetensors", 400_000_000), ("pytorch_model.bin", 400_000_000),
             ("onnx/model.onnx", 500_000_000), ("model.gguf", 100_000_000),
             ("tf_model.h5", 400_000_000), ("flax_model.msgpack", 400_000_000),
             ("optimizer.bin", 900_000_000), ("training_args.bin", 2000)]
    assert size_mb(files) == 400.0


def test_size_rule_sums_shards_and_falls_back_to_bin():
    shards = [("model-00001-of-00002.safetensors", 3_000_000_000), ("model-00002-of-00002.safetensors", 1_500_000_000),
              ("model.safetensors.index.json", 50_000)]
    assert size_mb(shards) == 4500.0
    assert size_mb([("pytorch_model.bin", 250_000_000), ("tf_model.h5", 1)]) == 250.0


def test_size_unknown_when_no_main_weights_or_size_missing():
    assert size_mb([("README.md", 10), ("nested/model.safetensors", 5)]) is None
    assert size_mb([("model.safetensors", None)]) is None
    assert size_mb([]) is None


def test_param_count_and_base_model():
    assert param_count({"total": 278_000_000}) == 278_000_000
    assert param_count({}) is None and param_count(None) is None
    assert base_model({"base_model": "xlm-roberta-base"}) == "xlm-roberta-base"
    assert base_model({"base_model": ["a/b", "c/d"]}) == "a/b"
    assert base_model({}) is None


RAW = {"id": "org/marathi-ner", "pipeline_tag": "token-classification", "downloads": 12,
       "tags": ["license:apache-2.0"],
       "cardData": {"language": ["mr"], "license": "apache-2.0", "base_model": "xlm-roberta-base"},
       "siblings": [{"rfilename": "model.safetensors", "size": 300_000_000}],
       "safetensors": {"total": 150_000_000}}


def test_normalize_record_full():
    m = normalize_record(RAW)
    assert m["size_mb"] == 300.0 and m["size_status"] == "known"
    assert (m["commercial"], m["modifiable"]) == ("yes", "yes")
    assert m["languages"] == ["mr"] and m["language_status"] == "known" and m["multilingual"] is False
    assert m["base_model"] == "xlm-roberta-base" and m["lineage_status"] == "known"
    assert m["param_count"] == 150_000_000


def test_normalize_record_unknowns_are_omitted_not_sentinels():
    m = normalize_record({"id": "x/y", "pipeline_tag": "translation", "siblings": []})
    assert "size_mb" not in m and m["size_status"] == "unknown"
    assert "param_count" not in m and "base_model" not in m and m["lineage_status"] == "unknown"
    assert m["language_status"] == "unknown" and m["commercial"] == "unknown" and m["modifiable"] == "unknown"


def test_size_is_not_rounded_across_a_threshold():
    assert size_mb([("model.safetensors", 500_040_000)]) > 500
