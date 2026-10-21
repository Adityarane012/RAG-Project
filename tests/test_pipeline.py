"""build_pipeline wires real components in production; here every component is injected, so this checks the
wiring (which text is embedded, which namespace is queried, that variants use the right pieces) offline."""
from src import pipeline
from src.baselines import KeywordIndex
from src.localindex import LocalIndex

CONS = {"task": "text-classification", "langs": ["hi"], "direction": None, "max_size_mb": 500, "size_word": None,
        "commercial": True, "modifiable": None, "soft_query": "hindi sentiment"}


def meta(model_id, **k):
    return {"model_id": model_id, "task": "text-classification", "languages": ["hi"], "language_status": "known", "multilingual": False,
            "size_status": "known", "size_mb": 100.0, "commercial": "yes", "modifiable": "yes", "section": "s", "text": f"{model_id} text", **k}


class Emb:
    def __init__(self):
        self.queries = []

    def query(self, text):
        self.queries.append(text)
        return [1.0, 0.0]


def index_with(models):
    idx = LocalIndex()
    idx.upsert([{"id": f"{m}::0", "values": v, "metadata": meta(m, **k)} for m, v, k in models], namespace="ns")
    return idx


def test_ours_embeds_the_users_query_filters_reranks_and_verifies():
    idx = index_with([("good/m", [1, 0], {}), ("big/m", [0.9, 0.1], {"size_mb": 9000.0}), ("nc/m", [0.8, 0.2], {"commercial": "no"})])
    emb, seen = Emb(), {}

    def rerank(q, ms):
        seen["q"], seen["n"] = q, len(ms)
        return ms

    g = pipeline.build_pipeline("ours", namespace="ns", index=idx, embedder=emb, reranker=rerank, extract=lambda q: dict(CONS))
    s = g.invoke({"query": "a long original request"})
    assert emb.queries == ["a long original request"] and seen["q"] == "a long original request"
    assert [r["model_id"] for r in s["results"]] == ["good/m"] and seen["n"] == 1        # filtered BEFORE reranking
    assert s["outcome"] == "answer" and "fully_verified" in s


def test_naive_searches_everything_and_returns_violators_in_vector_order():
    idx = index_with([("good/m", [0.5, 0.5], {}), ("big/m", [1.0, 0.0], {"size_mb": 9000.0}), ("nc/m", [0.9, 0.1], {"commercial": "no"})])
    g = pipeline.build_pipeline("naive", namespace="ns", index=idx, embedder=Emb(), reranker=lambda q, m: m, extract=lambda q: dict(CONS))
    s = g.invoke({"query": "q"})
    assert [r["model_id"] for r in s["results"]] == ["big/m", "nc/m", "good/m"]
    assert [r["overall"] for r in s["results"]] == ["fail", "fail", "pass"] and "explanations" not in s


def test_keyword_uses_bm25_with_the_same_filter_and_no_embedding_or_reranker():
    kw = KeywordIndex([{"id": "a/m::0", "text": "hindi sentiment model", "metadata": meta("a/m")},
                       {"id": "b/m::0", "text": "hindi sentiment model huge", "metadata": meta("b/m", size_mb=9000.0)}])
    emb = Emb()

    def boom(q, m):
        raise AssertionError("keyword must not rerank")

    g = pipeline.build_pipeline("keyword", keyword=kw, embedder=emb, reranker=boom, extract=lambda q: dict(CONS))
    s = g.invoke({"query": "hindi sentiment model"})
    assert [r["model_id"] for r in s["results"]] == ["a/m"] and emb.queries == []
