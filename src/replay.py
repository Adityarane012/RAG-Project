"""Record and replay graph runs (D21).

Retrieval needs Pinecone and query embedding, so only the LLM can be cached for real
offline use. For the demo we record each planned query's final graph state once, with
live services, and replay it later. `REPLAY=1` serves recordings and never touches the
network; `RECORD=1` runs live and saves each result.

The key covers everything that determines a run: the query, the user's overrides and the
carried loop counters, so a clarify -> answer -> relax sequence replays step by step.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from src.config import CFG

CARRIED = ("clarifications_asked", "relax_count")


class MissingRecording(KeyError):
    """No recording for this input. Record it live first (RECORD=1)."""


def replay_dir() -> Path:
    return Path(os.getenv("REPLAY_DIR") or CFG["replay"]["dir"])


def run_key(graph_input: dict, variant: str = "ours") -> str:
    canonical = {"query": (graph_input.get("query") or "").strip(),
                 "overrides": graph_input.get("overrides") or {},
                 **{k: graph_input.get(k, 0) for k in CARRIED}}
    if variant != "ours":                      # the side-by-side view records the baseline separately
        canonical["variant"] = variant
    blob = json.dumps(canonical, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


class ReplayGraph:
    """Drop-in for a compiled graph: same `.invoke(input) -> state`.

    mode "replay": serve recordings only; "record": call `graph` and save; "live": passthrough.
    """

    def __init__(self, graph=None, mode: str = "live", directory: Path | None = None, variant: str = "ours"):
        if mode not in ("live", "record", "replay"):
            raise ValueError(f"unknown mode {mode!r}")
        if mode != "replay" and graph is None:
            raise ValueError(f"mode {mode!r} needs a graph")
        self.graph, self.mode, self.directory, self.variant = graph, mode, directory, variant

    @property
    def _dir(self) -> Path:
        return self.directory or replay_dir()

    def invoke(self, graph_input: dict) -> dict:
        if self.mode == "live":
            return self.graph.invoke(graph_input)
        path = self._dir / f"{run_key(graph_input, self.variant)}.json"
        if self.mode == "replay":
            if not path.exists():
                raise MissingRecording(
                    f"No recording for query {graph_input.get('query')!r}. "
                    "Run it once with RECORD=1 and live services.")
            return json.loads(path.read_text(encoding="utf-8"))["state"]
        state = self.graph.invoke(graph_input)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"input": graph_input, "state": state}, ensure_ascii=False,
                                  indent=1, default=str), encoding="utf-8")
        tmp.replace(path)
        return state


def mode_from_env() -> str:
    if os.getenv("REPLAY") == "1":
        return "replay"
    if os.getenv("RECORD") == "1":
        return "record"
    return "live"
