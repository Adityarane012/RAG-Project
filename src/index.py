"""Chunk cards by section, embed locally, upsert to Pinecone (D4, D8, D10, D20, D21).

Invariants: queries and documents use the same embedding model (changing it means
re-indexing everything), and metadata is identical on every chunk of a model.
"""

from __future__ import annotations

import re

from src.clean import clean_card, doc_quality, fallback_chunk
from src.config import CFG
from src.normalize import normalize_record
from src.tokens import approx_tokens  # noqa: F401  (re-exported: tests and callers import it from here)

EMBED_MODEL = CFG["embedding"]["model"]
EMBED_DIM = CFG["embedding"]["dim"]
MAX_SECTION_TOKENS = CFG["embedding"]["max_section_tokens"]  # model limit is ~507

# e5 models expect these prefixes on their inputs.
PASSAGE_PREFIX = "passage: "
QUERY_PREFIX = "query: "

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$", re.M)


def load_embedder():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBED_MODEL)


def embed_passages(model, texts: list[str]) -> list[list[float]]:
    return model.encode([PASSAGE_PREFIX + t for t in texts], normalize_embeddings=True).tolist()


def embed_query(model, text: str) -> list[float]:
    return model.encode(QUERY_PREFIX + text, normalize_embeddings=True).tolist()


def _split_long(text: str, max_tokens: int) -> list[str]:
    """Split on paragraph boundaries, then on words, so every piece fits."""
    pieces: list[str] = []
    current: list[str] = []
    for para in re.split(r"\n\s*\n", text):
        for part in ([para] if approx_tokens(para) <= max_tokens else _split_words(para, max_tokens)):
            if current and approx_tokens("\n\n".join(current + [part])) > max_tokens:
                pieces.append("\n\n".join(current))
                current = []
            current.append(part)
    if current:
        pieces.append("\n\n".join(current))
    return pieces


def _split_words(text: str, max_tokens: int) -> list[str]:
    words = text.split()
    step = max(1, int(max_tokens / 1.5) - 1)
    return [" ".join(words[i:i + step]) for i in range(0, len(words), step)]


def chunk_card(cleaned: str, max_tokens: int = MAX_SECTION_TOKENS) -> list[tuple[str, str]]:
    """Split a cleaned card into (section, text) chunks of <= max_tokens, by heading."""
    sections: list[tuple[str, str]] = []
    heading, start = "overview", 0
    for m in _HEADING.finditer(cleaned):
        sections.append((heading, cleaned[start:m.start()]))
        heading, start = m.group(2).strip().lower() or "section", m.end()
    sections.append((heading, cleaned[start:]))

    chunks: list[tuple[str, str]] = []
    for name, body in sections:
        body = body.strip()
        if not body:
            continue
        for part in _split_long(body, max_tokens):
            chunks.append((name, part))
    return chunks


def build_vectors(raw: dict, card_markdown: str, embed) -> list[dict]:
    """All Pinecone vectors for one model. `embed(texts) -> list of vectors`.

    Cards with no real content get one metadata fallback chunk and
    `doc_quality: minimal` (D20). Every chunk carries the same model metadata plus
    its own `section` and `text` (`text` is for the explanation step, D17).
    """
    meta = normalize_record(raw)
    cleaned = clean_card(card_markdown)
    meta["doc_quality"] = doc_quality(cleaned)
    chunks = chunk_card(cleaned) if meta["doc_quality"] == "full" else []
    if not chunks:
        chunks = [("metadata", fallback_chunk(meta, raw.get("tags")))]
    vectors = embed([text for _, text in chunks])
    return [
        {"id": f"{meta['model_id']}::{i}", "values": vec,
         "metadata": {k: v for k, v in {**meta, "section": section, "text": text}.items()
                      if v is not None}}  # Pinecone rejects null metadata values
        for i, ((section, text), vec) in enumerate(zip(chunks, vectors))
    ]


def upsert(index, vectors: list[dict], namespace: str, batch: int = 100) -> None:
    for i in range(0, len(vectors), batch):
        index.upsert(vectors=vectors[i:i + batch], namespace=namespace)


def main() -> None:
    # TODO (after ingest has run): iterate data/raw via ingest.load_raw, embed with
    # load_embedder(), upsert into CFG["pinecone"]["namespace"] (or exp-<name>),
    # and write the normalized records to data/snapshot-<date>/.
    raise NotImplementedError


if __name__ == "__main__":
    main()
