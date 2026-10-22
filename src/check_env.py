"""Create and validate `.env` without ever printing a secret.

    python -m src.check_env --init    # copy .env.example to .env (never overwrites)
    python -m src.check_env           # report what is set; exit 1 if something needed is missing

Only variable *names* and set/missing status are printed, never values, so the output is
safe to paste into a chat or an issue.
"""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path

from src.config import CFG

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE, ENV_EXAMPLE = ROOT / ".env", ROOT / ".env.example"

# variable -> (needed for, kind)
NEEDED = {
    "groq": {"GROQ_API_KEY": "the Groq LLM provider"},
    "ollama": {},
}
ALWAYS = {"PINECONE_API_KEY": "retrieval and indexing (not needed for tests or REPLAY=1)"}
OPTIONAL = {"HF_TOKEN": "higher Hub rate limits during ingestion"}
_PLACEHOLDERS = {"changeme", "your_key", "your-key", "xxx", "todo", "<key>"}


def init_env(example: Path = ENV_EXAMPLE, target: Path = ENV_FILE) -> bool:
    """Copy the example to .env. Returns False (and changes nothing) if .env exists."""
    if target.exists():
        return False
    target.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
    try:
        target.chmod(stat.S_IRUSR | stat.S_IWUSR)  # keys: owner read/write only
    except OSError:
        pass  # e.g. Windows
    return True


def _usable(value: str | None) -> bool:
    v = (value or "").strip()
    return bool(v) and v.lower() not in _PLACEHOLDERS


def _git_says(args: list[str]) -> bool | None:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True).returncode == 0
    except OSError:
        return None  # no git available


def check(env: dict[str, str] | None = None) -> dict:
    """Status of every variable we use. Pure function of `env` (default: os.environ)."""
    env = dict(os.environ) if env is None else env
    provider = (env.get("LLM_PROVIDER") or "groq").strip().lower()
    problems: list[str] = []
    if provider not in NEEDED:
        problems.append(f"LLM_PROVIDER must be 'groq' or 'ollama', got {provider!r}")
    rows = []
    for group, names, required in (
        ("required", NEEDED.get(provider, {}), True),
        ("live", ALWAYS, True),
        ("optional", OPTIONAL, False),
    ):
        for name, why in names.items():
            ok = _usable(env.get(name))
            rows.append({"name": name, "group": group, "set": ok, "why": why})
            if required and not ok and group == "required":
                problems.append(f"{name} is not set ({why})")
    model_var, cfg_key = ("GROQ_MODEL", "groq_model") if provider == "groq" else ("OLLAMA_MODEL", "ollama_model")
    return {
        "provider": provider,
        "model": (env.get(model_var) or "").strip() or CFG["llm"].get(cfg_key),
        "model_source": "env override" if (env.get(model_var) or "").strip() else "config.yaml",
        "rows": rows,
        "problems": problems,
        "live_ready": not problems and all(r["set"] for r in rows if r["group"] == "live"),
    }


def main(argv: list[str]) -> int:
    if "--init" in argv:
        created = init_env()
        print(f"{'created' if created else 'already exists, left unchanged'}: {ENV_FILE}")
        if created:
            print("Now open it and fill in the secrets (see the comments for where to get each key).")
    print(f".env file: {'present' if ENV_FILE.exists() else 'MISSING (run with --init)'}")
    ignored, tracked = _git_says(["check-ignore", "-q", ".env"]), _git_says(["ls-files", "--error-unmatch", ".env"])
    if ignored is False or tracked:
        print("!! .env is NOT safely ignored by git. Fix .gitignore before adding any secret.")
        return 1
    report = check()
    print(f"provider: {report['provider']}   model: {report['model']} ({report['model_source']})")
    for r in report["rows"]:
        print(f"  {'ok     ' if r['set'] else 'MISSING'}  {r['name']:18s} [{r['group']}]  {r['why']}")
    for p in report["problems"]:
        print(f"!! {p}")
    print("live pipeline ready" if report["live_ready"] else "not ready for the live pipeline (tests and REPLAY=1 still work)")
    return 1 if report["problems"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
