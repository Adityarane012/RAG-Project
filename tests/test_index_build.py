import json

from src import index
from src.embedder import CachedEmbedder


class FakeIndex:
    def __init__(self):
        self.calls = []

    def upsert(self, vectors, namespace):
        self.calls.append((namespace, [v["id"] for v in vectors]))


class FakeEmb:
    def __init__(self):
        self.seen = []

    def passages(self, texts):
        self.seen += texts
        return [[1.0, 0.0] for _ in texts]


def chunk(model, i):
    return {"id": f"{model}::{i}", "text": f"{model} text {i}", "metadata": {"model_id": model, "section": f"s{i}"}}


CHUNKS = [chunk("a/m", 0), chunk("a/m", 1), chunk("b/m", 0), chunk("b/m", 1), chunk("b/m", 2), chunk("c/m", 0)]


def test_upserts_every_chunk_once_in_batches_and_records_finished_models(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    idx = FakeIndex()
    stats = index.run_build(CHUNKS, FakeEmb(), "exp-t", idx, embed_batch=4, upsert_batch=3, log=lambda *a: None)
    sent = [i for _, ids in idx.calls for i in ids]
    assert sorted(sent) == sorted(c["id"] for c in CHUNKS) and len(sent) == len(set(sent))
    assert stats["upserted"] == 6 and all(len(ids) <= 3 for _, ids in idx.calls)
    assert index.done_models("exp-t") == {"a/m", "b/m", "c/m"}


def test_a_model_split_across_batches_is_not_marked_done_until_its_last_chunk_is_in(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    class Crash(FakeIndex):
        def upsert(self, vectors, namespace):
            if any(v["id"] == "b/m::2" for v in vectors):
                raise RuntimeError("connection lost")      # dies on the batch holding b/m's last chunk
            super().upsert(vectors, namespace)

    idx = Crash()
    try:
        index.run_build(CHUNKS, FakeEmb(), "exp-t", idx, embed_batch=4, upsert_batch=10, log=lambda *a: None)
    except RuntimeError:
        pass
    assert index.done_models("exp-t") == {"a/m"}           # b/m straddles the batch boundary: must NOT be recorded
    good = FakeIndex()
    index.run_build(CHUNKS, FakeEmb(), "exp-t", good, embed_batch=4, upsert_batch=10, log=lambda *a: None)
    resent = sorted(i for _, ids in good.calls for i in ids)
    assert resent == ["b/m::0", "b/m::1", "b/m::2", "c/m::0"]      # all of b/m again, a/m skipped
    assert index.done_models("exp-t") == {"a/m", "b/m", "c/m"}


def test_a_second_run_with_everything_done_embeds_and_upserts_nothing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    index.run_build(CHUNKS, FakeEmb(), "exp-t", FakeIndex(), log=lambda *a: None)
    emb, idx = FakeEmb(), FakeIndex()
    stats = index.run_build(CHUNKS, emb, "exp-t", idx, log=lambda *a: None)
    assert emb.seen == [] and idx.calls == [] and stats["skipped_done"] == 6


def test_embed_only_never_touches_an_index_or_writes_progress(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    emb = FakeEmb()
    stats = index.run_build(CHUNKS, emb, "exp-t", index=None, log=lambda *a: None)
    assert stats["embedded"] == 6 and stats["upserted"] == 0 and len(emb.seen) == 6
    assert not index.progress_path("exp-t").exists()


def test_namespaces_keep_separate_progress(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    index.run_build(CHUNKS[:2], FakeEmb(), "exp-one", FakeIndex(), log=lambda *a: None)
    assert index.done_models("exp-one") == {"a/m"} and index.done_models("exp-two") == set()


def test_prepare_all_reads_the_cache_applies_canonical_ids_and_limits(tmp_path):
    raw = {"id": "o/m", "pipeline_tag": "translation", "cardData": {"language": ["hi"], "license": "mit", "base_model": "xlm-roberta-base"},
           "siblings": [{"rfilename": "model.safetensors", "size": 1_000_000}]}
    (tmp_path / "o__m.json").write_text(json.dumps(raw), encoding="utf-8")
    (tmp_path / "o__m.md").write_text("# Overview\n" + "A useful description of what this model does. " * 10, encoding="utf-8")
    (tmp_path / "_canonical_ids.json").write_text(json.dumps({"xlm-roberta-base": "FacebookAI/xlm-roberta-base"}), encoding="utf-8")
    (tmp_path / "x__no_card.json").write_text(json.dumps({"id": "x/no_card"}), encoding="utf-8")     # no .md: skipped
    chunks = index.prepare_all(raw_dir=tmp_path)
    assert {c["metadata"]["model_id"] for c in chunks} == {"o/m"}
    assert chunks[0]["metadata"]["base_model"] == "FacebookAI/xlm-roberta-base"
    assert index.prepare_all(raw_dir=tmp_path, limit=0) == []
    assert all(len(json.dumps(c["metadata"]).encode()) < 40_000 for c in chunks)                      # Pinecone's per-vector limit


def test_a_local_index_build_is_not_resumed_from_pinecone_progress(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    index.run_build(CHUNKS, FakeEmb(), "ns", FakeIndex(), log=lambda *a: None)            # a Pinecone-style run recorded progress
    from src.localindex import LocalIndex

    local = LocalIndex()
    index.run_build(CHUNKS, FakeEmb(), "ns", local, log=lambda *a: None, resume=False)
    assert local.count("ns") == 6                       # nothing skipped: a fresh in-memory index needs every chunk


def test_store_backend_selection(monkeypatch):
    import pytest

    monkeypatch.delenv("INDEX_BACKEND", raising=False)
    assert index.store_backend() == "local"
    monkeypatch.setenv("INDEX_BACKEND", "Pinecone")
    assert index.store_backend() == "pinecone"
    monkeypatch.setenv("INDEX_BACKEND", "faiss")
    with pytest.raises(ValueError):
        index.store_backend()


def test_open_index_loads_a_saved_local_index(tmp_path, monkeypatch):
    from src.config import CFG
    from src.localindex import LocalIndex

    idx = LocalIndex()
    idx.upsert([{"id": "a::0", "values": [1.0, 0.0], "metadata": {"model_id": "a"}}], namespace="demo")
    idx.save(tmp_path, "demo")
    monkeypatch.setitem(CFG["vector_store"], "local_dir", str(tmp_path))
    monkeypatch.delenv("INDEX_BACKEND", raising=False)
    assert index.open_index("demo").count("demo") == 1
