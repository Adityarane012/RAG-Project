"""Run every system on every evaluation query and write the results table (D11, D19, D21).

    python -m eval.run_eval [--systems ours,naive,keyword,hf_basic,hf_licensed] [--tag v1] [--label 40]

Fairness rules enforced here:
  * every system is judged against the SAME constraints: one cached `extract_constraints` parse per query;
  * every recommended model is judged by `verify.verify` with that parse (one definition of "violation");
  * ours only "recommends" models that are not ❌ (it shows ✅ and ⚠️ ones); a baseline recommends all of its
    top-5. Systems that abstain or ask a question recommend nothing, so each result also reports how many queries
    were answered: a low violation rate with few answers is not a win.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import statistics
import subprocess
import time
from collections import Counter, defaultdict
from pathlib import Path

from eval.metrics import load_queries
from src.verify import FAIL, PASS, UNKNOWN, overall, verify

SYSTEMS = ("ours", "naive", "keyword", "hf_basic", "hf_licensed")
GRAPH_SYSTEMS = {"ours", "naive", "keyword"}
TOP_K = 5


def _row(model_id: str, meta: dict, constraints: dict) -> dict:
    table = verify(meta, constraints)
    return {"model_id": model_id, "table": table, "overall": overall(table),
            "task": meta.get("task"), "languages": meta.get("languages", [])[:8]}


def outcome_from_state(system: str, state: dict, constraints: dict, k: int = TOP_K) -> dict:
    """What a graph run recommended. Ours recommends only models that did not fail; baselines their whole top-k."""
    results = state.get("results") or []
    if system == "ours":
        if state.get("outcome") != "answer":
            results = []                                  # clarify / relax / abstain: nothing is recommended
        else:
            results = [r for r in results if r["overall"] != FAIL]
    top = [{"model_id": r["model_id"], "table": r["table"], "overall": r["overall"], "task": r["meta"].get("task"),
            "languages": r["meta"].get("languages", [])[:8]} for r in results[:k]]
    return {"outcome": state.get("outcome", "answer"), "top": top, "fully_verified": state.get("fully_verified"),
            "question": (state.get("question") or {}).get("field"), "offer": (state.get("relax_offer") or {}).get("field"),
            "explain_error": state.get("explain_error")}


def outcome_from_hub(ids: list[str], constraints: dict, resolve, k: int = TOP_K) -> dict:
    """What the Hub's own filters returned, judged with our rules. A model whose metadata cannot be resolved is
    counted (as `unresolved`) but cannot be judged."""
    top, unresolved = [], 0
    for mid in ids[:k]:
        meta = resolve(mid)
        if meta is None:
            unresolved += 1
            continue
        top.append(_row(mid, meta, constraints))
    return {"outcome": "answer", "top": top, "unresolved": unresolved}


# ---- metrics ------------------------------------------------------------------------------------------------------

def _pct(n, d):
    return round(100 * n / d, 1) if d else None


def system_metrics(per_query: list[dict]) -> dict:
    """Metrics for one system over a set of queries. `per_query`: [{"outcome", "top", "latency_s"}]."""
    recs = [m for q in per_query for m in q["top"]]
    n = len(per_query)
    answered = sum(1 for q in per_query if q["top"])
    by_constraint: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for m in recs:
        for key, verdict in m["table"].items():
            by_constraint[key][1] += 1
            by_constraint[key][0] += verdict == FAIL
    lat = sorted(q["latency_s"] for q in per_query if q.get("latency_s") is not None)
    return {
        "queries": n,
        "answered_pct": _pct(answered, n),
        "recommendations": len(recs),
        "violation_pct": _pct(sum(m["overall"] == FAIL for m in recs), len(recs)),
        "unknown_pct": _pct(sum(m["overall"] == UNKNOWN for m in recs), len(recs)),
        "fully_verified_pct": _pct(sum(m["overall"] == PASS for m in recs), len(recs)),
        "violation_by_constraint_pct": {k: _pct(v[0], v[1]) for k, v in sorted(by_constraint.items())},
        "latency_median_s": round(statistics.median(lat), 2) if lat else None,
        "latency_p95_s": round(lat[min(len(lat) - 1, int(0.95 * len(lat)))], 2) if lat else None,
    }


def feasibility(records: list[dict], constraints: dict) -> dict:
    """How many models in the corpus could answer this request: with every constraint passing, and with none failing."""
    verdicts = [overall(verify(r, constraints)) for r in records]
    return {"full_pass": sum(v == PASS for v in verdicts), "not_fail": sum(v != FAIL for v in verdicts)}


def evaluate(queries: list[dict], parsed: dict, outcomes: dict, records: list[dict] | None = None) -> dict:
    """All metrics. `outcomes[system][query_id]` -> outcome dict (with latency_s)."""
    by_kind = defaultdict(list)
    for q in queries:
        by_kind[q["kind"]].append(q)
    out: dict = {"systems": {}, "no_constraint_queries": [], "extraction": {}}
    for q in queries:
        c = parsed[q["id"]]
        if not any([c.get("task"), c.get("langs"), c.get("max_size_mb"), c.get("size_word"), c.get("commercial"), c.get("modifiable")]):
            out["no_constraint_queries"].append(q["id"])        # these make violation trivially zero (E-MET-3)
    for system, per_q in outcomes.items():
        s = {}
        for kind, qs in by_kind.items():
            rows = [{**per_q[q["id"]]} for q in qs if q["id"] in per_q]
            s[kind] = system_metrics(rows)
        normal = [per_q[q["id"]] for q in by_kind["normal"] if q["id"] in per_q]
        s["normal"]["by_task"] = {}
        for task in sorted({parsed[q["id"]].get("task") or "none" for q in by_kind["normal"]}):
            sub = [per_q[q["id"]] for q in by_kind["normal"] if (parsed[q["id"]].get("task") or "none") == task and q["id"] in per_q]
            s["normal"]["by_task"][task] = system_metrics(sub)
        indic = {"hi", "mr", "bn", "ta", "te", "gu", "kn", "ml", "pa", "ur"}
        for label, pred in (("indic", lambda c: bool(indic & set(c.get("langs") or []))), ("non_indic", lambda c: not (indic & set(c.get("langs") or [])))):
            sub = [per_q[q["id"]] for q in by_kind["normal"] if pred(parsed[q["id"]]) and q["id"] in per_q]
            s["normal"].setdefault("by_language_group", {})[label] = system_metrics(sub)
        s["outcomes"] = {kind: dict(Counter(per_q[q["id"]]["outcome"] for q in qs if q["id"] in per_q)) for kind, qs in by_kind.items()}
        if system == "ours":
            vague = [per_q[q["id"]] for q in by_kind["vague"] if q["id"] in per_q]
            s["clarification_rate_pct"] = _pct(sum(o["outcome"] == "clarify" for o in vague), len(vague))
            imp = [per_q[q["id"]] for q in by_kind["impossible"] if q["id"] in per_q]
            s["abstention_pct"] = _pct(sum(o["outcome"] in ("abstain", "relax") for o in imp), len(imp))
            s["impossible_shown_with_banner_pct"] = _pct(sum(o["outcome"] == "answer" and not o.get("fully_verified") for o in imp), len(imp))
            s["impossible_shown_as_verified_pct"] = _pct(sum(o["outcome"] == "answer" and bool(o.get("fully_verified")) for o in imp), len(imp))
        out["systems"][system] = s
    if records is not None:
        out["feasibility"] = {q["id"]: feasibility(records, parsed[q["id"]]) for q in queries if q["kind"] in ("normal", "impossible")}
        # "Impossible" cannot be proved (a model with unknown size/language never FAILS), so the abstention metric is
        # defined on what the corpus can show: queries for which NO model fully passes. There a system must not claim
        # a verified answer (false assurance) and should not recommend violators.
        none_ids = [qid for qid, f in out["feasibility"].items() if f["full_pass"] == 0]
        sl = {"queries": len(none_ids), "ids": none_ids, "systems": {}}
        for system, per_q in outcomes.items():
            rows = [per_q[i] for i in none_ids if i in per_q]
            m = system_metrics(rows)
            sl["systems"][system] = {"violation_pct": m["violation_pct"], "unknown_pct": m["unknown_pct"], "answered_pct": m["answered_pct"],
                                     "claimed_fully_verified": sum(bool(o.get("fully_verified")) and o["outcome"] == "answer" for o in rows),
                                     "banner": sum((not o.get("fully_verified")) and o["outcome"] == "answer" for o in rows),
                                     "abstained_or_relaxed": sum(o["outcome"] in ("abstain", "relax") for o in rows)}
        out["no_verified_slice"] = sl
    return out


def render_markdown(result: dict, meta: dict) -> str:
    L = [f"# Evaluation results ({meta['tag']})", "",
         f"- date {meta['date']} · git `{meta['git']}` · config sha256 `{meta['config_sha'][:12]}` · LLM `{meta['llm']}` · "
         f"vector store `{meta['store']}` · embeddings `{meta['embedding']}` · reranker `{meta['reranker']}`",
         f"- queries: {meta['n_queries']} ({meta['kinds']}); single author, written before any retrieval experiment (D11 deviation)",
         f"- queries whose parsed constraints are empty (violation is trivially 0 for them): {len(result['no_constraint_queries'])}", "",
         "## Normal queries (75): recommendations judged with verify()", "",
         "| System | Answered % | Recs | Violation % | Unknown % | Fully verified % | Median s | p95 s |", "|---|---|---|---|---|---|---|---|"]
    for sys_, s in result["systems"].items():
        m = s["normal"]
        L.append(f"| {sys_} | {m['answered_pct']} | {m['recommendations']} | {m['violation_pct']} | {m['unknown_pct']} | {m['fully_verified_pct']} | {m['latency_median_s']} | {m['latency_p95_s']} |")
    L += ["", "### Violations by constraint (% of recommended models failing that constraint)", ""]
    keys = sorted({k for s in result["systems"].values() for k in s["normal"]["violation_by_constraint_pct"]})
    L += ["| System | " + " | ".join(keys) + " |", "|---|" + "---|" * len(keys)]
    for sys_, s in result["systems"].items():
        v = s["normal"]["violation_by_constraint_pct"]
        L.append(f"| {sys_} | " + " | ".join(str(v.get(k, "-")) for k in keys) + " |")
    L += ["", "### By task and language group (violation % / answered %)", ""]
    for sys_, s in result["systems"].items():
        parts = [f"{t}: {m['violation_pct']}/{m['answered_pct']}" for t, m in s["normal"]["by_task"].items()]
        parts += [f"{g}: {m['violation_pct']}/{m['answered_pct']}" for g, m in s["normal"]["by_language_group"].items()]
        L.append(f"- **{sys_}**: " + " · ".join(parts))
    ours = result["systems"].get("ours")
    if ours:
        L += ["", "## Behaviour of the full system", "",
              f"- vague queries (15): asked a clarifying question on **{ours['clarification_rate_pct']}%**; outcomes {ours['outcomes'].get('vague')}",
              f"- impossible queries (10): abstained or offered a relaxation on **{ours['abstention_pct']}%**; "
              f"shown with the 'no model fully verified' banner on {ours['impossible_shown_with_banner_pct']}%; "
              f"shown as fully verified on {ours['impossible_shown_as_verified_pct']}%; outcomes {ours['outcomes'].get('impossible')}"]
    if "feasibility" in result:
        imp = [(qid, f) for qid, f in result["feasibility"].items() if qid in meta["impossible_ids"]]
        L += ["", "### Impossible queries: models in the corpus that could answer them", "",
              "| query | full pass | not failing (pass or unknown) |", "|---|---|---|"]
        for qid, f in imp:
            L.append(f"| {qid} | {f['full_pass']} | {f['not_fail']} |")
        zero = sum(1 for _, f in imp if f["not_fail"] == 0)
        L.append(f"\n{zero}/{len(imp)} are verifiably impossible (no model passes or is unknown).")
    if "no_verified_slice" in result:
        sl = result["no_verified_slice"]
        L += ["", f"### Queries with no fully verified model in the corpus ({sl['queries']}): false assurance and violations", "",
              "| System | answered % | violation % | unknown % | claimed fully verified | shown with banner | abstained / relaxed |", "|---|---|---|---|---|---|---|"]
        for sys_, m in sl["systems"].items():
            L.append(f"| {sys_} | {m['answered_pct']} | {m['violation_pct']} | {m['unknown_pct']} | {m['claimed_fully_verified']} | {m['banner']} | {m['abstained_or_relaxed']} |")
    L += ["", "## Vague and impossible queries: baselines (they never ask or abstain)", ""]
    for kind in ("vague", "impossible"):
        for sys_, s in result["systems"].items():
            m = s[kind]
            L.append(f"- {kind} · {sys_}: answered {m['answered_pct']}%, violation {m['violation_pct']}%, unknown {m['unknown_pct']}%")
    return "\n".join(L) + "\n"


# ---- run ----------------------------------------------------------------------------------------------------------

def git_sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip() or "unknown"
    except OSError:
        return "unknown"


def config_sha() -> str:
    return hashlib.sha256((Path(__file__).resolve().parent.parent / "config.yaml").read_bytes()).hexdigest()


def sample_for_labelling(queries: list[dict], parsed: dict, n: int, seed: int = 2026) -> list[dict]:
    """A stratified, reproducible sample of normal queries (equal share per parsed task)."""
    by_task = defaultdict(list)
    for q in queries:
        if q["kind"] == "normal":
            by_task[parsed[q["id"]].get("task") or "none"].append(q)
    rng = random.Random(seed)
    pools = {}
    for task in sorted(by_task):
        pools[task] = by_task[task][:]
        rng.shuffle(pools[task])
    picked = []
    while len(picked) < n and any(pools.values()):          # round-robin: equal share per task, remainder filled evenly
        for task in sorted(pools):
            if pools[task] and len(picked) < n:
                picked.append(pools[task].pop())
    return sorted(picked, key=lambda q: q["id"])


def export_label_sheet(sample: list[dict], parsed: dict, outcomes: dict, systems: list[str], snippet, directory: Path) -> dict:
    """Blind relevance sheet: the union of every system's top-k per query, shuffled, without system names.
    A separate key file maps each pair to the systems that returned it."""
    directory.mkdir(parents=True, exist_ok=True)
    rng = random.Random(7)
    rows, key = [], {}
    for q in sample:
        pairs: dict[str, list[str]] = {}
        for sysname in systems:
            for m in outcomes.get(sysname, {}).get(q["id"], {}).get("top", []):
                pairs.setdefault(m["model_id"], []).append(sysname)
        ids = sorted(pairs)
        rng.shuffle(ids)
        for mid in ids:
            pid = f"{q['id']}|{mid}"
            rows.append({"pair_id": pid, "query_id": q["id"], "request": q["query"], "soft_preference": parsed[q["id"]].get("soft_query", ""),
                         "model_id": mid, "snippet": snippet(mid), "grade_0_1_2": ""})
            key[pid] = pairs[mid]
    with open(directory / "relevance_sheet.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["pair_id", "query_id", "request", "soft_preference", "model_id", "snippet", "grade_0_1_2"])
        w.writeheader()
        w.writerows(rows)
    (directory / "_key.json").write_text(json.dumps(key, indent=1, ensure_ascii=False), encoding="utf-8")
    return {"queries": len(sample), "pairs": len(rows)}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--systems", default=",".join(SYSTEMS))
    ap.add_argument("--tag", default="v1")
    ap.add_argument("--label", type=int, default=0, help="export a blind relevance sheet for N sampled queries")
    ap.add_argument("--limit", type=int, help="only the first N queries (smoke test)")
    args = ap.parse_args(argv)

    from huggingface_hub import HfApi

    from src import baselines, ingest, llm
    from src.config import CFG
    from src.index import prepare_all, store_backend
    from src.pipeline import build_pipeline, vector_fetch  # noqa: F401
    from src.snapshot import collect_records

    systems = args.systems.split(",")
    queries = load_queries("eval/queries.jsonl")[: args.limit]
    parsed, bad = {}, []
    for q in queries:
        try:
            parsed[q["id"]] = llm.extract_constraints(q["query"])
        except Exception as e:                                         # LLM down or not JSON: the query is skipped, visibly
            bad.append((q["id"], str(e)[:80]))
    queries = [q for q in queries if q["id"] in parsed]
    print(f"{len(queries)} queries parsed; extraction failures: {bad or 'none'}")

    graphs = {}
    shared_kw = baselines.KeywordIndex(prepare_all()) if "keyword" in systems else None
    for s in systems:
        if s in GRAPH_SYSTEMS:
            graphs[s] = build_pipeline(s, explain=False, keyword=shared_kw, extract=lambda text, _p={q["query"]: parsed[q["id"]] for q in queries}: dict(_p[text]))
    api = HfApi()
    extra = Path("data/raw_extra")
    extra.mkdir(parents=True, exist_ok=True)

    def resolve(mid):
        return baselines.resolve_metadata(mid, (ingest.RAW_DIR,), extra, fetch=lambda i, d: _fetch_into(i, d))

    outcomes: dict = {s: {} for s in systems}
    for n, q in enumerate(queries, 1):
        c = parsed[q["id"]]
        for s in systems:
            t0 = time.perf_counter()
            if s in GRAPH_SYSTEMS:
                state = graphs[s].invoke({"query": q["query"]})
                o = outcome_from_state(s, state, c)
            else:
                ids = baselines.hub_candidates(api, c, variant=s.split("_", 1)[1])
                o = outcome_from_hub(ids, c, resolve)
            o["latency_s"] = round(time.perf_counter() - t0, 3)
            outcomes[s][q["id"]] = o
        if n % 10 == 0:
            print(f"  {n}/{len(queries)} queries", flush=True)

    records = collect_records()
    result = evaluate(queries, parsed, outcomes, records)
    meta = {"tag": args.tag, "date": time.strftime("%Y-%m-%d"), "git": git_sha(), "config_sha": config_sha(),
            "llm": f"{CFG['llm']['groq_model']} (reasoning_effort={CFG['llm'].get('reasoning_effort')})",
            "store": store_backend(), "embedding": f"{CFG['embedding']['backend']}:{CFG['embedding']['model']}",
            "reranker": CFG["retrieval"]["reranker"], "n_queries": len(queries),
            "kinds": dict(Counter(q["kind"] for q in queries)), "impossible_ids": [q["id"] for q in queries if q["kind"] == "impossible"]}
    out = Path("eval/results")
    out.mkdir(parents=True, exist_ok=True)
    (out / f"raw-{args.tag}.json").write_text(json.dumps({"meta": meta, "parsed": parsed, "outcomes": outcomes, "result": result}, indent=1, ensure_ascii=False), encoding="utf-8")
    (out / f"results-{args.tag}.md").write_text(render_markdown(result, meta), encoding="utf-8")
    print(render_markdown(result, meta))
    if args.label:
        def snippet(mid):
            from src.clean import clean_card
            for d in (ingest.RAW_DIR, extra):
                p = d / f"{mid.replace('/', '__')}.md"
                if p.exists():
                    return " ".join(clean_card(p.read_text(encoding='utf-8')).split())[:400]
            return "(no card text available)"
        sample = sample_for_labelling(queries, parsed, args.label)
        print("label sheet:", export_label_sheet(sample, parsed, outcomes, [s for s in ("ours", "naive", "keyword", "hf_licensed") if s in systems], snippet, Path("eval/labels")))


def _fetch_into(model_id: str, directory: Path) -> None:
    from src import ingest
    old = ingest.RAW_DIR
    ingest.RAW_DIR = directory
    try:
        ingest.fetch_raw(model_id)
    finally:
        ingest.RAW_DIR = old


if __name__ == "__main__":
    main()
