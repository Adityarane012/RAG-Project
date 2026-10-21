"""Chunk cards by section, embed locally, upsert to Pinecone (D4, D8, D10, D20, D21).

Invariants: queries and documents use the same embedding model (changing it means
re-indexing everything), and metadata is identical on every chunk of a model.
"""

from __future__ import annotations

import re
from pathlib import Path

from src.clean import clean_card, doc_quality, fallback_chunk
from src.config import CFG
from src.normalize import normalize_record
from src.tokens import approx_tokens  # noqa: F401  (re-exported: tests and callers import it from here)

EMBED_MODEL = CFG["embedding"]["model"]
EMBED_DIM = CFG["embedding"]["dim"]
MAX_SECTION_TOKENS = CFG["embedding"]["max_section_tokens"]  # model limit is ~507
MAX_CHUNKS = CFG["embedding"]["max_chunks_per_model"]
DROP_SECTIONS = tuple(x.lower() for x in CFG["embedding"]["drop_sections"])

# e5 prefixes and the embedding backends live in src/embedder.py
from src.embedder import PASSAGE_PREFIX, QUERY_PREFIX  # noqa: F401,E402

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$", re.M)


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


_PLACEHOLDER_ONLY = re.compile(r"more information (needed|required)|add (a )?description|todo|n/?a|none", re.I)


def select_chunks(chunks: list[tuple[str, str]], max_n: int | None = None,
                  drop: tuple[str, ...] | None = None) -> list[tuple[str, str]]:
    """Keep the informative chunks, in document order, at most `max_n`.

    Drops chunks whose heading names a boilerplate section (config `embedding.drop_sections`) and chunks
    with no real content (empty or placeholder-only). Measured on 2,800 real cards, uncapped chunking gives
    ~8.7 chunks per model; most of the extra is boilerplate, so this keeps cost and noise down without
    losing the description, usage, limitations or data sections. Returns [] if nothing survives; the
    caller then uses the metadata fallback chunk.
    """
    max_n = MAX_CHUNKS if max_n is None else max_n
    drop = DROP_SECTIONS if drop is None else drop
    kept = []
    for section, text in chunks:
        if any(d in section.lower() for d in drop):
            continue
        if len(_PLACEHOLDER_ONLY.sub("", text).strip(" \n.-*#|:")) < 30:
            continue
        kept.append((section, text))
    return kept[:max_n]


def prepare_model(raw: dict, card_markdown: str, canonical: dict[str, str] | None = None) -> list[dict]:
    """All chunks of one model WITHOUT vectors: [{"id", "text", "metadata"}].

    Cards with no real content get one metadata fallback chunk and `doc_quality: minimal` (D20). Every chunk
    carries the same model metadata plus its own `section` and `text` (`text` is for the explanation step,
    D17). `None` values are dropped because Pinecone rejects null metadata.
    """
    meta = normalize_record(raw, canonical)
    cleaned = clean_card(card_markdown)
    meta["doc_quality"] = doc_quality(cleaned)
    chunks = select_chunks(chunk_card(cleaned)) if meta["doc_quality"] == "full" else []
    if not chunks:
        chunks = [("metadata", fallback_chunk(meta, raw.get("tags")))]
    return [
        {"id": f"{meta['model_id']}::{i}", "text": text,
         "metadata": {k: v for k, v in {**meta, "section": section, "text": text}.items() if v is not None}}
        for i, (section, text) in enumerate(chunks)
    ]


def build_vectors(raw: dict, card_markdown: str, embed, canonical: dict[str, str] | None = None) -> list[dict]:
    """All Pinecone vectors for one model. `embed(texts) -> list of vectors`."""
    prepared = prepare_model(raw, card_markdown, canonical)
    vectors = embed([p["text"] for p in prepared])
    return [{"id": p["id"], "values": vec, "metadata": p["metadata"]} for p, vec in zip(prepared, vectors)]


def upsert(index, vectors: list[dict], namespace: str, batch: int = 100) -> None:
    for i in range(0, len(vectors), batch):
        index.upsert(vectors=vectors[i:i + batch], namespace=namespace)


def progress_path(namespace: str) -> Path:
    return Path("data/index_progress") / f"{namespace}.txt"


def done_models(namespace: str) -> set[str]:
    p = progress_path(namespace)
    return set(p.read_text(encoding="utf-8").split("\n")) - {""} if p.exists() else set()


def prepare_all(raw_dir: Path | None = None, limit: int | None = None) -> list[dict]:
    """Prepared chunks for every cached model, in a stable order."""
    import json

    from src import ingest

    raw_dir = raw_dir or ingest.RAW_DIR
    cpath = raw_dir / "_canonical_ids.json"
    canonical = json.loads(cpath.read_text(encoding="utf-8")) if cpath.exists() else None
    out: list[dict] = []
    paths = sorted(p for p in raw_dir.glob("*.json") if not p.name.startswith("_") and p.with_suffix(".md").exists())
    for p in paths[:limit]:
        raw = json.loads(p.read_text(encoding="utf-8"))
        out += prepare_model(raw, p.with_suffix(".md").read_text(encoding="utf-8"), canonical)
    return out


