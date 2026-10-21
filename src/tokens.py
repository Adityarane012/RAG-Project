"""One cheap token estimator shared by chunking, throttling and prompt budgeting."""

from __future__ import annotations


def approx_tokens(text: str) -> int:
    """Cheap token estimate (no tokenizer needed): 1.5 x words. Multilingual/Indic text
    splits into more tokens per word than English, so this is deliberately pessimistic for
    English and may under-count Devanagari; check against the real tokenizer (E-IDX-4) and
    keep headroom in every budget that uses it."""
    return int(len(text.split()) * 1.5) + 1
