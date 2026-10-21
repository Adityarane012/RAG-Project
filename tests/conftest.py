import pytest

from src import llm


@pytest.fixture(autouse=True)
def isolate_llm_throttle(monkeypatch):
    """The per-minute token throttle is real wall-clock state shared across calls. Tests must
    never wait on it or inherit another test's usage: start every test with no budgets and no
    configured limits. Tests of the throttle itself build their own TokenBudget."""
    monkeypatch.setattr(llm, "_budgets", {})
    monkeypatch.setitem(llm.CFG["llm"], "tpm", {})
    monkeypatch.setattr(llm, "_sleep", lambda seconds: None)
