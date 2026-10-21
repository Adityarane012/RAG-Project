"""Pull model metadata and cards for the 5 tasks (D5, D6), resumable (D21).

Corpus = top ~1,000 models per task by downloads, plus every model in those tasks
tagged with an Indic language. Every raw API response is written to data/raw/ and
never fetched twice, so rate limits and crashes only cost time.

Usage:  python -m src.ingest counts     # day-1 check: models per task, vs. the ~5-8k estimate
        python -m src.ingest fetch      # fetch (or resume fetching) raw metadata + cards
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import requests

from src.config import CFG

TASKS = tuple(CFG["corpus"]["tasks"])
INDIC_LANGS = tuple(CFG["corpus"]["indic_langs"])
TOP_N = CFG["corpus"]["top_n_per_task"]
RAW_DIR = Path("data/raw")
HUB = "https://huggingface.co"


def candidate_ids(api, tasks=TASKS) -> dict[str, set[str]]:
    """Per task: top-N by downloads union all Indic-tagged models (D6).

    `api` is a huggingface_hub.HfApi. Returns {task: {model ids}}.
    """
    out: dict[str, set[str]] = {}
    for task in tasks:
        ids = {m.id for m in api.list_models(pipeline_tag=task, sort="downloads", limit=TOP_N)}
        for lang in INDIC_LANGS:
            ids |= {m.id for m in api.list_models(pipeline_tag=task, language=lang)}
        out[task] = ids
    return out


def raw_path(model_id: str, suffix: str) -> Path:
    return RAW_DIR / (model_id.replace("/", "__") + suffix)


def _get(url: str, params: dict | None = None, retries: int = 5) -> requests.Response:
    headers = {"Authorization": f"Bearer {os.environ['HF_TOKEN']}"} if os.getenv("HF_TOKEN") else {}
    for attempt in range(retries):
        resp = requests.get(url, params=params, headers=headers, timeout=30)
        if resp.status_code == 429 or resp.status_code >= 500:
            time.sleep(min(2 ** attempt, 60) * (1 + attempt))
            continue
        return resp
    resp.raise_for_status()
    return resp


def _write_atomic(path: Path, text: str) -> None:
    """Write then rename, so a crash never leaves a truncated file that a resumed run
    would mistake for a finished fetch."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def fetch_raw(model_id: str) -> bool:
    """Fetch and cache one model's API response and README. Returns False if it was
    already cached (nothing is re-requested for a model we already have)."""
    info_path, card_path = raw_path(model_id, ".json"), raw_path(model_id, ".md")
    if info_path.exists() and card_path.exists():
        return False
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if not info_path.exists():
        resp = _get(f"{HUB}/api/models/{model_id}", params={"blobs": "true", "cardData": "true"})
        resp.raise_for_status()
        _write_atomic(info_path, json.dumps(resp.json()))
    if not card_path.exists():
        resp = _get(f"{HUB}/{model_id}/raw/main/README.md")
        _write_atomic(card_path, resp.text if resp.status_code == 200 else "")  # no card -> empty (minimal doc)
    return True


def log_failure(model_id: str, error: Exception) -> None:
    """Record a model we couldn't fetch so a resumed run doesn't hide it (see failed.jsonl)."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    with open(RAW_DIR / "failed.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"model_id": model_id, "error": f"{type(error).__name__}: {error}"}) + "\n")


def load_raw(model_id: str) -> tuple[dict, str]:
    return (json.loads(raw_path(model_id, ".json").read_text(encoding="utf-8")),
            raw_path(model_id, ".md").read_text(encoding="utf-8"))


def main(argv: list[str]) -> None:
    from huggingface_hub import HfApi

    cmd = argv[0] if argv else "counts"
    per_task = candidate_ids(HfApi())
    all_ids = set().union(*per_task.values())
    for task, ids in per_task.items():
        print(f"{task:32s} {len(ids):6d}")
    print(f"{'TOTAL (unique)':32s} {len(all_ids):6d}   (D6 estimate: ~5,000-8,000)")
    if cmd == "fetch":
        fetched = 0
        for i, model_id in enumerate(sorted(all_ids), 1):
            try:
                fetched += fetch_raw(model_id)
            except requests.RequestException as e:  # deleted, private or erroring: skip, don't loop forever
                log_failure(model_id, e)
            if i % 100 == 0:
                print(f"  {i}/{len(all_ids)} ({fetched} new)")


if __name__ == "__main__":
    main(sys.argv[1:])
