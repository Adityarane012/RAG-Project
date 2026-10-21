import stat
import sys

import pytest

from src import check_env


def ok(**extra):
    return {"GROQ_API_KEY": "k", "PINECONE_API_KEY": "p", **extra}


def test_complete_groq_setup_is_live_ready_and_model_comes_from_config():
    r = check_env.check(ok())
    assert r["problems"] == [] and r["live_ready"] is True
    assert (r["provider"], r["model"], r["model_source"]) == ("groq", "openai/gpt-oss-20b", "config.yaml")


def test_missing_groq_key_is_a_problem_but_pinecone_only_blocks_live():
    r = check_env.check({"PINECONE_API_KEY": "p"})
    assert any("GROQ_API_KEY" in p for p in r["problems"]) and not r["live_ready"]
    r = check_env.check({"GROQ_API_KEY": "k"})
    assert r["problems"] == [] and r["live_ready"] is False       # tests and REPLAY=1 still fine


def test_ollama_needs_no_api_key_and_reports_its_model():
    r = check_env.check({"LLM_PROVIDER": "ollama", "PINECONE_API_KEY": "p", "OLLAMA_MODEL": "qwen2.5:3b"})
    assert r["problems"] == [] and r["model"] == "qwen2.5:3b" and r["model_source"] == "env override"


def test_blank_whitespace_and_placeholder_values_count_as_missing():
    for bad in ("", "   ", "changeme", "YOUR_KEY"):
        assert check_env.check({"GROQ_API_KEY": bad, "PINECONE_API_KEY": "p"})["problems"], bad


def test_unknown_provider_is_reported():
    assert any("LLM_PROVIDER" in p for p in check_env.check(ok(LLM_PROVIDER="openai"))["problems"])


def test_secret_values_are_never_printed(monkeypatch, capsys):
    monkeypatch.setenv("GROQ_API_KEY", "SECRET-groq-VALUE-123")
    monkeypatch.setenv("PINECONE_API_KEY", "SECRET-pine-VALUE-456")
    monkeypatch.setenv("HF_TOKEN", "SECRET-hf-VALUE-789")
    check_env.main([])
    out = capsys.readouterr().out
    assert "SECRET" not in out and "VALUE" not in out
    assert "GROQ_API_KEY" in out and "ok" in out


def test_init_creates_from_example_never_overwrites_and_restricts_permissions(tmp_path):
    example, target = tmp_path / ".env.example", tmp_path / ".env"
    example.write_text("GROQ_API_KEY=\n", encoding="utf-8")
    assert check_env.init_env(example, target) is True
    assert target.read_text(encoding="utf-8") == "GROQ_API_KEY=\n"
    target.write_text("GROQ_API_KEY=mine\n", encoding="utf-8")
    assert check_env.init_env(example, target) is False
    assert target.read_text(encoding="utf-8") == "GROQ_API_KEY=mine\n"          # untouched
    if sys.platform != "win32":
        assert stat.S_IMODE(target.stat().st_mode) == 0o600


def test_example_file_lists_every_variable_the_checker_and_llm_read_and_has_no_secrets():
    text = check_env.ENV_EXAMPLE.read_text(encoding="utf-8")
    for name in ("GROQ_API_KEY", "HF_TOKEN", "PINECONE_API_KEY", "LLM_PROVIDER", "OLLAMA_HOST",
                 "GROQ_MODEL", "OLLAMA_MODEL"):
        assert f"{name}=" in text, name
    for line in text.splitlines():
        if "_KEY=" in line or "TOKEN=" in line:
            assert line.split("=", 1)[1].strip() == "", f"example must not contain a value: {line}"
