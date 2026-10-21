"""Cut and check the data snapshot (D21), and produce the data-quality report.

The snapshot is the normalized metadata (not the raw cache, not the card text): small
enough to attach to a GitHub Release. Its checksum is recorded in config.yaml so everyone
evaluates against the same data. It is deterministic: same raw cache -> same bytes.

    python -m src.snapshot build      # writes data/snapshot-<date>/records.jsonl.gz
"""

from __future__ import annotations

import gzip
import hashlib
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

from src import ingest
from src.clean import clean_card, doc_quality
from src.normalize import INDIC_LANGS, license_rights, normalize_record, size_unknown_reason


def snapshot_record(raw: dict, card_markdown: str, canonical: dict[str, str] | None = None) -> dict:
    """The normalized metadata plus the extra fields the data-quality report needs."""
    meta = normalize_record(raw, canonical)
    meta["doc_quality"] = doc_quality(clean_card(card_markdown))
    card = raw.get("cardData") or {}
    files = [(f.get("rfilename", ""), f.get("size")) for f in raw.get("siblings") or []]
    license_id = card.get("license") if isinstance(card.get("license"), str) else None
    meta["_license"] = license_id
    meta["_languages_raw"] = card.get("language")
    meta["_has_model_index"] = bool(card.get("model-index"))
    meta["_size_unknown_reason"] = size_unknown_reason(files)
    return meta


def write_snapshot(records: list[dict], path: Path) -> str:
    """Write sorted, gzip'd JSONL deterministically (fixed mtime) and return its sha256."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = "".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n"
                    for r in sorted(records, key=lambda r: r["model_id"]))
    with open(path, "wb") as raw_file, gzip.GzipFile(fileobj=raw_file, mode="wb", mtime=0) as gz:
        gz.write(lines.encode("utf-8"))
    return sha256_of(path)


def sha256_of(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_snapshot(path: Path, expected_sha256: str | None = None) -> list[dict]:
    """Read a snapshot, refusing a file whose checksum doesn't match config.yaml."""
    if expected_sha256 and sha256_of(path) != expected_sha256:
        raise ValueError(f"{path} does not match the checksum in config.yaml; re-download the release asset")
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _pct(n: int, total: int) -> float:
    return round(100 * n / total, 1) if total else 0.0


def data_quality_report(records: list[dict]) -> dict:
    """The measures in docs/data-pipeline.md section 7, as counts and percentages."""
    n = len(records)
    unknown_size = [r for r in records if r.get("size_status") == "unknown"]
    unmapped = Counter(r["_license"] for r in records
                       if r.get("_license") and license_rights(r["_license"]) == ("unknown", "unknown"))
    raw_lang_tokens = Counter(str(x).lower() for r in records
                              for x in (r["_languages_raw"] if isinstance(r.get("_languages_raw"), list)
                                        else [r.get("_languages_raw")] if r.get("_languages_raw") else []))
    return {
        "models": n,
        "per_task": dict(Counter(r.get("task") for r in records)),
        "size_unknown": {"count": len(unknown_size), "pct": _pct(len(unknown_size), n),
                         "by_reason": dict(Counter(r.get("_size_unknown_reason") for r in unknown_size))},
        "commercial_unknown_pct": _pct(sum(r["commercial"] == "unknown" for r in records), n),
        "modifiable_unknown_pct": _pct(sum(r["modifiable"] == "unknown" for r in records), n),
        "top_unmapped_licenses": unmapped.most_common(30),
        "language_unknown_pct": _pct(sum(r["language_status"] == "unknown" for r in records), n),
        "multilingual_pct": _pct(sum(bool(r.get("multilingual")) for r in records), n),
        "raw_language_tokens_not_2_letters": [t for t, _ in raw_lang_tokens.most_common()
                                              if len(t) != 2][:40],
        "indic_tagged_pct": _pct(sum(any(lang in r.get("languages", []) for lang in INDIC_LANGS)
                                     for r in records), n),
        "base_model_pct": _pct(sum("base_model" in r for r in records), n),
        "param_count_pct": _pct(sum("param_count" in r for r in records), n),
        "doc_minimal_pct": _pct(sum(r.get("doc_quality") == "minimal" for r in records), n),
        "model_index_pct": _pct(sum(bool(r.get("_has_model_index")) for r in records), n),
        "directions_from_name": sum("directions" in r for r in records),
    }


def collect_records(raw_dir: Path | None = None) -> list[dict]:
    """Normalised snapshot records for every model in the raw cache (those with both a JSON and a card file)."""
    raw_dir = raw_dir or ingest.RAW_DIR
    canonical_path = raw_dir / "_canonical_ids.json"
    canonical = (json.loads(canonical_path.read_text(encoding="utf-8")) if canonical_path.exists() else None)
    records = []
    for path in sorted(raw_dir.glob("*.json")):
        if path.name.startswith("_"):
            continue
        card_path = path.with_suffix(".md")
        card = card_path.read_text(encoding="utf-8") if card_path.exists() else ""
        records.append(snapshot_record(json.loads(path.read_text(encoding="utf-8")), card, canonical))
    return records


def build(raw_dir: Path | None = None, out_dir: Path | None = None, today: str | None = None):
    records = collect_records(raw_dir)
    today = today or date.today().isoformat()
    out = (out_dir or Path("data") / f"snapshot-{today}") / "records.jsonl.gz"
    return out, write_snapshot(records, out), today, data_quality_report(records)


def main(argv: list[str]) -> None:
    out, sha, today, report = build()
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nwrote {out}\nPaste into config.yaml:\n  snapshot_date: {today}\n  snapshot_sha256: {sha}")


if __name__ == "__main__":
    main(sys.argv[1:])
