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


def test_candidate_listing_only_uses_arguments_the_real_hub_library_accepts():
    """A live run once failed on `list_models(language=...)`, which does not exist. Calls are checked
    against the installed library's real signature so API drift is caught offline."""
    import inspect

    from huggingface_hub import HfApi

    allowed = set(inspect.signature(HfApi.list_models).parameters)
    seen = []

    class Rec:
        def list_models(self, **kw):
            seen.append(kw)
            assert set(kw) <= allowed, f"not accepted by huggingface_hub: {set(kw) - allowed}"
            return []

    ingest.candidate_ids(Rec(), tasks=("translation",))
    assert any(kw.get("filter") in ingest.INDIC_LANGS for kw in seen)            # Indic via tags
    assert any(kw.get("sort") == "downloads" and kw.get("limit") == ingest.TOP_N for kw in seen)   # top-N
    assert all(kw["pipeline_tag"] == "translation" for kw in seen)


class FakeResp:
    def __init__(self, status, headers=None):
        self.status_code, self.headers = status, headers or {}

    def raise_for_status(self):
        raise requests.HTTPError(str(self.status_code))


def test_retry_wait_honours_the_server_hint_and_caps_it():
    assert ingest._retry_wait(FakeResp(429, {"retry-after": "42"}), 0) == 42
    assert ingest._retry_wait(FakeResp(429, {"ratelimit": '"api";r=0;t=17'}), 0) == 17      # HF's header
    assert ingest._retry_wait(FakeResp(429, {"retry-after": "99999"}), 0) == 300               # never sleep for hours
    assert ingest._retry_wait(FakeResp(429, {"retry-after": "soon"}), 3) == 8                  # garbage -> back-off
    assert ingest._retry_wait(FakeResp(503), 2) == 4 and ingest._retry_wait(FakeResp(503), 20) == 60
    assert ingest._retry_wait(FakeResp(429, {"retry-after": "0"}), 0) == 1                     # never a busy loop


def test_get_sleeps_the_hinted_time_then_succeeds(monkeypatch):
    seq = [FakeResp(429, {"retry-after": "3"}), FakeResp(200)]
    slept = []
    monkeypatch.setattr(ingest.requests, "get", lambda *a, **k: seq.pop(0))
    monkeypatch.setattr(ingest.time, "sleep", slept.append)
    assert ingest._get("http://x").status_code == 200 and slept == [3.0]


def test_get_gives_up_with_an_error_after_the_retries(monkeypatch):
    monkeypatch.setattr(ingest.requests, "get", lambda *a, **k: FakeResp(429, {"retry-after": "1"}))
    monkeypatch.setattr(ingest.time, "sleep", lambda s: None)
    with pytest.raises(requests.HTTPError):
        ingest._get("http://x", retries=3)


def test_a_forbidden_readme_is_a_logged_failure_not_a_silent_empty_card(raw_dir, monkeypatch):
    """The raw endpoint answers 403 for some public repos; that must not be cached as 'no README'."""
    def fake_get(url, params=None, retries=5):
        if "/api/" in url:
            return Resp(payload={"id": "a/b"})
        assert "/resolve/main/README.md" in url, url           # the resolver, not /raw/
        return Resp(status=403)

    monkeypatch.setattr(ingest, "_get", fake_get)
    with pytest.raises(requests.HTTPError):
        ingest.fetch_raw("a/b")
    assert not ingest.raw_path("a/b", ".md").exists()           # nothing cached: a rerun retries it
