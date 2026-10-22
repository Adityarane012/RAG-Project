import numpy as np
import pytest

from src import embedder
from src.embedder import CachedEmbedder, HostedEmbedder, LocalEmbedder, QuotaExceeded, text_key


class Fake:
    """Deterministic 4-d 'embeddings' so tests can tell which text produced which vector."""
    name = "fake"

    def __init__(self):
        self.calls = []

    def passages(self, texts):
        self.calls.append(list(texts))
        return [[float(len(t)), 1.0, 0.0, 0.0] for t in texts]

    def query(self, text):
        return [9.0, 9.0, 9.0, 9.0]


def test_cache_embeds_each_distinct_text_once_and_returns_vectors_in_order(tmp_path):
    fake = Fake()
    emb = CachedEmbedder(fake, cache_dir=tmp_path, shard_size=2)
    out = emb.passages(["aa", "bbbb", "aa", "c"])
    assert [v[0] for v in out] == [2.0, 4.0, 2.0, 1.0]                       # order preserved, duplicates share a vector
    assert sorted(len(c) for c in fake.calls) == [1, 2] and emb.misses == 3  # 3 distinct texts, in shards of 2
    again = emb.passages(["c", "aa"])
    assert [v[0] for v in again] == [1.0, 2.0] and emb.hits == 3          # 1 duplicate in call 1 + 2 cached in call 2
    assert len(fake.calls) == 2                                              # nothing re-embedded


def test_cache_survives_a_new_process_and_is_keyed_by_content(tmp_path):
    CachedEmbedder(Fake(), cache_dir=tmp_path).passages(["hello", "world"])
    fake2 = Fake()
    emb2 = CachedEmbedder(fake2, cache_dir=tmp_path)
    assert [v[0] for v in emb2.passages(["world", "hello"])] == [5.0, 5.0] and fake2.calls == []
    emb2.passages(["brand new"])
    assert fake2.calls == [["brand new"]]
    assert text_key("passage", "x") != text_key("query", "x") != text_key("passage", "x", model="other-model")


def test_a_crash_between_shards_loses_only_the_unfinished_shard(tmp_path):
    class Boom(Fake):
        def passages(self, texts):
            if len(self.calls) == 1:
                raise RuntimeError("network")
            return super().passages(texts)

    emb = CachedEmbedder(Boom(), cache_dir=tmp_path, shard_size=2)
    with pytest.raises(RuntimeError):
        emb.passages(["a", "bb", "ccc", "dddd"])
    fresh = Fake()
    CachedEmbedder(fresh, cache_dir=tmp_path, shard_size=2).passages(["a", "bb", "ccc", "dddd"])
    assert fresh.calls == [["ccc", "dddd"]]                                  # first shard was already saved


def test_the_cache_stores_float32_and_no_temp_files_remain(tmp_path):
    CachedEmbedder(Fake(), cache_dir=tmp_path).passages(["a"])
    assert not list(tmp_path.glob("*.tmp*"))
    with np.load(next(tmp_path.glob("emb-*.npz"))) as z:
        assert z["vectors"].dtype == np.float32 and z["hashes"].shape == (1,)


class Resp:
    def __init__(self, status=200, payload=None, text=""):
        self.status_code, self._p, self.text = status, payload or {}, text

    def json(self):
        return self._p


def hosted(posts, sleeps=None):
    it = iter(posts)
    sent = []

    def post(url, json=None, headers=None, timeout=None):
        sent.append((url, json, headers))
        return next(it)

    return HostedEmbedder(api_key="k", batch=2, post=post, sleep=(sleeps.append if sleeps is not None else lambda s: None)), sent


def ok(n, tokens=7):
    return Resp(200, {"data": [{"values": [0.1] * 4} for _ in range(n)], "usage": {"total_tokens": tokens}})


