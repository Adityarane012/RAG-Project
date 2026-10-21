from src.clean import clean_card, doc_quality, fallback_chunk

CARD = """---
license: mit
language: hi
---
# My model
[![badge](https://img.shields.io/x.svg)](https://example.com)
<img src="logo.png"> <b>Bold</b> text with a [link](https://example.com).

```python
secret_code()
```

| a | b |
|---|---|
| 1 | 2 |
"""


def test_clean_strips_noise_keeps_text_and_short_tables():
    out = clean_card(CARD)
    assert "license: mit" not in out and "badge" not in out and "<img" not in out
    assert "secret_code" not in out and "https://example.com" not in out
    assert "Bold text with a link." in out
    assert "| 1 | 2 |" in out


def test_long_tables_are_dropped():
    table = "\n".join(f"| {i} | x |" for i in range(30))
    assert "| 5 | x |" not in clean_card("intro\n\n" + table)


def test_doc_quality():
    assert doc_quality(clean_card("# Model\n\nMore information needed")) == "minimal"
    assert doc_quality("") == "minimal"
    assert doc_quality("A fine-tuned model for Marathi named-entity recognition. " * 10) == "full"


def test_fallback_chunk_uses_metadata_only():
    text = fallback_chunk({"model_id": "a/b", "task": "translation", "languages": ["hi"]}, ["tag1"])
    assert "a/b" in text and "translation" in text and "hi" in text and "tag1" in text
