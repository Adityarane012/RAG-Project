"""Build-on information, all computed from metadata (D14, D23, D24).

Rights, lineage and memory come from code; the LLM only explains them (D2).
Also backs check-a-model mode: `model_report` takes one model's metadata and
needs no retrieval.
"""

from __future__ import annotations

from collections import defaultdict

from src.config import CFG
from src.guide import TASK_GUIDES, model_page_url
from src.verify import FAIL, PASS, UNKNOWN

_A = CFG["adapt"]
GB = 1_000_000_000


# --- rights ------------------------------------------------------------------

def rights_notes(meta: dict) -> list[str]:
    """Plain-language caveats on `commercial` / `modifiable` (D14)."""
    commercial, modifiable = meta.get("commercial", "unknown"), meta.get("modifiable", "unknown")
    notes = []
    if modifiable == "yes" and commercial == "no":
        notes.append("You may modify it, but the result stays non-commercial.")
    if modifiable == "no":
        notes.append("No derivatives allowed: you may not fine-tune and redistribute it.")
    if "conditional" in (commercial, modifiable):
        notes.append("Extra terms apply (e.g. use restrictions that carry over to a "
                     "fine-tune). Read the license before relying on it.")
    if "unknown" in (commercial, modifiable):
        notes.append("The license is missing or not one we can interpret.")
    return notes


# --- fine-tuning memory (lower bounds, excluding activations) ------------------

def memory_estimate(param_count: int | None) -> dict:
    """GB needed per method, compared with the reference GPU (a free Colab T4).

    Lower bounds that exclude activations; label them as estimates in the UI.
    """
    gpu = _A["reference_gpu_gb"]
    if not param_count:
        return {"status": UNKNOWN, "reference_gpu_gb": gpu, "methods": {}}
    inference = param_count * _A["bytes_per_param_inference"]
    # LoRA: frozen base weights at inference precision + a small trainable adapter
    # trained at full-fine-tune cost per parameter.
    adapter = param_count * _A["lora_adapter_fraction"] * _A["bytes_per_param_full_finetune"]
    full = param_count * _A["bytes_per_param_full_finetune"]
    methods = {}
    for name, nbytes in (("inference", inference), ("lora", inference + adapter), ("full", full)):
        gb = nbytes / GB
        methods[name] = {"gb": round(gb, 1), "fits": PASS if gb <= gpu else FAIL}
    return {"status": PASS, "reference_gpu_gb": gpu, "methods": methods}


# --- lineage -------------------------------------------------------------------

def build_lineage_index(records: list[dict]) -> dict[str, list[dict]]:
    """base_model -> the models in the snapshot that declare it."""
    index: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        if r.get("base_model"):
            index[r["base_model"]].append(r)
    return index


def lineage(meta: dict, index: dict[str, list[dict]], langs: list[str] | None = None) -> dict:
    """"Fine-tune of X; N other fine-tunes exist (M for your language)" (D14).

    Missing `base_model` -> unknown. Counts cover our snapshot only, so they are
    "at least" figures for the Hub as a whole.
    """
    base = meta.get("base_model")
    if not base:
        return {"status": UNKNOWN}
    siblings = [m for m in index.get(base, []) if m["model_id"] != meta["model_id"]]
    in_lang = [m for m in siblings if langs and all(lang in m.get("languages", []) for lang in langs)]
    return {
        "status": PASS,
        "base_model": base,
        "other_finetunes": len(siblings),
        "other_finetunes_in_language": len(in_lang) if langs else None,
    }


# --- reported metrics (D24) ----------------------------------------------------

def reported_metrics(card_data: dict | None, limit: int = 5) -> list[dict]:
    """Author-reported `model-index` results, for display only: never a ranking signal."""
    out: list[dict] = []
    for entry in (card_data or {}).get("model-index") or []:
        for result in entry.get("results") or []:
            dataset = (result.get("dataset") or {}).get("name") or (result.get("dataset") or {}).get("type")
            for metric in result.get("metrics") or []:
                if metric.get("value") is None:
                    continue
                out.append({
                    "dataset": dataset,
                    "metric": metric.get("name") or metric.get("type"),
                    "value": metric["value"],
                    "label": "reported by the author, not verified",
                })
    return out[:limit]


# --- the D14 panel / D23 report ------------------------------------------------

def model_report(meta: dict, index: dict[str, list[dict]] | None = None,
                 langs: list[str] | None = None, card_data: dict | None = None) -> dict:
    """Everything the "Build on it" panel and check-a-model mode show for one model."""
    return {
        "model_id": meta["model_id"],
        "rights": {"commercial": meta.get("commercial", "unknown"),
                   "modifiable": meta.get("modifiable", "unknown"),
                   "notes": rights_notes(meta)},
        "lineage": lineage(meta, index or {}, langs),
        "memory": memory_estimate(meta.get("param_count")),
        "task_guide": TASK_GUIDES.get(meta.get("task")),
        "model_page": model_page_url(meta["model_id"]),
        "reported_metrics": reported_metrics(card_data),
    }
