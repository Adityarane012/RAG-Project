from src.normalize import (apply_multilingual_map, base_model, license_from_tags, license_rights,
                           normalize_languages, normalize_record, param_count, size_mb)


def test_license_rights_map():
    assert license_rights("Apache-2.0") == ("yes", "yes")
    assert license_rights("cc-by-nc-4.0") == ("no", "yes")      # modify yes, result non-commercial
    assert license_rights("cc-by-nd-4.0") == ("yes", "no")      # no derivatives
    assert license_rights("cc-by-nc-nd-4.0") == ("no", "no")
    assert license_rights("openrail") == ("conditional", "conditional")
    assert license_rights("gpl-3.0") == ("conditional", "conditional")   # share-alike: both rights need reading
    assert license_rights("cc-by-sa-4.0") == ("conditional", "conditional")
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


def test_language_spellings_are_normalised():
    assert normalize_languages(["hin", "hi-IN", "mr_IN", "eng", "en-US"]) == ["hi", "mr", "en"]
    assert normalize_languages(["multilingual", "en"]) == ["en"]   # not a language
    assert normalize_languages(["zzz"]) == ["zzz"]                 # unknown codes are kept, not guessed


def test_card_saying_only_multilingual_is_unknown_not_a_wrong_no():
    from src.verify import UNKNOWN, verify

    m = normalize_record({"id": "x/y", "pipeline_tag": "token-classification", "cardData": {"language": "multilingual"}})
    assert m["multilingual"] is True and m["language_status"] == "unknown" and m["languages"] == []
    assert verify(m, {"langs": ["hi"]})["languages"] == UNKNOWN


def test_multilingual_card_with_a_list_keeps_it_and_an_unlisted_language_is_unknown_not_fail():
    from src.verify import FAIL, PASS, UNKNOWN, verify

    m = normalize_record({"id": "x/y", "pipeline_tag": "token-classification",
                          "cardData": {"language": ["multilingual", "en", "hi"]}})
    assert m["languages"] == ["en", "hi"] and m["language_status"] == "known" and m["multilingual"] is True
    assert verify(m, {"langs": ["hi"]})["languages"] == PASS          # listed: a real pass
    assert verify(m, {"langs": ["mr"]})["languages"] == UNKNOWN       # not listed, but the card says multilingual
    plain = normalize_record({"id": "x/z", "pipeline_tag": "token-classification", "cardData": {"language": ["en", "hi"]}})
    assert verify(plain, {"langs": ["mr"]})["languages"] == FAIL      # a non-multilingual list is definitive


def test_opus_mt_name_supplies_the_languages_when_the_card_has_none():
    m = normalize_record({"id": "Helsinki-NLP/opus-mt-hi-mr", "pipeline_tag": "translation", "cardData": {}})
    assert m["languages"] == ["hi", "mr"] and m["language_status"] == "known" and m["directions"] == ["hi-mr"]


def test_every_multilingual_entry_cites_a_source_and_none_is_silently_checked():
    from src.normalize import MULTILINGUAL_MODELS

    assert MULTILINGUAL_MODELS
    for model_id, entry in MULTILINGUAL_MODELS.items():
        assert entry.source.strip(), f"{model_id} has no source"
        assert entry.languages, model_id
        assert entry.checked is False  # flip to True only after comparing against the source


def test_direction_comes_only_from_the_opus_mt_naming_pattern():
    from src.normalize import directions_from_name

    assert directions_from_name("Helsinki-NLP/opus-mt-hi-en") == ["hi-en"]
    assert directions_from_name("Helsinki-NLP/opus-mt-en-mr") == ["en-mr"]
    assert directions_from_name("someone/opus-mt-en-hi-finetuned") == ["en-hi"]
    assert directions_from_name("opus-mt-hin-eng") == ["hi-en"]                 # 3-letter codes normalised
    assert directions_from_name("Helsinki-NLP/opus-mt-tc-big-en-ro") == []      # tc- family: not src-tgt
    assert directions_from_name("facebook/nllb-200-distilled-600M") == []       # multi-direction: unknown
    assert directions_from_name("someone/my-opus-mt-hi-en") == []               # name must start with opus-mt-
    assert directions_from_name("org/opus-mt-hindi-english") == []


def test_direction_check_uses_the_name_and_says_so():
    from src.verify import PASS, UNKNOWN, notes, verify

    m = normalize_record({"id": "Helsinki-NLP/opus-mt-hi-mr", "pipeline_tag": "translation",
                          "cardData": {"language": ["hi", "mr"]}})
    assert m["directions"] == ["hi-mr"] and m["direction_source"] == "model_name"
    fwd = {"task": "translation", "langs": ["hi", "mr"], "direction": ["hi", "mr"]}
    rev = {**fwd, "direction": ["mr", "hi"]}
    assert verify(m, fwd)["direction"] == PASS and "direction from model name" in notes(m, fwd)
    assert verify(m, rev)["direction"] == UNKNOWN and "direction from model name" not in notes(m, rev)


def test_canonical_base_model_merges_legacy_ids():
    raw = {"id": "a/b", "cardData": {"base_model": "xlm-roberta-base"}, "siblings": []}
    assert normalize_record(raw)["base_model"] == "xlm-roberta-base"
    merged = normalize_record(raw, {"xlm-roberta-base": "FacebookAI/xlm-roberta-base"})
    assert merged["base_model"] == "FacebookAI/xlm-roberta-base"


def test_why_size_is_unknown():
    from src.normalize import size_unknown_reason

    assert size_unknown_reason([("model.safetensors", 5)]) is None
    assert size_unknown_reason([("model.safetensors", None)]) == "weights_missing_size"
    assert size_unknown_reason([("adapter_model.safetensors", 5)]) == "adapter_only"
    assert size_unknown_reason([("fp16/model.safetensors", 5)]) == "weights_only_in_subfolder"
    assert size_unknown_reason([("model-q4.gguf", 5)]) == "gguf_only"
    assert size_unknown_reason([("best_checkpoint.bin", 5)]) == "weights_with_other_name"
    assert size_unknown_reason([("README.md", 5)]) == "no_weight_files"