def run_build(chunks: list[dict], embedder, namespace: str, index=None, embed_batch: int = 1000,
              upsert_batch: int = 100, log=print, resume: bool = True) -> dict:
    """Embed (through the cache) and, if an index is given, upsert resumably into `namespace`.

    Resumable: models whose chunks were all upserted are recorded in data/index_progress/<namespace>.txt
    and skipped. With `index=None` this only fills the embedding cache (the stage that needs neither
    the vector database nor a fresh namespace).
    """
    done = done_models(namespace) if (index is not None and resume) else set()
    todo = [c for c in chunks if c["metadata"]["model_id"] not in done]
    stats = {"chunks": len(chunks), "skipped_done": len(chunks) - len(todo), "embedded": 0, "upserted": 0}
    for i in range(0, len(todo), embed_batch):
        part = todo[i:i + embed_batch]
        vecs = embedder.passages([c["text"] for c in part])
        stats["embedded"] += len(part)
        if index is not None:
            for j in range(0, len(part), upsert_batch):
                sub = part[j:j + upsert_batch]
                index.upsert(vectors=[{"id": c["id"], "values": v, "metadata": c["metadata"]}
                                      for c, v in zip(sub, vecs[j:j + upsert_batch])], namespace=namespace)
                stats["upserted"] += len(sub)
            # A model is "done" only once ALL its chunks are in. Chunks of one model are adjacent, so in every
            # batch except the last, the model of the final chunk may continue into the next batch: not done yet.
            ids = {c["metadata"]["model_id"] for c in part}
            finished = ids if i + embed_batch >= len(todo) else ids - {part[-1]["metadata"]["model_id"]}
            if resume:                                  # a local index is rebuilt from the cache each time: nothing to resume
                p = progress_path(namespace)
                p.parent.mkdir(parents=True, exist_ok=True)
                with open(p, "a", encoding="utf-8") as f:
                    f.write("".join(m + "\n" for m in sorted(finished)))
        log(f"  {min(i + embed_batch, len(todo))}/{len(todo)} chunks embedded"
            + (f", {stats['upserted']} upserted" if index is not None else ""))
    return stats


def store_backend() -> str:
    import os

    name = (os.getenv("INDEX_BACKEND") or CFG["vector_store"]["backend"]).lower()
    if name not in ("local", "pinecone"):
        raise ValueError(f"vector store backend must be 'local' or 'pinecone', got {name!r}")
    return name


def open_index(namespace: str):
    """The index retrieval reads from: a saved LocalIndex, or the Pinecone index (same `.query` interface)."""
    if store_backend() == "local":
        from src.localindex import LocalIndex

        return LocalIndex.load(CFG["vector_store"]["local_dir"], namespace)
    return connect()


def connect(create_if_missing: bool = False):
    """The Pinecone index named in config (needs the SDK and the data-plane host to be reachable)."""
    import os

    from pinecone import Pinecone, ServerlessSpec

    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    name = CFG["pinecone"]["index"]
    names = [i["name"] for i in pc.list_indexes()]
    if name not in names:
        if not create_if_missing:
            raise RuntimeError(f"Pinecone index {name!r} does not exist; run with --create")
        pc.create_index(name=name, dimension=EMBED_DIM, metric="cosine",
                        spec=ServerlessSpec(cloud="aws", region="us-east-1"))
    return pc.Index(host=pc.describe_index(name).host)


def main(argv: list[str] | None = None) -> None:
    import argparse

    from src.embedder import load_embedder

    ap = argparse.ArgumentParser(description="Embed all cached cards and upsert them into a Pinecone namespace.")
    ap.add_argument("--namespace", required=True, help="exp-<name> for experiments; prod only deliberately (D21)")
    ap.add_argument("--backend", choices=["local", "pinecone"], help="embedding backend (default: config)")
    ap.add_argument("--limit", type=int, help="only the first N cached models (smoke test)")
    ap.add_argument("--store", choices=["local", "pinecone"], help="where to write (default: config vector_store.backend)")
    ap.add_argument("--embed-only", action="store_true", help="fill the embedding cache; do not touch any index")
    ap.add_argument("--create", action="store_true", help="create the index if it does not exist")
    args = ap.parse_args(argv)

    chunks = prepare_all(limit=args.limit)
    models = len({c["metadata"]["model_id"] for c in chunks})
    print(f"{models} models -> {len(chunks)} chunks (namespace {args.namespace!r})")
    embedder = load_embedder(args.backend)
    store = args.store or store_backend()
    if args.embed_only:
        index = None
    elif store == "local":
        from src.localindex import LocalIndex

        index = LocalIndex()
    else:
        index = connect(create_if_missing=args.create)
    stats = run_build(chunks, embedder, args.namespace, index, resume=(store == "pinecone"))
    if not args.embed_only and store == "local":
        path = index.save(CFG["vector_store"]["local_dir"], args.namespace)
        print(f"saved local index: {path} ({index.count(args.namespace)} vectors)")
    print(stats, "| cache hits/misses:", embedder.hits, "/", embedder.misses)
    if hasattr(embedder, "tokens_total"):
        print(f"hosted embedding tokens charged so far (all runs, from {embedder.dir}/usage.jsonl): {embedder.tokens_total():,}")


if __name__ == "__main__":
    main()
