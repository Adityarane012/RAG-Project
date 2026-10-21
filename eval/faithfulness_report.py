"""Explanation faithfulness from the hand-scored sheet.

    python -m eval.faithfulness_report

Each scored item has the number of factual claims in the explanation and how many of them the shown card passages support.
Reports the claim-level share supported and the share of explanations with every claim supported.
Writes `eval/results/faithfulness.md`.
"""

from __future__ import annotations

import csv
from pathlib import Path

LABELS = Path("eval/labels/faithfulness_labels.csv")


def load(path: Path = LABELS) -> dict[str, dict]:
    """item_id -> {"claims", "supported", "note"}; the file is append-only, the last row for an item wins."""
    out: dict[str, dict] = {}
    if not path.exists():
        return out
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            try:
                claims, supported = int(r["claims"]), int(r["supported"])
            except (KeyError, ValueError):
                continue
            if 0 <= supported <= claims:
                out[r["item_id"]] = {"claims": claims, "supported": supported, "note": r.get("note", "")}
    return out


def summarise(scored: dict[str, dict]) -> dict:
    items = list(scored.values())
    claims = sum(i["claims"] for i in items)
    supported = sum(i["supported"] for i in items)
    return {"items": len(items), "claims": claims, "supported": supported,
            "claims_supported_pct": round(100 * supported / claims, 1) if claims else None,
            "explanations_fully_supported_pct": round(100 * sum(i["supported"] == i["claims"] for i in items) / len(items), 1) if items else None,
            "unsupported_notes": [(k, v["note"]) for k, v in scored.items() if v["supported"] < v["claims"] and v["note"]]}


def render(s: dict) -> str:
    L = ["# Explanation faithfulness (hand-scored)", "",
         f"- explanations scored: **{s['items']}**; factual claims checked: {s['claims']}; supported by the shown card passages: {s['supported']}",
         f"- claims supported: **{s['claims_supported_pct']}%**",
         f"- explanations with every claim supported: **{s['explanations_fully_supported_pct']}%**", ""]
    if s["unsupported_notes"]:
        L += ["## Unsupported claims (notes)", ""] + [f"- `{k}`: {n}" for k, n in s["unsupported_notes"]]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    text = render(summarise(load()))
    Path("eval/results/faithfulness.md").write_text(text, encoding="utf-8")
    print(text)
