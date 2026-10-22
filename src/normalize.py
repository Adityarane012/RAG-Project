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

import re
from dataclasses import dataclass

from src.config import CFG

INDIC_LANGS = tuple(CFG["corpus"]["indic_langs"])

# D3 + D14: license id -> (commercial use, modification rights).
# Anything not listed is ("unknown", "unknown"); never guess.
# "conditional" = allowed only under extra terms a human must read: use restrictions
# that carry over to derivatives (OpenRAIL, Llama-style) or share-alike obligations (GPL, CC-BY-SA).
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
    "afl-3.0": ("yes", "yes"),
    "openmdw-1.0": ("yes", "yes"),     # Linux Foundation OpenMDW: permissive, attribution
    "openmdw-1.1": ("yes", "yes"),
    "pddl": ("yes", "yes"),            # public-domain dedication (a data licence; seen on a few cards)
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
    "llama4": ("conditional", "conditional"),
    "lfm1.0": ("conditional", "conditional"),                     # revenue threshold applies
    "nvidia-open-model-license": ("conditional", "conditional"),  # use conditions carry over
    "falcon-llm-license": ("conditional", "conditional"),         # royalty above a revenue threshold
    # Copyleft / share-alike: derivatives allowed but must carry the same terms, and
    # commercial use comes with obligations. Both rights need a human to read the terms.
    "cc-by-sa-3.0": ("conditional", "conditional"),
    "cc-by-sa-4.0": ("conditional", "conditional"),
    "gpl": ("conditional", "conditional"),
    "gpl-2.0": ("conditional", "conditional"),
    "gpl-3.0": ("conditional", "conditional"),
    "lgpl": ("conditional", "conditional"),
    "odbl": ("conditional", "conditional"),
    "lgpl-2.1": ("conditional", "conditional"),
    "lgpl-3.0": ("conditional", "conditional"),
    "agpl-3.0": ("conditional", "conditional"),
    "mpl-2.0": ("conditional", "conditional"),
}

# D18: models that cover Indic languages without tagging them. Owned by the data lead.
# EVERY entry must cite where its language list came from, and `checked` is flipped to True
# only after someone has compared the Indic ten against that source. Target ~20 entries.
@dataclass(frozen=True)
class MultilingualEntry:
    languages: tuple[str, ...]
    source: str
    checked: bool = False


_XLMR_SOURCE = "XLM-R paper (Conneau et al., 2020), language list; and the model card"
_WHISPER_SOURCE = "Whisper paper (Radford et al., 2022) and the model card, supported-language list"

_QWEN_ASR_SOURCE = ("Qwen3-ASR model card, 'Supported Languages' table (30 languages); the only Indic-ten language "
                    "listed is Hindi (compared 2026-10-21)")

