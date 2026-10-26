"""Turn the hand-labelled relevance grades into the numbers for the write-up.

    python -m eval.relevance_report [--dir eval/labels]

Reads `relevance_sheet.csv` (what was labelled), `_key.json` (which systems returned each pair: kept out of the
labelling page so the labelling stays blind), `labels_pass1.csv` and, if it exists, `labels_pass2.csv` (a repeat pass
over a random subset). Writes `eval/results/relevance.md`.

Agreement is between two grading passes by the same kind of grader (a person a day apart, or two independent LLM passes), not
inter-annotator agreement between humans. Who graded is stated in the report, from `eval/labels/labeller.txt`.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from eval.metrics import cohens_kappa


def load_labels(path: Path) -> dict[str, int]:
    """pair_id -> grade. The file is append-only; when a pair appears twice the later row wins (an "undo" or a fix)."""
    out: dict[str, int] = {}
    if not path.exists():
        return out
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("grade") in ("0", "1", "2"):
                out[row["pair_id"]] = int(row["grade"])
            elif row.get("grade") == "":                    # an undo
                out.pop(row["pair_id"], None)
    return out


def per_system(labels: dict[str, int], key: dict[str, list[str]], k: int = 5) -> dict[str, dict]:
    """Per system: mean grade over its labelled top-k models, share of queries with at least one grade-2 model,
    and share of its models graded at least 1. Only queries the labeller finished count, for every system alike."""
    by_query: dict[str, set[str]] = defaultdict(set)
    for pid in key:
        by_query[pid.split("|", 1)[0]].add(pid)
    done = {q for q, pids in by_query.items() if all(p in labels for p in pids)}      # fully labelled queries only
    out: dict[str, dict] = {}
    systems = sorted({s for v in key.values() for s in v})
    for s in systems:
        grades, best, plausible, n_q = [], [], [], 0
        for q in sorted(done):
            mine = [labels[p] for p in by_query[q] if s in key[p]][:k]
            if not mine:
                continue                                    # the system returned nothing for this query
            n_q += 1
            grades += mine
            best.append(max(mine) == 2)
            plausible += [g >= 1 for g in mine]
        out[s] = {"queries": n_q, "models": len(grades),
                  "mean_grade": round(sum(grades) / len(grades), 3) if grades else None,
                  "queries_with_a_2_pct": round(100 * sum(best) / len(best), 1) if best else None,
                  "graded_1_or_2_pct": round(100 * sum(plausible) / len(plausible), 1) if plausible else None}
    out["_labelled_queries"] = {"queries": len(done), "of": len(by_query)}
    return out


def retest(pass1: dict[str, int], pass2: dict[str, int]) -> dict | None:
    common = sorted(set(pass1) & set(pass2))
    if len(common) < 2:
        return None
    a, b = [pass1[p] for p in common], [pass2[p] for p in common]
    return {"items": len(common), "same_grade_pct": round(100 * sum(x == y for x, y in zip(a, b)) / len(a), 1),
            "kappa_nominal": round(cohens_kappa(a, b), 3), "kappa_quadratic": round(cohens_kappa(a, b, "quadratic"), 3),
            "big_disagreements_0_vs_2": sum(abs(x - y) == 2 for x, y in zip(a, b))}


def labeller(directory: Path = Path("eval/labels")) -> str:
    """Who graded, from `eval/labels/labeller.txt` (written when labels are imported); a person by default."""
    f = directory / "labeller.txt"
    return f.read_text(encoding="utf-8").strip() if f.exists() else "one human labeller"


def render(stats: dict, agree: dict | None, who: str = "one human labeller") -> str:
    lq = stats["_labelled_queries"]
    L = [f"# Relevance @5 (blind; graded by {who})", "",
         f"Queries fully graded: **{lq['queries']} of {lq['of']}**. Grades 0/1/2 against the purpose of the request "
         "(size and license are checked automatically, not graded).", "",
         "| System | Queries | Models graded | Mean grade | Queries with a grade-2 model % | Models graded 1 or 2 % |", "|---|---|---|---|---|---|"]
    for s, m in stats.items():
        if s.startswith("_"):
            continue
        L.append(f"| {s} | {m['queries']} | {m['models']} | {m['mean_grade']} | {m['queries_with_a_2_pct']} | {m['graded_1_or_2_pct']} |")
    L += ["", "## Agreement between the two grading passes", ""]
    if agree is None:
        L.append("No repeat pass yet.")
    else:
        L += [f"- items graded twice: {agree['items']}; identical grade on **{agree['same_grade_pct']}%**",
              f"- Cohen's kappa: nominal **{agree['kappa_nominal']}**, quadratic-weighted **{agree['kappa_quadratic']}**",
              f"- 0-versus-2 disagreements: {agree['big_disagreements_0_vs_2']}",
              "", f"Both passes were made by: {who}. This is agreement between two independent passes by the same kind of grader "
              "(test-retest of one labeller, or two LLM passes), not agreement between independent humans."]
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="eval/labels")
    args = ap.parse_args(argv)
    d = Path(args.dir)
    key = json.loads((d / "_key.json").read_text(encoding="utf-8"))
    p1, p2 = load_labels(d / "labels_pass1.csv"), load_labels(d / "labels_pass2.csv")
    text = render(per_system(p1, key), retest(p1, p2), labeller(d))
    out = Path("eval/results/relevance.md")
    out.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
