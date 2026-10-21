"""Score explanations for faithfulness.   streamlit run eval/faithfulness_app.py

For each explanation: count its factual claims, then count how many the shown card passages support. A claim the passages
do not state is unsupported even if it is true of the model in general. Every save is appended to
`eval/labels/faithfulness_labels.csv` immediately.
"""

from __future__ import annotations

import csv
import os
import time
from pathlib import Path

import streamlit as st

from eval.faithfulness_report import load

DIR = Path(os.environ.get("LABEL_DIR", "eval/labels"))


def save(item_id: str, claims: int, supported: int, note: str) -> None:
    path = DIR / "faithfulness_labels.csv"
    new = not path.exists()
    with open(path, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["item_id", "claims", "supported", "note", "ts"])
        w.writerow([item_id, claims, supported, note, int(time.time())])


def main() -> None:
    st.set_page_config(page_title="Faithfulness scoring", layout="centered")
    with open(DIR / "faithfulness_sheet.csv", encoding="utf-8", newline="") as f:
        items = list(csv.DictReader(f))
    done = load(DIR / "faithfulness_labels.csv")
    todo = [i for i in items if i["item_id"] not in done]
    st.sidebar.progress(len(done.keys() & {i["item_id"] for i in items}) / max(len(items), 1))
    st.sidebar.write(f"{len(items) - len(todo)} of {len(items)} scored")
    if not todo:
        st.success("All scored. Run `python -m eval.faithfulness_report`.")
        return
    it = todo[0]
    st.subheader("The request")
    st.write(it["request"])
    st.subheader(f"The explanation for {it['model_id']}")
    st.info(it["explanation"])
    st.caption(f"Cited sections: {it['cited_sections']}")
    st.subheader("The card passages the model was given")
    st.text(it["evidence"] or "(no passages)")
    claims = st.number_input("Factual claims in the explanation", min_value=0, max_value=20, value=2, key=f"c-{it['item_id']}")
    supported = st.number_input("... of which the passages above support", min_value=0, max_value=20, value=int(claims), key=f"s-{it['item_id']}")
    note = st.text_input("Which claim was unsupported? (optional)", key=f"n-{it['item_id']}")
    if st.button("Save and next", type="primary", key=f"b-{it['item_id']}"):
        if supported > claims:
            st.error("Supported cannot be more than the number of claims.")
        else:
            save(it["item_id"], int(claims), int(supported), note)
            st.rerun()


main()
