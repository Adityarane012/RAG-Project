"""Load config.yaml once (D21). Every tunable lives there, not in code."""

from __future__ import annotations

from pathlib import Path

import yaml

try:  # keys live in .env (gitignored); real environment variables take precedence
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)
except ImportError:
    pass

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


def load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


CFG = load_config()
