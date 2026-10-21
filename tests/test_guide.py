import pytest

from src.guide import (EXAMPLE_QUERIES, TASK_GUIDES, TASK_LABELS, clarifying_question, describe_intent,
                       relaxation_offer, try_it_snippet)

TASKS = list(TASK_LABELS)


def test_vague_query_gets_one_task_question_with_options():
    q = clarifying_question({"task": None, "langs": ["hi"]})
    assert q["field"] == "task" and set(q["options"]) == set(TASKS)


def test_translation_needs_two_languages_and_complete_queries_need_nothing():
    assert clarifying_question({"task": "translation", "langs": ["hi"]})["field"] == "langs"
    assert clarifying_question({"task": "translation", "langs": ["hi", "mr"]}) is None
    assert clarifying_question({"task": "token-classification", "langs": []}) is None


def test_intent_in_plain_words_shows_size_word_mapping():
    text = describe_intent({"task": "text-classification", "langs": ["hi"], "size_word": "small", "commercial": True})
    assert "Hindi" in text and "500 MB" in text and '"small"' in text and "commercially" in text
    assert "from Hindi to Marathi" in describe_intent({"task": "translation", "direction": ["hi", "mr"]})


def test_relaxation_order_size_then_rights_never_task_or_language():
    assert relaxation_offer({"max_size_mb": 300})["new_value"] == 500
    assert relaxation_offer({"size_word": "small"})["new_value"] == 2000
    assert relaxation_offer({"max_size_mb": 5000, "modifiable": True})["field"] == "modifiable"
    assert relaxation_offer({"commercial": True})["field"] == "commercial"
    assert relaxation_offer({"task": "translation", "langs": ["hi", "mr"]}) is None


@pytest.mark.parametrize("task", TASKS)
def test_try_it_snippets_are_valid_python_for_every_task(task):
    code = try_it_snippet("org/some-model.v2", task)
    compile(code, "<snippet>", "exec")
    assert "org/some-model.v2" in code
    assert ("sentence_transformers" in code) == (task == "sentence-similarity")


@pytest.mark.parametrize("bad", ['x"; import os #', "a b", "a/b/c", "", "a/\nb", "org/m\n", "org/m\r\n"])
def test_try_it_rejects_ids_that_could_inject_code(bad):
    with pytest.raises(ValueError):
        try_it_snippet(bad, "translation")


def test_one_guide_per_task_and_example_queries():
    assert set(TASK_GUIDES) == set(TASKS)
    assert 4 <= len(EXAMPLE_QUERIES) <= 5


def test_direction_alone_is_enough_for_translation():
    assert clarifying_question({"task": "translation", "langs": [], "direction": ["hi", "mr"]}) is None
