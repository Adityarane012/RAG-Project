"""Choose and trim the card passages that go into the explanation prompt.

Why: the free Groq tier allows ~8,000 tokens per minute for gpt-oss-20b, and five models x
several full 450-token chunks is far more than that. Instead of keeping 1-2 whole chunks,
keep up to `explain.chunks_per_model` passages per model (best chunk from each distinct
section first) and trim each to its share of `explain.max_prompt_tokens`, keeping the
sentences that overlap the user's request. Selection is deterministic and never reads
verification results (D2): it only decides what the LLM gets to read.
"""

from __future__ import annotations

import re
import string

from src.config import CFG
from src.tokens import approx_tokens

_SENTENCE = re.compile(r"(?<=[.!?।॥])\s+|\n+")        # includes the Devanagari danda
_STRIP = string.punctuation + "।॥…“”‘’"
_STOP = {"a", "an", "the", "for", "of", "in", "on", "and", "or", "to", "with", "is", "are", "i", "my",
         "model", "models", "that", "can", "use", "need", "want"}


def _terms(text: str) -> set[str]:
    # split on whitespace, not \w: Python's \w breaks Devanagari words at the vowel signs
    return {t for t in (w.strip(_STRIP).lower() for w in text.split()) if len(t) > 1 and t not in _STOP}


def _cut(sentence: str, budget: int) -> str:
    words = sentence.split()
    keep = max(1, int((budget - 1) / 1.5))
    return " ".join(words[:keep]) + (" …" if keep < len(words) else "")


def excerpt(text: str, query: str, budget: int) -> str:
    """At most ~`budget` estimated tokens of `text`: the sentences that best match `query`
    (earliest first on ties), in their original order, with [...] marking gaps."""
    if approx_tokens(text) <= budget:
        return text
    sentences = [s.strip() for s in _SENTENCE.split(text) if s.strip()]
    terms = _terms(query)
    order = sorted(range(len(sentences)), key=lambda i: (-len(terms & _terms(sentences[i])), i))
    chosen: list[int] = []
    used = 0
    for i in order:
        cost = approx_tokens(sentences[i])
        if used + cost > budget:
            if not chosen:  # the best sentence alone is too long: cut it, and stop
                sentences[i] = _cut(sentences[i], budget)
                chosen.append(i)
                break
            continue
        chosen.append(i)
        used += cost
    chosen.sort()
    pieces: list[str] = []
    for n, i in enumerate(chosen):
        if n and i != chosen[n - 1] + 1:
            pieces.append("[...]")
        pieces.append(sentences[i])
    if chosen and chosen[-1] != len(sentences) - 1:
        pieces.append("[...]")
    return " ".join(pieces)


def select_evidence(candidates: list[dict], query: str, chunks_per_model: int | None = None,
                    max_prompt_tokens: int | None = None) -> list[dict]:
    """Per candidate, up to `chunks_per_model` passages trimmed to fit one prompt budget.

    `candidates`: [{"model_id", "chunks": [{"score", "metadata": {"section", "text"}}]}].
    Returns [{"model_id", "passages": [{"section", "text"}]}], same order as the input.
    If the budget can't give every passage `min_tokens_per_chunk`, the lowest-ranked
    passages of the model that has the most are dropped first (every model keeps one).
    """
    cfg = CFG["explain"]
    n = chunks_per_model or cfg["chunks_per_model"]
    total = max_prompt_tokens or cfg["max_prompt_tokens"]

    picked: list[list[tuple[str, str]]] = []
    for c in candidates:
        ranked = sorted(c.get("chunks", []), key=lambda m: m.get("score", 0), reverse=True)
        passages: list[tuple[str, str]] = []
        seen_sections: set[str] = set()
        for distinct_only in (True, False):          # first the best chunk of each section, then the rest
            for m in ranked:
                if len(passages) == n:
                    break
                md = m["metadata"]
                item = (md.get("section", ""), md.get("text", ""))
                if not item[1].strip() or item in passages:
                    continue
                if distinct_only and item[0] in seen_sections:
                    continue
                seen_sections.add(item[0])
                passages.append(item)
        picked.append(passages)

    def room(blocks: int) -> int:
        return total - cfg["fixed_overhead_tokens"] - cfg["block_overhead_tokens"] * blocks

    while True:
        blocks = sum(len(p) for p in picked)
        if blocks == 0 or room(blocks) // blocks >= cfg["min_tokens_per_chunk"]:
            break
        fullest = max(range(len(picked)), key=lambda i: len(picked[i]))
        if len(picked[fullest]) <= 1:
            break                                     # one each and still tight: accept it
        picked[fullest].pop()

    # Water-filling: short passages keep their full length; what they don't use goes to long ones.
    needs = sorted(((i, j, min(approx_tokens(t), cfg["max_tokens_per_chunk"]))
                    for i, ps in enumerate(picked) for j, (_, t) in enumerate(ps)), key=lambda x: x[2])
    remaining, left = max(room(len(needs)), len(needs)), len(needs)
    alloc: dict[tuple[int, int], int] = {}
    for i, j, need in needs:
        alloc[(i, j)] = min(need, max(1, remaining // left))
        remaining -= alloc[(i, j)]
        left -= 1

    return [
        {"model_id": c["model_id"],
         "passages": [{"section": sec, "text": excerpt(text, query, alloc[(i, j)])}
                      for j, (sec, text) in enumerate(picked[i])]}
        for i, c in enumerate(candidates)
    ]