def test_hosted_batches_requests_and_counts_tokens():
    h, sent = hosted([ok(2), ok(1)])
    vecs = h.passages(["a", "b", "c"])
    assert len(vecs) == 3 and h.tokens_used == 14
    assert [len(s[1]["inputs"]) for s in sent] == [2, 1]
    url, body, headers = sent[0]
    assert url.endswith("/embed") and body["model"] == "multilingual-e5-large"
    assert body["parameters"] == {"input_type": "passage", "truncate": "END"} and headers["Api-Key"] == "k"


def test_hosted_query_uses_the_query_input_type():
    h, sent = hosted([ok(1)])
    h.query("hindi ner")
    assert sent[0][1]["parameters"]["input_type"] == "query"


def test_hosted_retries_rate_limits_then_succeeds_and_raises_clearly_on_quota():
    sleeps = []
    h, _ = hosted([Resp(429, text="slow down"), Resp(503), ok(1)], sleeps)
    assert len(h.passages(["a"])) == 1 and sleeps == [1, 2]
    h, _ = hosted([Resp(429, text="Monthly token quota exceeded for this project")])
    with pytest.raises(QuotaExceeded):
        h.passages(["a"])
    h, _ = hosted([Resp(400, text="bad input")])
    with pytest.raises(RuntimeError, match="HTTP 400"):
        h.passages(["a"])
    h, _ = hosted([Resp(429, text="x")] * 6)
    with pytest.raises(RuntimeError, match="rate limited"):
        h.passages(["a"])


def test_local_embedder_applies_the_e5_prefixes_and_normalises():
    seen = {}

    class Model:
        def encode(self, x, normalize_embeddings=False, batch_size=None):
            seen["x"], seen["norm"] = x, normalize_embeddings
            return np.zeros((len(x), 4)) if isinstance(x, list) else np.zeros(4)

    e = LocalEmbedder(model=Model())
    e.passages(["a", "b"])
    assert seen["x"] == ["passage: a", "passage: b"] and seen["norm"] is True
    e.query("q")
    assert seen["x"] == "query: q"


def test_backend_selection(monkeypatch):
    monkeypatch.delenv("EMBED_BACKEND", raising=False)
    assert embedder.load_embedder("pinecone", cached=False).name == "pinecone"
    assert embedder.load_embedder("local", cached=False).name == "local"
    monkeypatch.setenv("EMBED_BACKEND", "pinecone")
    assert embedder.load_embedder(cached=False).name == "pinecone"
    with pytest.raises(ValueError):
        embedder.load_embedder("openai")


def test_hosted_usage_is_logged_per_shard_and_totalled_across_runs(tmp_path):
    h, _ = hosted([ok(2, tokens=10), ok(1, tokens=5), ok(2, tokens=7)])
    emb = CachedEmbedder(h, cache_dir=tmp_path, shard_size=3)
    emb.passages(["a", "b", "c"])                            # batch=2 -> two requests, one shard
    assert emb.tokens_total() == 15
    emb2 = CachedEmbedder(h, cache_dir=tmp_path, shard_size=3)
    emb2.passages(["a", "d", "e"])                           # 'a' is cached; d, e are new
    assert CachedEmbedder(Fake(), cache_dir=tmp_path).tokens_total() == 22     # a fresh process still sees the total
    CachedEmbedder(Fake(), cache_dir=tmp_path).passages(["zzz"])                # a backend with no usage adds nothing
    assert CachedEmbedder(Fake(), cache_dir=tmp_path).tokens_total() == 22


def test_query_vectors_are_cached_on_disk_and_distinct_from_passage_vectors(tmp_path):
    fake = Fake()
    emb = CachedEmbedder(fake, cache_dir=tmp_path)
    q1 = emb.query("hindi ner")
    assert q1 == [9.0] * 4 and emb.query("hindi ner") == q1
    fresh = Fake()
    fresh.query = lambda t: (_ for _ in ()).throw(AssertionError("must come from the cache"))
    assert CachedEmbedder(fresh, cache_dir=tmp_path).query("hindi ner") == q1
    emb.passages(["hindi ner"])                       # same text as a passage is a DIFFERENT vector (e5 prefix)
    assert emb.passages(["hindi ner"])[0] != q1
