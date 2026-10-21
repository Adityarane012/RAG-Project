"""Model-card cleaning and the metadata fallback chunk (D20)."""

from __future__ import annotations

import re

from src.config import CFG

_FRONT_MATTER = re.compile(r"\A---\s*\n.*?\n---\s*\n", re.DOTALL)
_CODE_BLOCK = re.compile(r"```.*?```|~~~.*?~~~", re.DOTALL)
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_HTML_TAG = re.compile(r"</?[a-zA-Z][^>]*>")
_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")  # also catches badges: [![..](img)](link)
_BADGE_LINK = re.compile(r"\[\s*\]\([^)]*\)")  # link left empty after its image is removed
_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")  # keep the link text, drop the URL
_TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")
_PLACEHOLDER = re.compile(r"more information (needed|required)|add (a )?description", re.I)


def _drop_long_tables(text: str, max_rows: int) -> str:
    """Keep tables only if short (D20): drop any run of table rows longer than max_rows."""
    out: list[str] = []
    run: list[str] = []

    def flush() -> None:
        if len(run) <= max_rows:
            out.extend(run)
        run.clear()

    for line in text.split("\n"):
        if _TABLE_ROW.match(line):
            run.append(line)
        else:
            flush()
            out.append(line)
    flush()
    return "\n".join(out)


def clean_card(markdown: str) -> str:
    """Strip front matter, badges/images, HTML and code blocks; keep short tables."""
    text = _FRONT_MATTER.sub("", markdown or "")
    text = _CODE_BLOCK.sub("", text)
    text = _HTML_COMMENT.sub("", text)
    text = _IMAGE.sub("", text)
    text = _BADGE_LINK.sub("", text)
    text = _LINK.sub(r"\1", text)
    text = _HTML_TAG.sub("", text)
    text = _drop_long_tables(text, CFG["cleaning"]["max_table_rows"])
    text = re.sub(r"[ \t]+\n", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def doc_quality(cleaned: str) -> str:
    """"minimal" for empty or auto-generated cards, else "full" (D20).

    Placeholder phrases are stripped first, so a card that is mostly boilerplate
    around a few real words still counts as minimal.
    """
    body = _PLACEHOLDER.sub("", cleaned)
    body = re.sub(r"^#+\s.*$", "", body, flags=re.M)  # headings alone are not content
    return "full" if len(body.strip()) >= CFG["cleaning"]["min_card_chars"] else "minimal"


def fallback_chunk(meta: dict, tags: list[str] | None = None) -> str:
    """One chunk built from metadata, for cards with nothing worth embedding (D20)."""
    parts = [f"Model: {meta['model_id']}"]
    if meta.get("task"):
        parts.append(f"Task: {meta['task']}")
    if meta.get("languages"):
        parts.append(f"Languages: {', '.join(meta['languages'])}")
    if meta.get("base_model"):
        parts.append(f"Fine-tuned from: {meta['base_model']}")
    if tags:
        parts.append(f"Tags: {', '.join(tags)}")
    return "\n".join(parts)
