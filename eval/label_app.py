"""Blind relevance labelling.   streamlit run eval/label_app.py

Shows one (request, model) pair at a time, never which system returned it. Every click is appended to
`eval/labels/labels_pass1.csv` straight away (a closed tab loses nothing). Pass 2 is a repeat over 15 random queries:
do it at least a day after pass 1, and do NOT open pass 1's file in between (this page hides your earlier grades).

Do not open `eval/labels/_key.json`: it says which system returned which model and would unblind the labelling.
"""

from __future__ import annotations

import csv
import os
import random
import time
from pathlib import Path

import streamlit as st

from eval.relevance_report import load_labels

DIR = Path(os.environ.get("LABEL_DIR", "eval/labels"))
RETEST_QUERIES = 15
RUBRIC = {2: "Clearly suits the request (the card says so, or the evidence is explicit)",
          1: "Plausible: right kind of model, but nothing on the card speaks to what was asked",
          0: "Does not suit the request"}


def load_sheet() -> list[dict]:
    with open(DIR / "relevance_sheet.csv", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def retest_queries(rows: list[dict]) -> list[str]:
    ids = sorted({r["query_id"] for r in rows})
    return sorted(random.Random(99).sample(ids, min(RETEST_QUERIES, len(ids))))


def save(path: Path, pair_id: str, grade: int | None) -> None:
    new = not path.exists()
    with open(path, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["pair_id", "grade", "ts"])
        w.writerow([pair_id, "" if grade is None else grade, int(time.time())])


def main() -> None:
    st.set_page_config(page_title="Relevance labelling", layout="centered")
    rows = load_sheet()
    mode = st.sidebar.radio("Pass", ["Pass 1: all queries", f"Pass 2: repeat on {RETEST_QUERIES} queries (a day later)"])
    second = mode.startswith("Pass 2")
    path = DIR / ("labels_pass2.csv" if second else "labels_pass1.csv")
    items = [r for r in rows if not second or r["query_id"] in set(retest_queries(rows))]
    labels = load_labels(path)
    todo = [r for r in items if r["pair_id"] not in labels]

    st.sidebar.progress(len(labels.keys() & {r["pair_id"] for r in items}) / max(len(items), 1))
    st.sidebar.write(f"{len(items) - len(todo)} of {len(items)} labelled")
    st.sidebar.caption("Grade the **purpose** of the request. Size and license are checked automatically: ignore them.")
    last = st.session_state.get("last")
    if last and st.sidebar.button("Undo last grade"):
        save(path, last, None)
        st.session_state["last"] = None
        st.rerun()

    if not todo:
        st.success("Everything in this pass is labelled. Run `python -m eval.relevance_report` for the numbers.")
        return
    r = todo[0]
    queries = sorted({x["query_id"] for x in items})
    st.caption(f"Query {queries.index(r['query_id']) + 1} of {len(queries)}")
    st.subheader("The request")
    st.write(r["request"])
    st.subheader("The model")
    st.write(f"[{r['model_id']}](https://huggingface.co/{r['model_id']})")
    st.text(r["snippet"])
    st.write("How well does this model suit the request?")
    cols = st.columns(3)
    for col, g in zip(cols, (0, 1, 2)):
        if col.button(f"{g}", use_container_width=True, key=f"g{g}-{r['pair_id']}", help=RUBRIC[g]):
            save(path, r["pair_id"], g)
            st.session_state["last"] = r["pair_id"]
            st.rerun()
    st.caption("  \n".join(f"**{g}**  {RUBRIC[g]}" for g in (2, 1, 0)))


main()
