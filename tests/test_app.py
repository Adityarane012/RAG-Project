from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def test_app_renders_and_degrades_gracefully_when_pipeline_is_not_wired():
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    assert any("not legal" in c.value for c in at.caption)
    assert len(at.tabs) == 2
    at.text_input(key="query").set_value("Marathi NER").run()
    at.button[-1].click().run()  # "Search"
    assert not at.exception
    assert any("isn't wired up" in i.value for i in at.info)


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
