"""Baselines that are not graph variants (D19): BM25 keyword search and the Hub's own filters."""

from __future__ import annotations

import json
import math
import re
import string
from collections import Counter, defaultdict
from pathlib import Path

from src.localindex import matches_filter
from src.normalize import normalize_record

_STRIP = string.punctuation + "।॥…“”‘’"


def tokenize(text: str) -> list[str]:
    """Lower-case whitespace tokens with punctuation stripped. Whitespace (not \\w) so Devanagari words are not
    split at their vowel signs."""
    return [t for t in (w.strip(_STRIP).lower() for w in text.split()) if len(t) > 1]


class KeywordIndex:
    """Okapi BM25 over card chunks, with the same metadata filters as the vector index (D19: "BM25 with the
    same filters"). `fetch(text, flt, k)` has the same shape and output as the vector retrievers."""

    def __init__(self, chunks: list[dict], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.docs = chunks                              # [{"id", "text", "metadata"}]
        self.post: dict[str, list[tuple[int, int]]] = defaultdict(list)
        self.len = []
        for i, c in enumerate(chunks):
            toks = tokenize(c["text"])
            self.len.append(len(toks))
            for term, tf in Counter(toks).items():
                self.post[term].append((i, tf))
        self.n = len(chunks)
        self.avg = (sum(self.len) / self.n) if self.n else 0.0

    def _idf(self, term: str) -> float:
        df = len(self.post.get(term, ()))
        return math.log(1 + (self.n - df + 0.5) / (df + 0.5))

    def search(self, text: str, flt: dict | None, top_k: int) -> list[dict]:
        scores: dict[int, float] = defaultdict(float)
        for term in set(tokenize(text)):
            idf = self._idf(term)
            for i, tf in self.post.get(term, ()):
                denom = tf + self.k1 * (1 - self.b + self.b * self.len[i] / (self.avg or 1))
                scores[i] += idf * tf * (self.k1 + 1) / denom
        ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))      # ties: insertion order
        out = []
        for i, sc in ranked:
            md = self.docs[i]["metadata"]
            if matches_filter(md, flt):
                out.append({"id": self.docs[i]["id"], "score": sc, "metadata": md})
                if len(out) == top_k:
                    break
        return out

    def fetch(self, text: str, flt: dict, k: int) -> list[dict]:
        return self.search(text, flt or None, k)


# ---- the Hub's own filters ---------------------------------------------------------------------------------------

def hub_candidates(api, constraints: dict, variant: str = "basic", limit: int = 5) -> list[str]:
    """What a user gets from the Hub's own task / language / license filters.

    The Hub's search box matches model *names*, not card text, so a soft preference ("noisy social-media text")
    cannot be expressed; results are the filtered listing ordered by downloads (deterministic; the Hub has no
    size-in-MB filter and no notion of unknowns).
      * basic   : task + language(s). A user who cannot express "commercial" or "modifiable" as a license.
      * licensed: basic + `license:apache-2.0` when commercial or modifiable use is required (a user who picks
                  one well-known permissive license string; the best case for a license-string filter).
    """
    tags = list(constraints.get("langs") or [])
    if variant == "licensed" and (constraints.get("commercial") or constraints.get("modifiable")):
        tags.append("license:apache-2.0")
    kwargs = {"sort": "downloads", "limit": limit}
    if constraints.get("task"):
        kwargs["pipeline_tag"] = constraints["task"]
    if tags:
        kwargs["filter"] = tags
    return [m.id for m in api.list_models(**kwargs)]


def resolve_metadata(model_id: str, dirs: tuple[Path, ...], fetch_dir: Path, fetch=None) -> dict | None:
    """Normalised metadata for a model id: from a cache dir if present, else fetched into `fetch_dir`
    (kept apart from the corpus cache so out-of-corpus models are never indexed). None if unavailable."""
    name = model_id.replace("/", "__")
    for d in (*dirs, fetch_dir):
        p = d / f"{name}.json"
        if p.exists():
            return normalize_record(json.loads(p.read_text(encoding="utf-8")))
    if fetch is None:
        return None
    try:
        fetch(model_id, fetch_dir)
    except Exception:
        return None
    p = fetch_dir / f"{name}.json"
    return normalize_record(json.loads(p.read_text(encoding="utf-8"))) if p.exists() else None
