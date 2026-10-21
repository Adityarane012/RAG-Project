"""Local cross-encoder reranker (D9): `BAAI/bge-reranker-v2-m3`, the safe default.

Contract with graph.Deps.rerank: return the same match dicts with `score` REPLACED by the
reranker's score, best first. `retrieve.group_by_model` ranks by `score`, so keeping the
vector-similarity score here would silently disable reranking.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import requests

from src.config import CFG


class LocalReranker:
    def __init__(self, scorer=None, model_name: str | None = None):
        """`scorer(pairs) -> list[float]` is injectable for tests; by default a
        sentence-transformers CrossEncoder is loaded lazily on first use."""
        self._scorer = scorer
        self._model_name = model_name or CFG["retrieval"]["local_reranker_model"]

    def _score(self, pairs: list[tuple[str, str]]) -> list[float]:
        if self._scorer is None:
            from sentence_transformers import CrossEncoder

            self._scorer = CrossEncoder(self._model_name).predict
        return [float(x) for x in self._scorer(pairs)]

    def __call__(self, query: str, matches: list[dict]) -> list[dict]:
        if not matches:
            return []
        scores = self._score([(query, m["metadata"].get("text", "")) for m in matches])
        reranked = [{**m, "score": s, "retrieval_score": m["score"]} for m, s in zip(matches, scores)]
        return sorted(reranked, key=lambda m: m["score"], reverse=True)


class RerankQuotaExceeded(RuntimeError):
    """The hosted reranker's monthly quota is used up."""


class HostedReranker:
    """Pinecone's hosted `bge-reranker-v2-m3` (D9's first option) via `POST /rerank` on the control-plane host.

    Same contract as LocalReranker. Results are cached on disk by (query, document ids and text), so
    re-running an evaluation costs no quota; every real call is appended to `usage.jsonl` (the Starter plan
    allows only a small number of rerank requests per month). At most `max_docs` chunks are sent (the
    best by vector score); the rest keep their retrieval score and sort below the reranked ones.
    """

    API_VERSION = "2024-10"      # the rerank endpoint does not exist in the older version used for embeddings

    def __init__(self, api_key: str | None = None, cache_dir: str | Path | None = None, max_docs: int = 100,
                 post=None, sleep=time.sleep):
        self._key = api_key or os.environ.get("PINECONE_API_KEY", "")
        self.dir = Path(cache_dir or CFG["retrieval"]["rerank_cache_dir"])
        self.max_docs, self._post, self._sleep = max_docs, post or requests.post, sleep
        self.calls = self.cache_hits = 0

    def _cache_path(self, query: str, docs: list[dict]) -> Path:
        h = hashlib.sha256(json.dumps([query, [(d["id"], d["text"]) for d in docs]], ensure_ascii=False).encode()).hexdigest()
        return self.dir / f"{h}.json"

    def _scores(self, query: str, docs: list[dict]) -> list[float]:
        path = self._cache_path(query, docs)
        if path.exists():
            self.cache_hits += 1
            return json.loads(path.read_text(encoding="utf-8"))
        body = {"model": "bge-reranker-v2-m3", "query": query, "documents": docs, "top_n": len(docs), "return_documents": False}
        headers = {"Api-Key": self._key, "X-Pinecone-API-Version": self.API_VERSION, "Content-Type": "application/json"}
        for attempt in range(5):
            r = self._post("https://api.pinecone.io/rerank", json=body, headers=headers, timeout=120)
            if r.status_code == 429 or r.status_code >= 500:
                if any(w in r.text.lower() for w in ("quota", "monthly", "limit exceeded")):
                    raise RerankQuotaExceeded(r.text[:300])
                self._sleep(min(2 ** attempt, 20))
                continue
            if r.status_code >= 400:
                raise RuntimeError(f"hosted rerank failed: HTTP {r.status_code}: {r.text[:300]}")
            j = r.json()
            scores = [0.0] * len(docs)
            for row in j["data"]:
                scores[row["index"]] = float(row["score"])
            self.dir.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(scores), encoding="utf-8")
            self.calls += 1
            with open(self.dir / "usage.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "docs": len(docs),
                                    "rerank_units": (j.get("usage") or {}).get("rerank_units")}) + "\n")
            return scores
        raise RuntimeError("hosted rerank: rate limited after 5 attempts")

    def __call__(self, query: str, matches: list[dict]) -> list[dict]:
        if not matches:
            return []
        head = sorted(matches, key=lambda m: m["score"], reverse=True)[: self.max_docs]
        tail = [m for m in matches if all(m is not h for h in head)]
        docs = [{"id": m["id"], "text": m["metadata"].get("text", "")} for m in head]
        scores = self._scores(query, docs)
        out = sorted(({**m, "score": s, "retrieval_score": m["score"]} for m, s in zip(head, scores)),
                     key=lambda m: m["score"], reverse=True)
        # chunks beyond max_docs were never reranked: they stay below every reranked chunk
        floor = (out[-1]["score"] if out else 0.0) - 1.0
        return out + [{**m, "score": floor, "retrieval_score": m["score"]} for m in tail]

    def units_total(self) -> int:
        p = self.dir / "usage.jsonl"
        return sum((json.loads(l).get("rerank_units") or 0) for l in p.read_text(encoding="utf-8").splitlines()) if p.exists() else 0


def load_reranker(name: str | None = None):
    """`pinecone` (hosted, default per config) or `local` (cross-encoder on this machine), or `none`."""
    name = (name or os.getenv("RERANKER") or CFG["retrieval"]["reranker"]).lower()
    if name == "pinecone":
        return HostedReranker()
    if name == "local":
        return LocalReranker()
    if name == "none":
        return lambda query, matches: matches
    raise ValueError(f"reranker must be 'pinecone', 'local' or 'none', got {name!r}")
