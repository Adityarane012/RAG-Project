"""Assemble the real pipeline (index + embedder + reranker + LLM) for the graph and its D19 variants.

`graph.build_graph` takes injected dependencies so it can be tested without a network; this module is where
the real ones are chosen, from config.yaml and the environment: vector store (local or Pinecone), embedding
backend, reranker, LLM provider.
"""

from __future__ import annotations

from functools import lru_cache

from src import llm
from src.baselines import KeywordIndex
from src.config import CFG
from src.embedder import load_embedder
from src.graph import Deps, build_graph
from src.index import open_index, prepare_all
from src.rerank import load_reranker
from src.retrieve import pinecone_fetch


@lru_cache(maxsize=1)
def lineage_index() -> dict:
    """base_model -> models declaring it, from the cached corpus (D14 lineage, in-snapshot counts)."""
    from src.adapt import build_lineage_index
    from src.snapshot import collect_records

    return build_lineage_index(collect_records())


def vector_fetch(index, embedder, namespace: str):
    """`fetch(text, filter, k)`: embed the query text, then filtered nearest-neighbour search."""
    def fetch(text: str, flt: dict, k: int) -> list[dict]:
        return pinecone_fetch(index, embedder.query(text), namespace)(flt, k)
    return fetch


def build_pipeline(variant: str = "ours", namespace: str | None = None, explain: bool = True, index=None,
                   embedder=None, reranker=None, keyword: KeywordIndex | None = None, extract=None):
    """A compiled graph for `variant` ("ours" | "naive" | "keyword"). Every argument can be injected for tests;
    `extract` lets the evaluation feed every system the same pre-computed constraints."""
    ns = namespace or CFG["pinecone"]["namespace"]
    if variant == "keyword":
        keyword = keyword or KeywordIndex(prepare_all())
        fetch = keyword.fetch
    else:
        fetch = vector_fetch(index or open_index(ns), embedder or load_embedder(), ns)
    deps = Deps(
        extract=extract or llm.extract_constraints,
        fetch=fetch,
        rerank=reranker or load_reranker(),
        explain=llm.explain if (explain and variant == "ours") else None,
        lineage_index=lineage_index() if variant == "ours" else {},
    )
    return build_graph(deps, variant=variant)
