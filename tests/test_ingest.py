import json

import pytest
import requests

from src import ingest


class Resp:
    def __init__(self, status=200, payload=None, text=""):
        self.status_code, self._payload, self.text = status, payload or {}, text

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")


@pytest.fixture
def raw_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(ingest, "RAW_DIR", tmp_path)
    return tmp_path


def test_fetch_is_cached_and_never_repeated(raw_dir, monkeypatch):
    calls = []
    monkeypatch.setattr(ingest, "_get", lambda url, params=None, retries=5: calls.append(url) or
                        (Resp(payload={"id": "a/b"}) if "/api/" in url else Resp(text="# card")))
    assert ingest.fetch_raw("a/b") is True and len(calls) == 2
    assert ingest.fetch_raw("a/b") is False and len(calls) == 2
    assert ingest.load_raw("a/b") == ({"id": "a/b"}, "# card")


def test_missing_readme_is_cached_as_empty_card(raw_dir, monkeypatch):
    monkeypatch.setattr(ingest, "_get", lambda url, params=None, retries=5:
                        Resp(payload={"id": "a/b"}) if "/api/" in url else Resp(status=404))
    ingest.fetch_raw("a/b")
    assert ingest.load_raw("a/b")[1] == ""


def test_http_error_propagates_from_fetch_and_is_loggable(raw_dir, monkeypatch):
    monkeypatch.setattr(ingest, "_get", lambda url, params=None, retries=5: Resp(status=404))
    with pytest.raises(requests.HTTPError) as e:
        ingest.fetch_raw("gone/model")
    ingest.log_failure("gone/model", e.value)
    line = json.loads((raw_dir / "failed.jsonl").read_text().strip())
    assert line["model_id"] == "gone/model" and "HTTPError" in line["error"]
    assert not ingest.raw_path("gone/model", ".json").exists()  # nothing half-written to resume from


def test_writes_are_atomic_and_leave_no_temp_files(raw_dir, monkeypatch):
    monkeypatch.setattr(ingest, "_get", lambda url, params=None, retries=5:
                        Resp(payload={"id": "a/b"}) if "/api/" in url else Resp(text="# card"))
    ingest.fetch_raw("a/b")
    assert not list(raw_dir.glob("*.tmp"))


def test_resume_fetches_only_the_missing_half(raw_dir, monkeypatch):
    ingest.raw_path("a/b", ".json").write_text('{"id": "a/b"}')  # info cached, card missing
    urls = []
    monkeypatch.setattr(ingest, "_get", lambda url, params=None, retries=5: urls.append(url) or Resp(text="# card"))
    assert ingest.fetch_raw("a/b") is True
    assert len(urls) == 1 and urls[0].endswith("README.md")


def test_devanagari_round_trips_regardless_of_platform_encoding(raw_dir, monkeypatch):
    card = "# मराठी मॉडेल\nहे मॉडेल नाव ओळखते."
    monkeypatch.setattr(ingest, "_get", lambda url, params=None, retries=5:
                        Resp(payload={"id": "a/b"}) if "/api/" in url else Resp(text=card))
    ingest.fetch_raw("a/b")
    assert ingest.raw_path("a/b", ".md").read_bytes() == card.encode("utf-8")
    assert ingest.load_raw("a/b")[1] == card