MULTILINGUAL_MODELS: dict[str, MultilingualEntry] = {
    **{name: MultilingualEntry(("en", "hi"), _QWEN_ASR_SOURCE, checked=True)
       for name in ("Qwen/Qwen3-ASR-0.6B", "Qwen/Qwen3-ASR-1.7B")},
    **{
        name: MultilingualEntry(("en", *INDIC_LANGS), _XLMR_SOURCE)
        for name in (
            "xlm-roberta-base",
            "xlm-roberta-large",
            "FacebookAI/xlm-roberta-base",
            "FacebookAI/xlm-roberta-large",
        )
    },
    **{
        f"openai/whisper-{size}": MultilingualEntry(("en", *INDIC_LANGS), _WHISPER_SOURCE)
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


# Cards write languages in many ways: "hin", "hi-IN", "multilingual". Only forms that
# are unambiguous for the languages we filter on are aliased; everything else is kept
# as written, so it can't be mistaken for a different language.
LANG_ALIASES = {"hin": "hi", "mar": "mr", "ben": "bn", "tam": "ta", "tel": "te", "guj": "gu",
                "kan": "kn", "mal": "ml", "pan": "pa", "urd": "ur", "eng": "en"}
MULTILINGUAL_TOKENS = {"multilingual", "multi", "mul"}


def declares_multilingual(langs: list[str] | str | None) -> bool:
    """True if the card says "multilingual" without (necessarily) listing languages."""
    if isinstance(langs, str):
        langs = [langs]
    return any(str(x).strip().lower() in MULTILINGUAL_TOKENS for x in langs or [])


def normalize_languages(langs: list[str] | str | None) -> list[str]:
    """Lower-cased, de-duplicated 2-letter codes where we can tell. Region subtags are
    dropped ("hi-IN" -> "hi"), "multilingual" is not a language and is removed (see
    declares_multilingual). Empty list means unknown (D12)."""
    if not langs:
        return []
    if isinstance(langs, str):
        langs = [langs]
    seen: list[str] = []
    for lang in langs:
        code = str(lang).strip().lower().replace("_", "-").split("-")[0]
        code = LANG_ALIASES.get(code, code)
        if code and code not in MULTILINGUAL_TOKENS and code not in seen:
            seen.append(code)
    return seen


def apply_multilingual_map(model_id: str, languages: list[str]) -> tuple[list[str], bool]:
    """Merge the hand-made multilingual map into the tagged languages (D18)."""
    entry = MULTILINGUAL_MODELS.get(model_id)
    if entry is None:
        return languages, False
    return normalize_languages([*languages, *entry.languages]), True


# Direction is stated only by the Helsinki-NLP naming scheme `opus-mt-<src>-<tgt>`, which is
# one-directional. Anything else stays unknown. `tc-` names (opus-mt-tc-big-…) are excluded
# because their next tokens are not language codes. Third-party fine-tunes that keep the
# name are assumed to keep the direction (residual risk; shown to the user as "from model name").
_OPUS_MT = re.compile(r"(?:^|/)opus-mt-(?!tc-)([a-z]{2,3})-([a-z]{2,3})(?![a-z])")


def directions_from_name(model_id: str) -> list[str]:
    """["src-tgt"] for an opus-mt-<src>-<tgt> model id, else []."""
    m = _OPUS_MT.search(model_id.lower())
    if not m:
        return []
    src, tgt = (LANG_ALIASES.get(c, c) for c in m.groups())
    return [f"{src}-{tgt}"]


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


def size_unknown_reason(files: list[tuple[str, int | None]]) -> str | None:
    """Why a model's size is unknown, to decide whether the D20 rule needs widening.
    None when the size is known."""
    if size_mb(files) is not None:
        return None
    names = [n for n, _ in files]
    if any(_is_main_weight(n, ".safetensors") or _is_main_weight(n, ".bin") for n in names):
        return "weights_missing_size"
    if any(n.rsplit("/", 1)[-1].startswith("adapter_model") for n in names):
        return "adapter_only"
    if any("/" in n and n.endswith((".safetensors", ".bin")) for n in names):
        return "weights_only_in_subfolder"
    if any(n.endswith(".gguf") for n in names):
        return "gguf_only"
    if any(n.endswith((".safetensors", ".bin")) for n in names):
        return "weights_with_other_name"
    return "no_weight_files"


def normalize_record(raw: dict, canonical: dict[str, str] | None = None) -> dict:
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
    # "multilingual" is not a language. A card that says only that has no language list (unknown). A card that
    # lists languages AND says "multilingual" keeps its list, and verify treats a language missing from such a
    # list as unknown rather than a definite no (the list may be partial).
    multilingual = multilingual or declares_multilingual(card.get("language"))
    directions = directions_from_name(model_id)
    if directions:  # opus-mt-<src>-<tgt> names state both languages even when the card has no language field
        languages = normalize_languages([*languages, *directions[0].split("-")])

    files = [(s.get("rfilename", ""), s.get("size")) for s in raw.get("siblings") or []]
    size = size_mb(files)
    base = base_model(card)
    if base and canonical:
        base = canonical.get(base, base)  # legacy ids -> current ids, so lineage counts merge
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
    if directions:
        meta["directions"] = directions
        meta["direction_source"] = "model_name"
    return meta

