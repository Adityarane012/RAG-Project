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
import re
import sys
import time
from pathlib import Path

import requests

from src.config import CFG

TASKS = tuple(CFG["corpus"]["tasks"])
INDIC_LANGS = tuple(CFG["corpus"]["indic_langs"])
TOP_N = CFG["corpus"]["top_n_per_task"]
RAW_DIR = Path("data/raw")
WORKERS = 6   # a few parallel requests; the Hub quota (not our speed) is the limit, and _get honours its retry hint
HUB = "https://huggingface.co"


def candidate_ids(api, tasks=TASKS) -> dict[str, set[str]]:
    """Per task: top-N by downloads union all Indic-tagged models (D6).

    `api` is a huggingface_hub.HfApi. Returns {task: {model ids}}.
    """
    out: dict[str, set[str]] = {}
    for task in tasks:
        ids = {m.id for m in api.list_models(pipeline_tag=task, sort="downloads", limit=TOP_N)}
        for lang in INDIC_LANGS:
            # language codes are plain Hub tags, so they go through `filter` (list_models has no `language` argument)
            ids |= {m.id for m in api.list_models(pipeline_tag=task, filter=lang)}
        out[task] = ids
    return out


def raw_path(model_id: str, suffix: str) -> Path:
    return RAW_DIR / (model_id.replace("/", "__") + suffix)


def _retry_wait(resp: requests.Response, attempt: int) -> float:
    """Seconds to wait after a 429/5xx: the server's own hint if it sent one (`Retry-After`, or the
    `t=` reset in HF's `RateLimit` header), else exponential back-off. Capped at 5 minutes, the
    length of the Hub's quota window."""
    hint = resp.headers.get("retry-after")
    if hint is None:
        m = re.search(r"\bt=(\d+)", resp.headers.get("ratelimit", ""))
        hint = m.group(1) if m else None
    try:
        wait = float(hint) if hint is not None else min(2 ** attempt, 60)
    except ValueError:
        wait = min(2 ** attempt, 60)
    return min(max(wait, 1.0), 300.0)


def _get(url: str, params: dict | None = None, retries: int = 6) -> requests.Response:
    headers = {"Authorization": f"Bearer {os.environ['HF_TOKEN']}"} if os.getenv("HF_TOKEN") else {}
    resp = None
    resp = None
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=30)
        except (requests.ConnectionError, requests.Timeout):   # dropped connection / proxy hiccup: transient
            if attempt == retries - 1:
                raise
            time.sleep(min(2 ** attempt, 30))
            continue
        if resp.status_code == 429 or resp.status_code >= 500:
            time.sleep(_retry_wait(resp, attempt))
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
        # `resolve`, not `raw`: `raw` answers 403 for some public repos, and `resolve` has the higher quota.
        resp = _get(f"{HUB}/{model_id}/resolve/main/README.md")
        if resp.status_code == 404:
            _write_atomic(card_path, "")            # genuinely no README -> empty card (minimal doc)
        else:
            resp.raise_for_status()                 # 401/403/5xx: do NOT cache as "no card"; log and move on
            _write_atomic(card_path, resp.text)
    return True


def log_failure(model_id: str, error: Exception) -> None:
    """Record a model we couldn't fetch so a resumed run doesn't hide it (see failed.jsonl)."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    with open(RAW_DIR / "failed.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"model_id": model_id, "error": f"{type(error).__name__}: {error}"}) + "\n")


CANONICAL_PATH = RAW_DIR / "_canonical_ids.json"
_HUB_ID = re.compile(r"^[\w.\-]+(/[\w.\-]+)?$")


def base_models_in_raw() -> set[str]:
    """Every distinct `base_model` declared by a cached model (first one if a list)."""
    from src.normalize import base_model

    found: set[str] = set()
    for path in RAW_DIR.glob("*.json"):
        if path.name.startswith("_"):
            continue
        base = base_model((json.loads(path.read_text(encoding="utf-8")).get("cardData") or {}))
        if base:
            found.add(base)
    return found


def canonicalize(ids: set[str], cache_path: Path | None = None) -> dict[str, str]:
    """Map each id to the Hub's current canonical id (e.g. legacy `xlm-roberta-base` ->
    `FacebookAI/xlm-roberta-base`) so lineage counts merge. Uses the `id` the Hub API
    returns for the repo; ids that don't look like Hub ids, or fail to resolve, map to
    themselves. Cached, resumable. ASSUMPTION to verify on one real model in WP1: that
    the API returns the current id for a legacy/redirected one.
    """
    cache_path = cache_path or CANONICAL_PATH
    cache: dict[str, str] = (json.loads(cache_path.read_text(encoding="utf-8"))
                             if cache_path.exists() else {})
    for base in sorted(ids - cache.keys()):
        if not _HUB_ID.match(base):  # a local path, URL or other non-Hub reference
            cache[base] = base
            continue
        try:
            resp = _get(f"{HUB}/api/models/{base}")
        except requests.RequestException:
            continue  # not cached on purpose: a rerun retries it
        cache[base] = (resp.json().get("id") or base) if resp.status_code == 200 else base
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    _write_atomic(cache_path, json.dumps(cache, indent=1, sort_keys=True, ensure_ascii=False))
    return cache


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
        from concurrent.futures import ThreadPoolExecutor, as_completed

        fetched = done = 0
        ids = sorted(all_ids)
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            futures = {pool.submit(fetch_raw, model_id): model_id for model_id in ids}
            for fut in as_completed(futures):
                try:
                    fetched += fut.result()
                except requests.RequestException as e:  # deleted, private or erroring: skip, don't loop forever
                    log_failure(futures[fut], e)
                done += 1
                if done % 250 == 0:
                    print(f"  {done}/{len(ids)} ({fetched} new)", flush=True)
        mapping = canonicalize(base_models_in_raw())
        merged = sum(1 for k, v in mapping.items() if k != v)
        print(f"base models: {len(mapping)} distinct, {merged} resolved to a different canonical id")


if __name__ == "__main__":
    main(sys.argv[1:])
