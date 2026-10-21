"""Guards the committed evaluation set. It was written before any retrieval experiment (gate G1),
so these checks exist to stop it drifting afterwards: a changed query must be a visible, reviewed edit."""
import collections
from pathlib import Path

from eval.metrics import load_queries

PATH = Path(__file__).resolve().parent.parent / "eval" / "queries.jsonl"


def test_set_is_valid_unique_and_has_the_planned_mix():
    qs = load_queries(PATH)
    assert len({q["id"] for q in qs}) == len(qs) == 100
    assert len({q["query"] for q in qs}) == len(qs)
    kinds = collections.Counter(q["kind"] for q in qs)
    assert kinds == {"normal": 75, "vague": 15, "impossible": 10}
    assert {q["source"] for q in qs} == {"author"}          # single author: disclosed deviation from D11


def test_normal_queries_cover_every_task_and_every_indic_language_and_non_english_phrasing():
    text = " ".join(q["query"].lower() for q in load_queries(PATH) if q["kind"] == "normal")
    for lang in ("hindi", "marathi", "bengali", "tamil", "telugu", "gujarati", "kannada", "malayalam", "punjabi", "urdu"):
        assert lang in text, lang
    for word in ("speech", "translat", "sentiment", "ner", "embedding"):
        assert word in text, word
    assert any("ऀ" <= c <= "ॿ" for c in text)      # Devanagari-script queries
