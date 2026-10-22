import json

import pytest
import requests

from src import ingest, snapshot

RAW_A = {"id": "org/a", "pipeline_tag": "token-classification", "downloads": 5, "tags": [],
         "cardData": {"language": ["mr", "multilingual"], "license": "gpl-3.0", "base_model": "xlm-roberta-base",
                      "model-index": [{"results": []}]},
         "siblings": [{"rfilename": "model.safetensors", "size": 400_000_000}], "safetensors": {"total": 100_000_000}}
RAW_B = {"id": "org/b", "pipeline_tag": "translation", "tags": [], "cardData": {"license": "weird"},
         "siblings": [{"rfilename": "adapter_model.safetensors", "size": 1}]}
CARD = "# A\n" + "A real description of what this model does and how. " * 8


def write_raw(d, raw, card):
    (d / (raw["id"].replace("/", "__") + ".json")).write_text(json.dumps(raw), encoding="utf-8")
    (d / (raw["id"].replace("/", "__") + ".md")).write_text(card, encoding="utf-8")


@pytest.fixture
def raw_dir(tmp_path):
    d = tmp_path / "raw"
    d.mkdir()
    write_raw(d, RAW_A, CARD)
    write_raw(d, RAW_B, "")
    (d / "_canonical_ids.json").write_text(json.dumps({"xlm-roberta-base": "FacebookAI/xlm-roberta-base"}))
    (d / "failed.jsonl").write_text("{}\n")
    return d


def test_build_is_deterministic_and_applies_canonical_ids(raw_dir, tmp_path):
    out1, sha1, _, report = snapshot.build(raw_dir, tmp_path / "s1", today="2026-10-23")
    out2, sha2, _, _ = snapshot.build(raw_dir, tmp_path / "s2", today="2026-10-23")
    assert sha1 == sha2 and snapshot.sha256_of(out1) == sha1       # same bytes: checksums are meaningful
    recs = snapshot.load_snapshot(out1, expected_sha256=sha1)
    assert [r["model_id"] for r in recs] == ["org/a", "org/b"]
    assert recs[0]["base_model"] == "FacebookAI/xlm-roberta-base"
    assert recs[0]["doc_quality"] == "full" and recs[1]["doc_quality"] == "minimal"
    assert report["models"] == 2


def test_wrong_checksum_is_refused(raw_dir, tmp_path):
    out, sha, _, _ = snapshot.build(raw_dir, tmp_path / "s", today="2026-10-23")
    with pytest.raises(ValueError, match="checksum"):
        snapshot.load_snapshot(out, expected_sha256="0" * 64)


def test_data_quality_report_counts_what_the_docs_promise(raw_dir, tmp_path):
    _, _, _, r = snapshot.build(raw_dir, tmp_path / "s", today="2026-10-23")
    assert r["per_task"] == {"token-classification": 1, "translation": 1}
    assert r["size_unknown"] == {"count": 1, "pct": 50.0, "by_reason": {"adapter_only": 1}}
    assert r["top_unmapped_licenses"] == [("weird", 1)]
    assert r["commercial_unknown_pct"] == 50.0 and r["multilingual_pct"] == 50.0
    assert "multilingual" in r["raw_language_tokens_not_2_letters"]
    assert r["base_model_pct"] == 50.0 and r["param_count_pct"] == 50.0
    assert r["doc_minimal_pct"] == 50.0 and r["model_index_pct"] == 50.0


def test_empty_snapshot_does_not_divide_by_zero():
    assert snapshot.data_quality_report([])["models"] == 0


class Resp:
    def __init__(self, status=200, payload=None):
        self.status_code, self._p = status, payload or {}

    def json(self):
        return self._p


def test_canonicalize_resolves_caches_and_never_asks_twice(tmp_path, monkeypatch):
    calls = []

    def fake_get(url, params=None, retries=5):
        calls.append(url)
        return Resp(200, {"id": "FacebookAI/xlm-roberta-base"}) if url.endswith("/xlm-roberta-base") else Resp(404)

    monkeypatch.setattr(ingest, "_get", fake_get)
    cache = tmp_path / "_canonical_ids.json"
    out = ingest.canonicalize({"xlm-roberta-base", "gone/model", "./local/path", "http://x/y"}, cache)
    assert out["xlm-roberta-base"] == "FacebookAI/xlm-roberta-base"
    assert out["gone/model"] == "gone/model" and out["./local/path"] == "./local/path"
    assert len(calls) == 2                                   # local path and URL never hit the network
    ingest.canonicalize({"xlm-roberta-base", "gone/model"}, cache)
    assert len(calls) == 2                                   # second run: all cached


def test_canonicalize_leaves_network_failures_uncached_so_a_rerun_retries(tmp_path, monkeypatch):
    def boom(url, params=None, retries=5):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(ingest, "_get", boom)
    cache = tmp_path / "_canonical_ids.json"
    assert "a/b" not in ingest.canonicalize({"a/b"}, cache)
    monkeypatch.setattr(ingest, "_get", lambda url, params=None, retries=5: Resp(200, {"id": "new/b"}))
    assert ingest.canonicalize({"a/b"}, cache)["a/b"] == "new/b"
