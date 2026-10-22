import csv
import json
from pathlib import Path

from streamlit.testing.v1 import AppTest

from eval.relevance_report import load_labels, per_system, render, retest

KEY = {"q1|a": ["ours", "naive"], "q1|b": ["naive"], "q2|c": ["ours"], "q2|d": ["ours", "naive"], "q3|e": ["naive"]}


def test_labels_file_is_append_only_and_the_last_row_wins_with_undo(tmp_path):
    p = tmp_path / "l.csv"
    p.write_text("pair_id,grade,ts\nq1|a,2,1\nq1|b,1,2\nq1|a,0,3\nq1|b,,4\nq9|x,7,5\n", encoding="utf-8")
    assert load_labels(p) == {"q1|a": 0}                    # a regrade replaces, an empty grade undoes, junk is ignored
    assert load_labels(tmp_path / "missing.csv") == {}


def test_per_system_scores_only_fully_labelled_queries_and_counts_each_system_alike():
    labels = {"q1|a": 2, "q1|b": 0, "q2|c": 1, "q2|d": 1}  # q3 is not labelled, so it is excluded for everyone
    s = per_system(labels, KEY)
    assert s["_labelled_queries"] == {"queries": 2, "of": 3}
    assert s["ours"] == {"queries": 2, "models": 3, "mean_grade": round(4 / 3, 3), "queries_with_a_2_pct": 50.0, "graded_1_or_2_pct": 100.0}
    assert s["naive"]["models"] == 3 and s["naive"]["mean_grade"] == 1.0 and "q3" not in str(s)


def test_retest_agreement_is_reported_as_self_consistency():
    a = {"p1": 2, "p2": 0, "p3": 1, "p4": 2}
    b = {"p1": 2, "p2": 2, "p3": 1, "p4": 2, "p9": 0}
    r = retest(a, b)
    assert r["items"] == 4 and r["same_grade_pct"] == 75.0 and r["big_disagreements_0_vs_2"] == 1
    assert retest(a, {}) is None
    md = render(per_system({"q1|a": 2, "q1|b": 1}, KEY), r)
    assert "not inter-annotator agreement" in md and "Test-retest" in md


def make_sheet(tmp_path):
    rows = [{"pair_id": f"q{i}|m{i}", "query_id": f"q{i}", "request": f"request {i}", "soft_preference": "x", "model_id": f"org/m{i}",
             "snippet": f"card of m{i}", "grade_0_1_2": ""} for i in (1, 2)]
    with open(tmp_path / "relevance_sheet.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    (tmp_path / "_key.json").write_text(json.dumps({"q1|m1": ["ours"], "q2|m2": ["naive"]}), encoding="utf-8")


def test_the_labelling_page_saves_every_click_hides_the_system_and_can_undo(tmp_path, monkeypatch):
    make_sheet(tmp_path)
    monkeypatch.setenv("LABEL_DIR", str(tmp_path))
    at = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "eval" / "label_app.py"), default_timeout=20).run()
    assert not at.exception
    text = " ".join(m.value for m in at.markdown) + " ".join(t.value for t in at.text)
    assert "request 1" in text and "card of m1" in text and "ours" not in text and "naive" not in text
    at.button[0].click().run()                               # grade 0 on the first pair
    assert load_labels(tmp_path / "labels_pass1.csv") == {"q1|m1": 0}
    assert "request 2" in " ".join(m.value for m in at.markdown)
    at.sidebar.button[0].click().run()                       # undo
    assert load_labels(tmp_path / "labels_pass1.csv") == {} and "request 1" in " ".join(m.value for m in at.markdown)


def test_faithfulness_summary_counts_claims_and_fully_supported_explanations(tmp_path):
    from eval.faithfulness_report import load as fload, render as frender, summarise
    p = tmp_path / "f.csv"
    p.write_text("item_id,claims,supported,note,ts\na,3,3,,1\nb,2,1,says it is multilingual,2\nc,4,5,,3\nb,2,2,,4\nd,2,1,invented a size,5\n", encoding="utf-8")
    s = summarise(fload(p))                                  # c is invalid (5 > 4) and ignored; the later row for b wins
    assert s["items"] == 3 and s["claims"] == 7 and s["supported"] == 6
    assert s["claims_supported_pct"] == 85.7 and s["explanations_fully_supported_pct"] == 66.7
    assert "invented a size" in frender(s)


def test_the_faithfulness_page_saves_a_score_and_moves_on(tmp_path, monkeypatch):
    from eval.faithfulness_report import load as fload
    with open(tmp_path / "faithfulness_sheet.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["item_id", "request", "model_id", "explanation", "cited_sections", "evidence"])
        w.writeheader()
        for i in (1, 2):
            w.writerow({"item_id": f"q{i}|m{i}", "request": f"request {i}", "model_id": f"org/m{i}", "explanation": f"explanation {i}",
                        "cited_sections": "[]", "evidence": f"evidence {i}"})
    monkeypatch.setenv("LABEL_DIR", str(tmp_path))
    at = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "eval" / "faithfulness_app.py"), default_timeout=20).run()
    assert not at.exception and "request 1" in " ".join(m.value for m in at.markdown)
    at.number_input[0].set_value(3).run()
    at.number_input[1].set_value(2).run()
    at.button[0].click().run()
    assert fload(tmp_path / "faithfulness_labels.csv") == {"q1|m1": {"claims": 3, "supported": 2, "note": ""}}
    assert "request 2" in " ".join(m.value for m in at.markdown)
