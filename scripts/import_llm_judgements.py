"""Import grades made by independent LLM judge agents into the label files, with checks.

    python -m scripts.import_llm_judgements --dir <folder with out_*.csv>

Each judge read a blind batch (request, model, card excerpt; no system names, no extractor fields) and wrote
`out_p1_batchK.csv`, `out_p2_batchK.csv` and `out_faith_batchK.csv`. This script verifies that every pair of the sheet is graded exactly once,
that grades are 0/1/2, and writes `labels_pass1.csv`, `labels_pass2.csv`, `faithfulness_labels.csv` (timestamps are the REAL modification
times of the judges' files), `llm_judge_reasons.csv` (the one-line reasons, for audit) and `labeller.txt` (who graded, which the reports print).
"""

from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path

LABELS = Path("eval/labels")
WHO = "independent Claude agents (LLM judges), not humans"


def read_outputs(folder: Path, prefix: str) -> list[tuple[dict, float]]:
    rows = []
    for f in sorted(folder.glob(f"out_{prefix}*.csv")):
        mtime = f.stat().st_mtime
        with open(f, encoding="utf-8", newline="") as fh:
            rows += [(r, mtime) for r in csv.DictReader(fh)]
    return rows


def write_labels(path: Path, graded: list[tuple[str, int, float]]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pair_id", "grade", "ts"])
        for pid, g, ts in graded:
            w.writerow([pid, g, int(ts)])


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    args = ap.parse_args(argv)
    folder = Path(args.dir)
    sheet = [r["pair_id"] for r in csv.DictReader(open(LABELS / "relevance_sheet.csv", encoding="utf-8"))]
    qids = sorted({p.split("|", 1)[0] for p in sheet})
    retest_q = set(random.Random(99).sample(qids, min(15, len(qids))))
    expect = {1: set(sheet), 2: {p for p in sheet if p.split("|", 1)[0] in retest_q}}
    reasons = []
    for n in (1, 2):
        rows = read_outputs(folder, f"p{n}_")
        graded = []
        for r, ts in rows:
            if r["grade"] not in ("0", "1", "2"):
                raise SystemExit(f"pass {n}: bad grade {r['grade']!r} for {r['pair_id']}")
            graded.append((r["pair_id"], int(r["grade"]), ts))
            reasons.append((n, r["pair_id"], r["grade"], r.get("reason", "")))
        ids = [g[0] for g in graded]
        if len(ids) != len(set(ids)) or set(ids) != expect[n]:
            raise SystemExit(f"pass {n}: graded {len(set(ids))} distinct of {len(expect[n])} expected "
                             f"(missing {len(expect[n] - set(ids))}, extra {len(set(ids) - expect[n])}, duplicates {len(ids) - len(set(ids))})")
        write_labels(LABELS / f"labels_pass{n}.csv", sorted(graded))
        print(f"pass {n}: {len(graded)} pairs graded")
    with open(LABELS / "llm_judge_reasons.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pass", "pair_id", "grade", "reason"])
        w.writerows(reasons)
    items = {r["item_id"] for r in csv.DictReader(open(LABELS / "faithfulness_sheet.csv", encoding="utf-8"))}
    fr = read_outputs(folder, "faith_")
    by_query = {i.split("|", 1)[0]: i for i in items}
    if len(by_query) == len(items):                   # one explanation per query: a bare "q036" is unambiguous
        fixed = 0
        for r, _ in fr:
            if r["item_id"] not in items and r["item_id"] in by_query:
                r["item_id"], fixed = by_query[r["item_id"]], fixed + 1
        if fixed:
            print(f"faithfulness: {fixed} item ids were given as the bare query id and were mapped to the full id")
    got = [r["item_id"] for r, _ in fr]
    if set(got) != items or len(got) != len(set(got)):
        raise SystemExit(f"faithfulness: {len(set(got))} distinct of {len(items)} expected")
    with open(LABELS / "faithfulness_labels.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["item_id", "claims", "supported", "note", "ts"])
        for r, ts in sorted(fr, key=lambda x: x[0]["item_id"]):
            c, s = int(r["claims"]), int(r["supported"])
            if not 0 <= s <= c:
                raise SystemExit(f"faithfulness: supported {s} > claims {c} for {r['item_id']}")
            w.writerow([r["item_id"], c, s, r.get("note", ""), int(ts)])
    (LABELS / "labeller.txt").write_text(WHO + "\n", encoding="utf-8")
    print(f"faithfulness: {len(got)} items scored; labeller: {WHO}")


if __name__ == "__main__":
    main()
