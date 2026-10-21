import json

from src.baselines import KeywordIndex, hub_candidates, resolve_metadata, tokenize


def doc(i, text, **meta):
    return {"id": f"m{i}::0", "text": text, "metadata": {"model_id": f"m{i}", "task": "token-classification", **meta}}


CORPUS = [
    doc(0, "Marathi named entity recognition model trained on noisy social media tweets", languages=["mr"], size_status="known", size_mb=300.0),
    doc(1, "Hindi sentiment analysis model for product reviews", languages=["hi"], size_status="known", size_mb=900.0),
    doc(2, "Marathi news article classifier", languages=["mr"], size_status="unknown"),
    doc(3, "Marathi marathi marathi tokens repeated tokens", languages=["mr"], size_status="known", size_mb=100.0),
    doc(4, "मराठी नावे ओळखणारे मॉडेल", languages=["mr"], size_status="known", size_mb=50.0),
]


def test_tokenizer_keeps_devanagari_words_whole_and_strips_punctuation():
    assert tokenize("Marathi, NER-model (small)!") == ["marathi", "ner-model", "small"]
    assert tokenize("मराठी नावे ओळखणारे मॉडेल।") == ["मराठी", "नावे", "ओळखणारे", "मॉडेल"]
    assert tokenize("a I x ok") == ["ok"]                                       # single characters dropped


def test_bm25_ranks_the_chunk_that_matches_the_rarest_query_terms_first():
    kw = KeywordIndex(CORPUS)
    top = kw.search("noisy social media Marathi", None, 5)
    assert top[0]["id"] == "m0::0" and top[0]["score"] > top[1]["score"]
    assert kw.search("sentiment", None, 5)[0]["id"] == "m1::0"
    assert kw.search("मराठी नावे", None, 1)[0]["id"] == "m4::0"                  # Devanagari queries match Devanagari text
    assert kw.search("nonexistentterm", None, 5) == []


def test_bm25_applies_the_same_filter_semantics_as_the_vector_index():
    kw = KeywordIndex(CORPUS)
    small = {"$or": [{"size_mb": {"$lte": 500}}, {"size_status": {"$eq": "unknown"}}]}
    got = [m["id"] for m in kw.fetch("marathi", small, 10)]
    assert "m1::0" not in got and set(got) == {"m0::0", "m2::0", "m3::0"}        # unknown-size m2 kept, 900 MB m1 absent
    assert len(kw.fetch("marathi", {}, 2)) == 2 and kw.fetch("marathi", {}, 10)[0]["metadata"]["model_id"]


def test_bm25_term_frequency_saturates_and_ties_are_deterministic():
    kw = KeywordIndex(CORPUS)
    ids = [m["id"] for m in kw.search("marathi", None, 5)]
    assert ids == [m["id"] for m in kw.search("marathi", None, 5)]
    twin = KeywordIndex([doc(0, "same words here", x=1), doc(1, "same words here", x=1)])
    assert [m["id"] for m in twin.search("words", None, 2)] == ["m0::0", "m1::0"]
    assert KeywordIndex([]).search("x", None, 3) == []


class Model:
    def __init__(self, i):
        self.id = i


class FakeApi:
    def __init__(self):
        self.calls = []

    def list_models(self, **kw):
        self.calls.append(kw)
        return [Model("a/one"), Model("b/two")]


def test_hub_basic_uses_task_and_language_only_sorted_by_downloads():
    api = FakeApi()
    assert hub_candidates(api, {"task": "translation", "langs": ["hi", "mr"], "commercial": True, "max_size_mb": 100}) == ["a/one", "b/two"]
    assert api.calls[0] == {"sort": "downloads", "limit": 5, "pipeline_tag": "translation", "filter": ["hi", "mr"]}


def test_hub_licensed_adds_one_permissive_license_string_only_when_rights_are_required():
    api = FakeApi()
    hub_candidates(api, {"task": "translation", "langs": ["hi"], "commercial": True}, variant="licensed")
    assert api.calls[-1]["filter"] == ["hi", "license:apache-2.0"]
    hub_candidates(api, {"task": "translation", "langs": ["hi"]}, variant="licensed")
    assert api.calls[-1]["filter"] == ["hi"]
    hub_candidates(api, {}, variant="basic")
    assert api.calls[-1] == {"sort": "downloads", "limit": 5}                     # nothing to filter on


def test_hub_baseline_only_passes_arguments_the_real_library_accepts():
    import inspect

    from huggingface_hub import HfApi

    allowed = set(inspect.signature(HfApi.list_models).parameters)
    api = FakeApi()
    hub_candidates(api, {"task": "translation", "langs": ["hi"], "commercial": True}, variant="licensed")
    assert set(api.calls[0]) <= allowed


def test_resolve_metadata_prefers_caches_fetches_elsewhere_and_degrades_to_none(tmp_path):
    corpus, extra = tmp_path / "corpus", tmp_path / "extra"
    corpus.mkdir(); extra.mkdir()
    raw = {"id": "o/m", "pipeline_tag": "translation", "cardData": {"license": "mit"}, "siblings": []}
    (corpus / "o__m.json").write_text(json.dumps(raw), encoding="utf-8")
    assert resolve_metadata("o/m", (corpus,), extra)["commercial"] == "yes"
    calls = []

    def fetch(model_id, d):
        calls.append(model_id)
        (d / "x__y.json").write_text(json.dumps({"id": "x/y", "pipeline_tag": "translation"}), encoding="utf-8")

    assert resolve_metadata("x/y", (corpus,), extra, fetch=fetch)["task"] == "translation" and calls == ["x/y"]
    assert resolve_metadata("x/y", (corpus,), extra, fetch=fetch) and calls == ["x/y"]       # now cached: no second fetch
    assert resolve_metadata("gone/model", (corpus,), extra) is None
    assert resolve_metadata("gone/model", (corpus,), extra, fetch=lambda i, d: (_ for _ in ()).throw(RuntimeError("404"))) is None
