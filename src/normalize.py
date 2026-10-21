"""Turn raw Hub metadata into the D10 schema, marking gaps as unknown (D3, D12).

Metadata written on every chunk of a model (D10):
    model_id, task, downloads, doc_quality, languages, language_status, multilingual,
    size_mb (only when known), size_status, param_count (only when known),
    commercial, modifiable, base_model (only when declared), lineage_status

`language_status` is an addition to D10: Pinecone cannot filter on "list is empty",
so an explicit flag is needed to keep unknown-language models (D12).
`section` and `text` are per-chunk and added by index.py.
"""

from __future__ import annotations

from src.config import CFG

INDIC_LANGS = tuple(CFG["corpus"]["indic_langs"])

# D3 + D14: license id -> (commercial use, modification rights).
# Anything not listed is ("unknown", "unknown"); never guess.
# "conditional" = allowed only under extra terms a human must read: use restrictions
# that carry over to derivatives (OpenRAIL, Llama-style) or copyleft obligations.
# Note CC-BY-NC is modifiable "yes" but the result stays non-commercial (see adapt.rights_notes).
LICENSE_RIGHTS: dict[str, tuple[str, str]] = {
    # Permissive: use commercially, modify and sell
    "apache-2.0": ("yes", "yes"),
    "mit": ("yes", "yes"),
    "bsd": ("yes", "yes"),
    "bsd-2-clause": ("yes", "yes"),
    "bsd-3-clause": ("yes", "yes"),
    "cc0-1.0": ("yes", "yes"),
    "cc-by-2.0": ("yes", "yes"),
    "cc-by-3.0": ("yes", "yes"),
    "cc-by-4.0": ("yes", "yes"),
    "unlicense": ("yes", "yes"),
    "artistic-2.0": ("yes", "yes"),
    "bsl-1.0": ("yes", "yes"),
    "ecl-2.0": ("yes", "yes"),
    "wtfpl": ("yes", "yes"),
    # Non-commercial: modification allowed, result non-commercial only
    "cc-by-nc-2.0": ("no", "yes"),
    "cc-by-nc-3.0": ("no", "yes"),
    "cc-by-nc-4.0": ("no", "yes"),
    "cc-by-nc-sa-2.0": ("no", "yes"),
    "cc-by-nc-sa-3.0": ("no", "yes"),
    "cc-by-nc-sa-4.0": ("no", "yes"),
    # No derivatives
    "cc-by-nd-4.0": ("yes", "no"),
    "cc-by-nc-nd-3.0": ("no", "no"),
    "cc-by-nc-nd-4.0": ("no", "no"),
    # Use restrictions carry over to the fine-tune
    "openrail": ("conditional", "conditional"),
    "openrail++": ("conditional", "conditional"),
    "bigscience-openrail-m": ("conditional", "conditional"),
    "creativeml-openrail-m": ("conditional", "conditional"),
    "bigscience-bloom-rail-1.0": ("conditional", "conditional"),
    "bigcode-openrail-m": ("conditional", "conditional"),
    "llama2": ("conditional", "conditional"),
    "llama3": ("conditional", "conditional"),
    "llama3.1": ("conditional", "conditional"),
    "llama3.2": ("conditional", "conditional"),
    "llama3.3": ("conditional", "conditional"),
    "gemma": ("conditional", "conditional"),
    # Copyleft: modification allowed, commercial use comes with obligations
    "cc-by-sa-3.0": ("conditional", "yes"),
    "cc-by-sa-4.0": ("conditional", "yes"),
    "gpl": ("conditional", "yes"),
    "gpl-2.0": ("conditional", "yes"),
    "gpl-3.0": ("conditional", "yes"),
    "lgpl-2.1": ("conditional", "yes"),
    "lgpl-3.0": ("conditional", "yes"),
    "agpl-3.0": ("conditional", "yes"),
    "mpl-2.0": ("conditional", "yes"),
}

# D18: models that cover Indic languages without tagging them. SEED ONLY: add entries
# (target ~20) only after checking the language list on each model's card.
MULTILINGUAL_MODELS: dict[str, tuple[str, ...]] = {
    **{
        name: ("en", *INDIC_LANGS)
        for name in (
            "xlm-roberta-base",
            "xlm-roberta-large",
            "FacebookAI/xlm-roberta-base",
            "FacebookAI/xlm-roberta-large",
        )
    },
    **{
        f"openai/whisper-{size}": ("en", *INDIC_LANGS)
        for size in ("tiny", "base", "small", "medium", "large", "large-v2", "large-v3")
    },
}

