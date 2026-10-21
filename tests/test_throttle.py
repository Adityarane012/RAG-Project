import json

import pytest

from src import llm
from src.llm import TokenBudget


class Clock:
    def __init__(self):
        self.t = 0.0
        self.slept = []

    def now(self):
        return self.t

    def sleep(self, s):
        self.slept.append(s)
        self.t += s


def budget(tpm):
    c = Clock()
    return TokenBudget(tpm, clock=c.now, sleep=c.sleep), c


def test_calls_that_fit_do_not_wait_and_the_next_one_waits_for_the_window():
    b, c = budget(8000)
    assert b.acquire(5000) == 0 and b.acquire(2500) == 0         # 7,500 used
    waited = b.acquire(2000)                                      # would be 9,500: must wait for the first to age out
    assert 59 <= waited <= 61 and c.t == pytest.approx(60, abs=1)


def test_old_usage_expires():
    b, c = budget(8000)
    b.acquire(8000)
    c.t += 61
    assert b.acquire(8000) == 0


def test_zero_budget_means_no_throttling_and_oversized_requests_use_one_whole_window():
    b, c = budget(0)
    assert b.acquire(10**9) == 0 and c.slept == []
    b, c = budget(6000)
    assert b.acquire(7000) == 0          # capped to the whole budget, not an error
    assert b.acquire(100) > 0            # ...but it filled the window


def test_extraction_then_a_full_size_explanation_in_the_same_minute_fit_under_8k(monkeypatch, tmp_path):
    """The case that matters in production: a query's extraction call, then its explain call
    at the full prompt budget, one right after the other."""
    c = Clock()
    cfg = llm.CFG
    monkeypatch.setattr(llm, "_budgets", {"openai/gpt-oss-20b": TokenBudget(8000, clock=c.now, sleep=c.sleep)})
    monkeypatch.setattr(llm, "CACHE_DIR", tmp_path)
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    monkeypatch.setitem(llm._PROVIDERS, "groq", (lambda p, s, m: "{}", "GROQ_MODEL", "groq_model"))
    explain_words = int(cfg["explain"]["max_prompt_tokens"] / 1.5)                  # a prompt at the full budget
    llm.complete("extract " * 150, reserve=cfg["llm"]["extract_output_reserve_tokens"])   # ~230-token prompt + 600 reserve
    llm.complete("explain " * explain_words, system="")                                    # ~5,000 + 1,500 reserve
    assert c.t == 0, "a normal query must not stall on its own two calls (8K budget)"
    llm.complete("a second explain call " * (explain_words // 4))                          # a second query in the same minute
    assert c.t >= 59                                                                       # ...is made to wait for the window


class RateLimitError(Exception):
    def __init__(self, retry_after=None):
        super().__init__("429")
        self.response = type("R", (), {"headers": {"retry-after": retry_after} if retry_after is not None else {}})()


def provider(monkeypatch, tmp_path, fn):
    monkeypatch.setattr(llm, "CACHE_DIR", tmp_path)
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    monkeypatch.setitem(llm._PROVIDERS, "groq", (fn, "GROQ_MODEL", "groq_model"))


def test_short_retry_after_waits_and_retries_the_same_model(monkeypatch, tmp_path):
    calls, slept = [], []
    monkeypatch.setattr(llm, "_sleep", slept.append)

    def fn(p, s, m):
        calls.append(m)
        if len(calls) == 1:
            raise RateLimitError("7")
        return '{"ok": 1}'

    provider(monkeypatch, tmp_path, fn)
    assert llm.complete("q") == '{"ok": 1}'
    assert calls == [llm.CFG["llm"]["groq_model"]] * 2 and slept == [7.0]       # no fallback needed
    assert json.loads(next(tmp_path.glob("*.json")).read_text(encoding="utf-8"))["model"] == llm.CFG["llm"]["groq_model"]


def test_long_retry_after_goes_straight_to_the_fallback_model(monkeypatch, tmp_path):
    calls, slept = [], []
    monkeypatch.setattr(llm, "_sleep", slept.append)

    def fn(p, s, m):
        calls.append(m)
        if m == llm.CFG["llm"]["groq_model"]:
            raise RateLimitError("3600")        # e.g. the daily limit
        return "{}"

    provider(monkeypatch, tmp_path, fn)
    llm.complete("q")
    assert calls[-1] == llm.CFG["llm"]["groq_fallback_model"] and slept == []        # never sleeps an hour


def test_still_limited_after_waiting_falls_back_then_gives_up(monkeypatch, tmp_path):
    calls = []

    def fn(p, s, m):
        calls.append(m)
        raise RateLimitError("2")

    provider(monkeypatch, tmp_path, fn)
    with pytest.raises(RateLimitError):
        llm.complete("q")
    assert calls == [llm.CFG["llm"]["groq_model"]] * 2 + [llm.CFG["llm"]["groq_fallback_model"]]


def test_garbage_retry_after_is_ignored():
    for bad in ("soon", "", None):
        e = RateLimitError()
        e.response.headers = {"retry-after": bad}
        assert llm._retry_after(e) is None
    assert llm._retry_after(ValueError("no response attr")) is None


def test_ollama_gets_an_explicit_context_window_big_enough_for_the_explain_prompt(monkeypatch):
    import requests

    sent = {}

    class R:
        def raise_for_status(self): pass
        def json(self): return {"response": "{}"}

    monkeypatch.setattr(requests, "post", lambda url, json=None, timeout=None: sent.update(json) or R())
    llm._call_ollama("p", "s", "qwen2.5:7b-instruct")
    assert sent["options"]["num_ctx"] == llm.CFG["llm"]["ollama_num_ctx"]
    assert llm.CFG["llm"]["ollama_num_ctx"] >= llm.CFG["explain"]["max_prompt_tokens"] + 1500


def test_pinned_budgets_match_the_documented_free_tier():
    from src.config import load_config      # conftest blanks the live config; read the file itself

    assert load_config()["llm"]["tpm"]["openai/gpt-oss-20b"] == 8000
    cfg = load_config()
    assert cfg["explain"]["max_prompt_tokens"] + cfg["llm"]["output_reserve_tokens"] <= 8000
