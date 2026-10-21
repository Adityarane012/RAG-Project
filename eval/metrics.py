"""Automatic evaluation metrics (D11). Pure functions over verified results, so the
same code scores our system and every baseline (D19): each baseline's top-5 is
re-verified with verify.verify() against the query's parsed constraints.

"Violation" and "unknown" are mutually exclusive per recommendation: a model with any
❌ is a violation; otherwise a model with any ⚠️ is unknown (D12).
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from src.verify import FAIL, UNKNOWN, overall

QUERY_KINDS = {"normal", "impossible", "vague"}
QUERY_SOURCES = {"teammate", "classmate"}


def _rates(tables_per_query: list[list[dict]], k: int) -> tuple[int, int, int]:
    total = fails = unknowns = 0
    for tables in tables_per_query:
        for table in tables[:k]:
            total += 1
            verdict = overall(table)
            fails += verdict == FAIL
            unknowns += verdict == UNKNOWN
    return total, fails, unknowns


def violation_rate_at_k(tables_per_query: list[list[dict]], k: int = 5) -> float:
    """Share of recommended models (top k per query) that break a hard constraint."""
    total, fails, _ = _rates(tables_per_query, k)
    return fails / total if total else 0.0


def unknown_rate_at_k(tables_per_query: list[list[dict]], k: int = 5) -> float:
    """Share of recommended models with ⚠️ on some constraint and no ❌."""
    total, _, unknowns = _rates(tables_per_query, k)
    return unknowns / total if total else 0.0


def abstention_accuracy(outcomes: list[str]) -> float:
    """On impossible queries: share where the system said no match. A relax offer
    ("no model meets all constraints; relax X?") counts as saying so."""
    return sum(o in ("abstain", "relax") for o in outcomes) / len(outcomes) if outcomes else 0.0


def clarification_rate(outcomes: list[str]) -> float:
    """On vague queries: share where it asked instead of guessing."""
    return sum(o == "clarify" for o in outcomes) / len(outcomes) if outcomes else 0.0


def modifiable_correctness(pairs: list[tuple[str | None, str]]) -> float:
    """Share of (license_id, shown `modifiable`) pairs that agree with the license map."""
    from src.normalize import modifiable_status

    return sum(modifiable_status(lic) == shown for lic, shown in pairs) / len(pairs) if pairs else 0.0


def latency_summary(seconds: list[float]) -> dict:
    return {"median": statistics.median(seconds), "worst": max(seconds)} if seconds else {}


def load_queries(path: str | Path) -> list[dict]:
    """Read eval/queries.jsonl: {"id", "query", "kind", "source"} per line. The set is
    written before tuning, by the teammate not building the pipeline (D11)."""
    queries = []
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        q = json.loads(line)
        missing = {"id", "query", "kind", "source"} - q.keys()
        if missing or q["kind"] not in QUERY_KINDS or q["source"] not in QUERY_SOURCES:
            raise ValueError(f"{path}:{n}: bad query record {q!r}")
        queries.append(q)
    return queries


def verifiably_impossible(records: list[dict], constraints: dict) -> bool:
    """True if EVERY model in the snapshot gets a ❌ (so even a model with unknowns is not
    a possible answer). Impossible test queries must satisfy this: otherwise an abstention
    miss would measure missing data, not the system (D11)."""
    from src.verify import verify

    return all(overall(verify(r, constraints)) == FAIL for r in records)


def cohens_kappa(a: list[int], b: list[int], weights: str | None = None) -> float:
    """Agreement between two labellers on the same items, corrected for chance.

    `weights`: None (nominal), "linear" or "quadratic" (for ordinal grades like 0/1/2,
    where 0-vs-2 is a worse disagreement than 0-vs-1). Returns 1.0 for perfect
    agreement; when chance agreement is already perfect (one label only) returns 1.0 if
    the labellers agree and 0.0 otherwise.
    """
    if len(a) != len(b) or not a:
        raise ValueError("need two equal-length, non-empty label lists")
    cats = sorted(set(a) | set(b))
    idx = {c: i for i, c in enumerate(cats)}
    k, n = len(cats), len(a)
    obs = [[0.0] * k for _ in range(k)]
    for x, y in zip(a, b):
        obs[idx[x]][idx[y]] += 1 / n
    row = [sum(r) for r in obs]
    col = [sum(obs[i][j] for i in range(k)) for j in range(k)]

    def w(i: int, j: int) -> float:  # disagreement weight
        if weights is None:
            return float(i != j)
        d = abs(i - j) / (k - 1 if k > 1 else 1)
        return d if weights == "linear" else d * d

    observed = sum(w(i, j) * obs[i][j] for i in range(k) for j in range(k))
    expected = sum(w(i, j) * row[i] * col[j] for i in range(k) for j in range(k))
    if expected == 0:
        return 1.0 if observed == 0 else 0.0
    return 1 - observed / expected
