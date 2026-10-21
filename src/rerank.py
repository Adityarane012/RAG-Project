"""Local cross-encoder reranker (D9): `BAAI/bge-reranker-v2-m3`, the safe default.

Contract with graph.Deps.rerank: return the same match dicts with `score` REPLACED by the
reranker's score, best first. `retrieve.group_by_model` ranks by `score`, so keeping the
vector-similarity score here would silently disable reranking.
"""

from __future__ import annotations

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
