from src.normalize import commercial_status, license_from_tags, normalize_languages, to_metadata


def test_license_map():
    assert commercial_status("Apache-2.0") == "yes"
    assert commercial_status("cc-by-nc-4.0") == "no"
    assert commercial_status("openrail") == "conditional"
    assert commercial_status("some-custom-license") == "unknown"
    assert commercial_status(None) == "unknown"


def test_license_from_tags():
    assert license_from_tags(["pytorch", "license:mit"]) == "mit"
    assert license_from_tags(["pytorch"]) is None


def test_languages():
    assert normalize_languages(["HI", "hi", " mr "]) == ["hi", "mr"]
    assert normalize_languages("en") == ["en"]
    assert normalize_languages(None) == []


def test_unknown_size_is_omitted_not_sentinel():
    m = to_metadata(model_id="x", task="translation", languages=[], size=None,
                    license_id=None, downloads=0, section="intro")
    assert "size_mb" not in m
    assert m["size_status"] == "unknown"
    assert m["language_status"] == "unknown"
    assert m["commercial"] == "unknown"
