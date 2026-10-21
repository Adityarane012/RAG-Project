"""Embedding backends and a content-hash cache (D8).

Two backends produce the SAME model's vectors (`intfloat/multilingual-e5-large`, 1024-d):
  * local   : sentence-transformers on this machine (no quota; needs the weights, ~2 GB)
  * pinecone: Pinecone's hosted copy of the model (no weights; counts against the monthly inference quota)
Queries and passages must use the same model, but the choice of backend is free. Both apply e5's
"passage: " / "query: " convention (locally by prefix, hosted via `input_type`).

Every vector is cached on disk under a hash of (model, kind, text), so rebuilding an index into a fresh
namespace costs no embedding time or quota, and embedding can run before the vector database is reachable.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import numpy as np
import requests

from src.config import CFG

PASSAGE_PREFIX = "passage: "
QUERY_PREFIX = "query: "
PINECONE_API = "https://api.pinecone.io"
API_VERSION = "2024-07"


class QuotaExceeded(RuntimeError):
    """The hosted backend's monthly inference quota is used up."""


def text_key(kind: str, text: str, model: str | None = None) -> str:
    model = model or CFG["embedding"]["model"]
    return hashlib.sha256(f"{model}\n{kind}\n{text}".encode("utf-8")).hexdigest()


class LocalEmbedder:
    name = "local"

    def __init__(self, model=None):
        self._model = model

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(CFG["embedding"]["model"])
        return self._model

    def passages(self, texts: list[str]) -> list[list[float]]:
        return self._load().encode([PASSAGE_PREFIX + t for t in texts], normalize_embeddings=True,
                                   batch_size=32).tolist()

    def query(self, text: str) -> list[float]:
        return self._load().encode(QUERY_PREFIX + text, normalize_embeddings=True).tolist()


class HostedEmbedder:
    """Pinecone's hosted multilingual-e5-large via `POST /embed` on the control-plane host."""

    name = "pinecone"

    def __init__(self, api_key: str | None = None, batch: int | None = None, post=None, sleep=time.sleep):
        self._key = api_key or os.environ.get("PINECONE_API_KEY", "")
        self._batch = batch or CFG["embedding"]["hosted_batch"]
        self._post, self._sleep = post or requests.post, sleep
        self.tokens_used = 0

    def _embed(self, texts: list[str], input_type: str) -> list[list[float]]:
        body = {"model": "multilingual-e5-large", "parameters": {"input_type": input_type, "truncate": "END"},
                "inputs": [{"text": t} for t in texts]}
        headers = {"Api-Key": self._key, "X-Pinecone-API-Version": API_VERSION, "Content-Type": "application/json"}
        for attempt in range(6):
            r = self._post(f"{PINECONE_API}/embed", json=body, headers=headers, timeout=120)
            if r.status_code == 429 or r.status_code >= 500:
                text = r.text.lower()
                if "quota" in text or "limit exceeded" in text or "monthly" in text:
                    raise QuotaExceeded(r.text[:300])
                self._sleep(min(2 ** attempt, 30))
                continue
            if r.status_code >= 400:
                raise RuntimeError(f"hosted embedding failed: HTTP {r.status_code}: {r.text[:300]}")
            j = r.json()
            self.tokens_used += int((j.get("usage") or {}).get("total_tokens", 0))
            return [d["values"] for d in j["data"]]
        raise RuntimeError("hosted embedding: rate limited after 6 attempts")

    def passages(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), self._batch):
            out += self._embed(texts[i:i + self._batch], "passage")
        return out

    def query(self, text: str) -> list[float]:
        return self._embed([text], "query")[0]


class CachedEmbedder:
    """Wraps a backend with the on-disk cache. `passages` embeds only the texts it has not seen."""

    def __init__(self, backend, cache_dir: str | Path | None = None, shard_size: int = 1000):
        self.backend, self.shard_size = backend, shard_size
        self.dir = Path(cache_dir or CFG["embedding"]["cache_dir"])
        self._mem: dict[str, np.ndarray] = {}
        self._loaded = False
        self.hits = self.misses = 0
        self._logged = getattr(backend, "tokens_used", 0) or 0     # only tokens charged from now on are ours to log

    def _load(self) -> None:
        if self._loaded:
            return
        for f in sorted(self.dir.glob("emb-*.npz")) if self.dir.exists() else []:
            with np.load(f, allow_pickle=False) as z:
                for h, v in zip(z["hashes"].tolist(), z["vectors"]):
                    self._mem[h] = v
        self._loaded = True

    def _save_shard(self, hashes: list[str], vecs: list[list[float]]) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        tag = hashlib.sha256("".join(hashes).encode()).hexdigest()[:12]
        tmp = self.dir / f"emb-{tag}.tmp.npz"
        np.savez(tmp, hashes=np.array(hashes), vectors=np.asarray(vecs, dtype=np.float32))
        tmp.replace(self.dir / f"emb-{tag}.npz")

    def _log_usage(self, chunks: int) -> None:
        """Append what the hosted backend charged for this shard, so the monthly quota can be tracked."""
        used = getattr(self.backend, "tokens_used", None)
        if used is None:
            return
        delta, self._logged = used - self._logged, used
        with open(self.dir / "usage.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "backend": self.backend.name,
                                "chunks": chunks, "tokens": delta}) + "\n")

    def tokens_total(self) -> int:
        """All hosted-embedding tokens ever logged in this cache directory."""
        p = self.dir / "usage.jsonl"
        return sum(json.loads(line)["tokens"] for line in p.read_text(encoding="utf-8").splitlines()) if p.exists() else 0

    def passages(self, texts: list[str]) -> list[list[float]]:
        self._load()
        keys = [text_key("passage", t) for t in texts]
        missing = [(k, t) for k, t in dict.fromkeys(zip(keys, texts)) if k not in self._mem]
        self.hits += len(texts) - len(missing)
        self.misses += len(missing)
        for i in range(0, len(missing), self.shard_size):         # embed and persist shard by shard (resumable)
            part = missing[i:i + self.shard_size]
            vecs = self.backend.passages([t for _, t in part])
            for (k, _), v in zip(part, vecs):
                self._mem[k] = np.asarray(v, dtype=np.float32)
            self._save_shard([k for k, _ in part], vecs)
            self._log_usage(len(part))
        return [self._mem[k].tolist() for k in keys]

    def query(self, text: str) -> list[float]:
        """Query vectors are cached too (same store, kind "query"): re-running an evaluation re-embeds nothing."""
        self._load()
        key = text_key("query", text)
        if key not in self._mem:
            vec = self.backend.query(text)
            self._mem[key] = np.asarray(vec, dtype=np.float32)
            self._save_shard([key], [vec])
            self._log_usage(1)
        return self._mem[key].tolist()


def load_embedder(backend: str | None = None, cached: bool = True):
    """The configured embedder (config `embedding.backend`, env EMBED_BACKEND overrides)."""
    name = (backend or os.getenv("EMBED_BACKEND") or CFG["embedding"]["backend"]).lower()
    if name not in ("local", "pinecone"):
        raise ValueError(f"embedding backend must be 'local' or 'pinecone', got {name!r}")
    inner = LocalEmbedder() if name == "local" else HostedEmbedder()
    return CachedEmbedder(inner) if cached else inner
