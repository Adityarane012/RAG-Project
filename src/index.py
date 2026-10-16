"""Chunk cards by section, embed locally, upsert to Pinecone (D4, D8, D10).

Invariant: queries and documents use the same embedding model. Changing it
means re-indexing everything.
"""

from __future__ import annotations

EMBED_MODEL = "intfloat/multilingual-e5-large"
EMBED_DIM = 1024
MAX_SECTION_TOKENS = 450  # model limit is ~507 tokens

# e5 models expect these prefixes on inputs.
PASSAGE_PREFIX = "passage: "
QUERY_PREFIX = "query: "


def load_embedder():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBED_MODEL)


def embed_passages(model, texts: list[str]) -> list[list[float]]:
    return model.encode([PASSAGE_PREFIX + t for t in texts], normalize_embeddings=True).tolist()


def embed_query(model, text: str) -> list[float]:
    return model.encode(QUERY_PREFIX + text, normalize_embeddings=True).tolist()


def chunk_card(card_markdown: str) -> list[tuple[str, str]]:
    """Split a model card into (section_heading, text) chunks of <= MAX_SECTION_TOKENS."""
    # TODO: split on markdown headings, then split long sections further.
    raise NotImplementedError


def main() -> None:
    # TODO: read normalized records from data/, chunk, embed, upsert with
    # metadata from normalize.to_metadata().
    raise NotImplementedError


if __name__ == "__main__":
    main()