# D20 size rule: only these top-level files count, safetensors first, .bin as fallback.
# Excluded: .onnx, .gguf, TF/Flax copies, nested folders, optimizer/training state.
_WEIGHT_PREFIXES = ("model", "pytorch_model")
MB = 1_000_000  # decimal, matching the size shown on the Hub


def license_rights(license_id: str | None) -> tuple[str, str]:
    """(commercial, modifiable), each "yes" / "no" / "conditional" / "unknown"."""
    if not license_id:
        return ("unknown", "unknown")
    return LICENSE_RIGHTS.get(license_id.strip().lower(), ("unknown", "unknown"))


def commercial_status(license_id: str | None) -> str:
    return license_rights(license_id)[0]


def modifiable_status(license_id: str | None) -> str:
    return license_rights(license_id)[1]


def license_from_tags(tags: list[str]) -> str | None:
    """Hub models carry their license as a "license:<id>" tag."""
    for tag in tags:
        if tag.startswith("license:"):
            return tag.split(":", 1)[1]
    return None


def normalize_languages(langs: list[str] | str | None) -> list[str]:
    """Lower-cased, de-duplicated codes. Empty list means unknown (D12)."""
    if not langs:
        return []
    if isinstance(langs, str):
        langs = [langs]
    seen: list[str] = []
    for lang in langs:
        code = str(lang).strip().lower()
        if code and code not in seen:
            seen.append(code)
    return seen


def apply_multilingual_map(model_id: str, languages: list[str]) -> tuple[list[str], bool]:
    """Merge the hand-made multilingual map into the tagged languages (D18)."""
    covered = MULTILINGUAL_MODELS.get(model_id)
    if covered is None:
        return languages, False
    return normalize_languages([*languages, *covered]), True


def _is_main_weight(name: str, suffix: str) -> bool:
    return "/" not in name and name.endswith(suffix) and name.startswith(_WEIGHT_PREFIXES)


def size_mb(files: list[tuple[str, int | None]]) -> float | None:
    """Model size in MB under the D20 rule, or None when it can't be determined.

    `files` is a list of (path, size_in_bytes) from the repo listing. Sums the
    top-level safetensors weights; if there are none, the top-level .bin weights.
    A weight file with no recorded size makes the whole answer unknown.
    """
    for suffix in (".safetensors", ".bin"):
        weights = [(n, s) for n, s in files if _is_main_weight(n, suffix)]
        if weights:
            if any(s is None for _, s in weights):
                return None
            return sum(s for _, s in weights) / MB  # exact: no rounding on a hard constraint
    return None


def param_count(safetensors_info: dict | None) -> int | None:
    """Total parameters from the Hub's safetensors metadata, if present."""
    if not safetensors_info:
        return None
    total = safetensors_info.get("total")
    return int(total) if isinstance(total, (int, float)) and total > 0 else None


def base_model(card_data: dict | None) -> str | None:
    """The declared `base_model` (first one if several); None when absent."""
    value = (card_data or {}).get("base_model")
    if isinstance(value, list):
        value = value[0] if value else None
    return value.strip() if isinstance(value, str) and value.strip() else None


def normalize_record(raw: dict) -> dict:
    """Raw Hub API response (`/api/models/<id>?blobs=true&cardData=true`) -> model record.

    The record holds the per-model metadata; index.py adds `section` and `text` per
    chunk and clean.py contributes `doc_quality`. Field names follow the Hub API
    response as documented; verify against a live response on day 1.
    """
    model_id = raw["id"]
    card = raw.get("cardData") or {}
    tags = raw.get("tags") or []

    languages = normalize_languages(card.get("language"))
    languages, multilingual = apply_multilingual_map(model_id, languages)

    files = [(s.get("rfilename", ""), s.get("size")) for s in raw.get("siblings") or []]
    size = size_mb(files)
    base = base_model(card)
    license_id = card.get("license") or license_from_tags(tags)
    commercial, modifiable = license_rights(license_id if isinstance(license_id, str) else None)

    meta: dict = {
        "model_id": model_id,
        "task": raw.get("pipeline_tag"),
        "downloads": int(raw.get("downloads") or 0),
        "languages": languages,
        "language_status": "known" if languages else "unknown",
        "multilingual": multilingual,
        "size_status": "known" if size is not None else "unknown",
        "commercial": commercial,
        "modifiable": modifiable,
        "lineage_status": "known" if base else "unknown",
    }
    # D12: optional numbers/strings are written only when known, never as sentinels.
    if size is not None:
        meta["size_mb"] = size
    params = param_count(raw.get("safetensors"))
    if params is not None:
        meta["param_count"] = params
    if base:
        meta["base_model"] = base
    return meta

