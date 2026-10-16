"""Turn raw Hub metadata into the D10 schema, marking gaps as unknown (D3, D12).

Metadata written per vector (D10, D12):
    task, languages, language_status, size_mb (only when known), size_status,
    commercial, downloads, section, model_id
"""

from __future__ import annotations

# D3: license id (as it appears in Hub tags / card metadata) -> commercial use.
# Anything not listed maps to "unknown"; never guess.
# "conditional" = commercial use allowed only under extra terms that need a human
# to read them (use-based restrictions, user caps, copyleft obligations).
LICENSE_COMMERCIAL: dict[str, str] = {
    # Permissive
    "apache-2.0": "yes",
    "mit": "yes",
    "bsd": "yes",
    "bsd-2-clause": "yes",
    "bsd-3-clause": "yes",
    "cc0-1.0": "yes",
    "cc-by-2.0": "yes",
    "cc-by-3.0": "yes",
    "cc-by-4.0": "yes",
    "unlicense": "yes",
    "artistic-2.0": "yes",
    "bsl-1.0": "yes",
    "ecl-2.0": "yes",
    "wtfpl": "yes",
    # Non-commercial
    "cc-by-nc-2.0": "no",
    "cc-by-nc-3.0": "no",
    "cc-by-nc-4.0": "no",
    "cc-by-nc-sa-2.0": "no",
    "cc-by-nc-sa-3.0": "no",
    "cc-by-nc-sa-4.0": "no",
    "cc-by-nc-nd-3.0": "no",
    "cc-by-nc-nd-4.0": "no",
    # Conditional: use restrictions or extra terms
    "openrail": "conditional",
    "openrail++": "conditional",
    "bigscience-openrail-m": "conditional",
    "creativeml-openrail-m": "conditional",
    "bigscience-bloom-rail-1.0": "conditional",
    "bigcode-openrail-m": "conditional",
    "llama2": "conditional",
    "llama3": "conditional",
    "llama3.1": "conditional",
    "llama3.2": "conditional",
    "llama3.3": "conditional",
    "gemma": "conditional",
    # Conditional: copyleft (commercial use allowed, with obligations)
    "cc-by-sa-3.0": "conditional",
    "cc-by-sa-4.0": "conditional",
    "gpl": "conditional",
    "gpl-2.0": "conditional",
    "gpl-3.0": "conditional",
    "lgpl-2.1": "conditional",
    "lgpl-3.0": "conditional",
    "agpl-3.0": "conditional",
    "mpl-2.0": "conditional",
}

# D6: Indic language tags we sample the long tail for.
INDIC_LANGS = ("hi", "mr", "bn", "ta", "te", "gu", "kn", "ml", "pa", "ur")


def commercial_status(license_id: str | None) -> str:
    """Map a license id to "yes" / "no" / "conditional" / "unknown" (D3)."""
    if not license_id:
        return "unknown"
    return LICENSE_COMMERCIAL.get(license_id.strip().lower(), "unknown")


def license_from_tags(tags: list[str]) -> str | None:
    """Hub models carry their license as a "license:<id>" tag."""
    for tag in tags:
        if tag.startswith("license:"):
            return tag.split(":", 1)[1]
    return None


def normalize_languages(langs: list[str] | str | None) -> list[str]:
    """Lower-cased, de-duplicated ISO codes. Empty list means unknown (D12)."""
    if not langs:
        return []
    if isinstance(langs, str):
        langs = [langs]
    seen: list[str] = []
    for lang in langs:
        code = lang.strip().lower()
        if code and code not in seen:
            seen.append(code)
    return seen


def size_mb(siblings) -> float | None:
    """Model size in MB, or None when it can't be determined.

    Blocked on open question Q2 (which files count: safetensors vs .bin,
    quantized variants). Agree the rule, record it in decisions.md, then
    implement it here.
    """
    raise NotImplementedError("Size rule pending Q2 in decisions.md")


def to_metadata(
    *,
    model_id: str,
    task: str,
    languages: list[str],
    size: float | None,
    license_id: str | None,
    downloads: int,
    section: str,
) -> dict:
    """Build Pinecone metadata. size_mb is omitted, not faked, when unknown (D12)."""
    meta = {
        "model_id": model_id,
        "task": task,
        "languages": languages,
        "language_status": "known" if languages else "unknown",
        "size_status": "known" if size is not None else "unknown",
        "commercial": commercial_status(license_id),
        "downloads": downloads,
        "section": section,
    }
    if size is not None:
        meta["size_mb"] = size
    return meta
