from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def test_app_renders_and_explains_when_there_is_no_index_instead_of_crashing(tmp_path, monkeypatch):
    monkeypatch.setenv("INDEX_BACKEND", "local")
    monkeypatch.setenv("LOCAL_INDEX_DIR", str(tmp_path))          # an empty directory: no index built here
    monkeypatch.delenv("REPLAY", raising=False)
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    assert any("not legal" in c.value for c in at.caption)
    assert len(at.tabs) == 2
    at.text_input(key="query").set_value("Marathi NER").run()
    at.button[-1].click().run()  # "Search"
    assert not at.exception
    assert any("Search is unavailable" in e.value for e in at.error)


def render_demo():
    import streamlit as st
    from app import render_state

    table = {"task": "pass", "size": "unknown", "commercial": "pass"}
    st.session_state.setdefault("overrides", {})
    render_state({
        "intent": "We understood: you want a model.", "outcome": "answer",
        "results": [{"model_id": "org/m", "table": table, "overall": "unknown", "notes": ["multilingual, not specific to hi"]}],
        "reports": [{"model_id": "org/m", "try_it": "print(1)", "model_page": "https://huggingface.co/org/m",
                     "rights": {"modifiable": "yes", "notes": ["x"]},
                     "lineage": {"status": "pass", "base_model": "xlmr", "other_finetunes": 3},
                     "memory": {"status": "pass", "reference_gpu_gb": 16,
                                "methods": {"inference": {"gb": 0.5, "fits": "pass"}}},
                     "task_guide": "https://example.com"}],
        "explanations": [{"model_id": "org/m", "text": "Explained."}],
    })


def test_result_rendering_shows_table_notes_and_panels():
    at = AppTest.from_function(render_demo, default_timeout=30).run()
    assert not at.exception
    assert [e.label for e in at.expander] == ["Try it", "Build on it"]
    assert any("multilingual" in c.value for c in at.caption)


def render_clarify_langs():
    from app import render_state

    render_state({"intent": "We understood: you want a model.", "outcome": "clarify",
                  "question": {"field": "langs", "question": "Which languages should it translate between?", "options": {}}})


def test_free_form_question_gets_a_language_picker():
    at = AppTest.from_function(render_clarify_langs, default_timeout=30).run()
    assert not at.exception
    assert at.multiselect(key="clarify-langs") is not None
    assert at.button[0].disabled  # needs two languages before Continue
    at.multiselect(key="clarify-langs").set_value(["hi", "mr"]).run()
    assert not at.button[0].disabled


def render_unverified():
    from app import render_state

    render_state({"intent": "x", "outcome": "answer", "fully_verified": False,
                  "results": [{"model_id": "org/m", "table": {"size": "unknown"}, "overall": "unknown", "notes": []}],
                  "reports": [], "explanations": []})


def test_banner_when_nothing_is_fully_verified():
    at = AppTest.from_function(render_unverified, default_timeout=30).run()
    assert not at.exception
    assert any("No model fully verified" in w.value for w in at.warning)
    assert len(at.table) == 1  # the ⚠️ table is still shown beneath the banner


def test_replay_mode_serves_a_recorded_run_with_no_live_services(tmp_path, monkeypatch):
    import json

    from src.replay import run_key

    state = {"intent": "We understood: recorded.", "outcome": "answer", "fully_verified": True,
             "results": [{"model_id": "org/recorded", "table": {"size": "pass"}, "overall": "pass", "notes": []}],
             "reports": [], "explanations": []}
    inp = {"query": "Marathi NER"}
    (tmp_path / f"{run_key(inp)}.json").write_text(json.dumps({"input": inp, "state": state}), encoding="utf-8")
    monkeypatch.setenv("REPLAY", "1")
    monkeypatch.setenv("REPLAY_DIR", str(tmp_path))
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert any("Replay mode" in c.value for c in at.caption)
    at.text_input(key="query").set_value("Marathi NER").run()
    at.button[-1].click().run()
    assert not at.exception
    assert any("recorded" in i.value for i in at.info)
    assert any("org/recorded" in m.value for m in at.markdown)


def test_replay_mode_explains_a_missing_recording(tmp_path, monkeypatch):
    monkeypatch.setenv("REPLAY", "1")
    monkeypatch.setenv("REPLAY_DIR", str(tmp_path))
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.text_input(key="query").set_value("never recorded").run()
    at.button[-1].click().run()
    assert not at.exception
    assert any("RECORD=1" in w.value for w in at.warning)


# ---- intent editor, side-by-side, check-a-model -------------------------------------------------------------------
import json  # noqa: E402

from src.replay import run_key  # noqa: E402


def _answer(model_ids, overall="pass", constraints=None):
    return {"intent": "We understood: you want a model.", "outcome": "answer", "fully_verified": True,
            "constraints": constraints or {"task": "token-classification", "langs": ["mr"], "max_size_mb": 500, "commercial": True},
            "results": [{"model_id": m, "table": {"size": overall, "commercial": overall}, "overall": overall, "notes": []} for m in model_ids],
            "reports": [], "explanations": []}


def _record(tmp_path, inp, state, variant="ours"):
    (tmp_path / f"{run_key(inp, variant)}.json").write_text(json.dumps({"input": inp, "state": state}), encoding="utf-8")


def test_editing_the_parsed_intent_sends_validated_overrides(tmp_path, monkeypatch):
    inp = {"query": "Marathi NER"}
    _record(tmp_path, inp, _answer(["org/m"]))
    monkeypatch.setenv("REPLAY", "1")
    monkeypatch.setenv("REPLAY_DIR", str(tmp_path))
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.text_input(key="query").set_value("Marathi NER").run()
    at.button[-1].click().run()
    assert not at.exception and at.selectbox(key="edit-task").value == "token-classification"      # the editor shows what was parsed
    assert at.multiselect(key="edit-langs").value == ["mr"] and at.number_input(key="edit-size").value == 500
    assert at.checkbox(key="edit-comm").value is True and at.checkbox(key="edit-mod").value is False
    at.selectbox(key="edit-task").set_value("translation")
    at.number_input(key="edit-size").set_value(0)
    at.button(key="edit-go").click().run()
    assert at.session_state["overrides"] == {"task": "translation", "langs": ["mr"], "max_size_mb": None, "size_word": None,
                                             "commercial": True, "modifiable": None}
    assert any("No recording" in w.value for w in at.warning)      # a replay has no recording for the edited request


def test_side_by_side_shows_ours_without_failures_and_naive_with_them(tmp_path, monkeypatch):
    inp = {"query": "Marathi NER"}
    ours = _answer(["good/model", "bad/model"], "pass")
    ours["results"][1].update(overall="fail", table={"size": "fail", "commercial": "pass"})
    naive = _answer(["bad/model", "good/model"], "pass")
    naive["results"][0].update(overall="fail", table={"size": "fail", "commercial": "pass"})
    _record(tmp_path, inp, ours)
    _record(tmp_path, inp, naive, variant="naive")
    monkeypatch.setenv("REPLAY", "1")
    monkeypatch.setenv("REPLAY_DIR", str(tmp_path))
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.text_input(key="query").set_value("Marathi NER").run()
    at.checkbox(key="compare").check().run()
    at.button[-1].click().run()
    assert not at.exception
    md = " ".join(m.value for m in at.markdown)
    assert "Ours (filters + verification)" in md and "Naive RAG (same index" in md
    assert md.count("[bad/model]") == 1 and md.count("[good/model]") == 2    # ours omits the failing model; naive shows it
    assert any("Naive RAG recommended 1 model(s) that fail" in c.value for c in at.caption)


def test_check_a_model_tab_judges_a_real_model_against_requirements(monkeypatch):
    from pathlib import Path

    monkeypatch.setenv("RAW_DIR", str(Path(__file__).resolve().parent / "fixtures" / "hub"))
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.text_input(key="check_id").set_value("facebook/nllb-200-distilled-600M").run()
    at.checkbox(key="check-comm").check().run()
    assert not at.exception
    tables = [t.value for t in at.table]
    assert any("❌ fail" in str(t.to_dict()) for t in tables)
    assert any("Commercial use" in str(t.to_dict()) and "no" in str(t.to_dict()) for t in tables)
    at.text_input(key="check_id").set_value("nobody/nothing").run()
    assert any("not in our snapshot" in w.value for w in at.warning)


def test_glossary_and_legend_are_present():
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert any(e.label == "Glossary" for e in at.expander)
