from src.index import approx_tokens, build_vectors, chunk_card

RAW = {"id": "org/m", "pipeline_tag": "token-classification", "tags": [], "downloads": 3,
       "cardData": {"language": ["mr"], "license": "mit"},
       "siblings": [{"rfilename": "model.safetensors", "size": 100_000_000}]}


def fake_embed(texts):
    return [[0.0, 1.0] for _ in texts]


def test_chunks_follow_headings_and_respect_the_token_limit():
    card = "# Intro\n" + "word " * 100 + "\n## Usage\n" + "token " * 1000
    chunks = chunk_card(card, max_tokens=100)
    assert {name for name, _ in chunks} == {"intro", "usage"}
    assert all(approx_tokens(text) <= 100 for _, text in chunks)
    assert len([c for c in chunks if c[0] == "usage"]) > 1


def test_text_before_first_heading_is_kept():
    assert chunk_card("Preamble text.\n# H\nBody")[0] == ("overview", "Preamble text.")


def test_vectors_carry_identical_model_metadata_plus_section_and_text():
    card = "# Overview\n" + "A Marathi named entity model trained on news. " * 12 + "\n# Usage\n" + "Use it like so. " * 20
    vecs = build_vectors(RAW, card, fake_embed)
    assert len(vecs) == 2 and [v["id"] for v in vecs] == ["org/m::0", "org/m::1"]
    shared = [{k: v for k, v in x["metadata"].items() if k not in ("section", "text")} for x in vecs]
    assert shared[0] == shared[1] and shared[0]["doc_quality"] == "full"


def test_sparse_card_gets_one_fallback_chunk_and_minimal_flag():
    vecs = build_vectors(RAW, "# Model\nMore information needed", fake_embed)
    assert len(vecs) == 1 and vecs[0]["metadata"]["doc_quality"] == "minimal"
    assert vecs[0]["metadata"]["section"] == "metadata" and "org/m" in vecs[0]["metadata"]["text"]


def test_no_null_metadata_values():
    vecs = build_vectors({"id": "x/y", "siblings": []}, "", fake_embed)  # no pipeline_tag
    assert all(v is not None for v in vecs[0]["metadata"].values())


def test_boilerplate_and_empty_sections_are_dropped_and_chunks_capped():
    from src.index import select_chunks

    chunks = [("overview", "A Marathi NER model trained on news and social media posts. " * 3),
              ("training hyperparameters", "learning_rate: 2e-05 " * 20),
              ("model description", "More information needed"),
              ("citation", "@article{x, title={y}} " * 10),
              ("intended uses & limitations", "Use it for named entity recognition in Marathi text. " * 3),
              ("training and evaluation data", "The model was trained on the L3Cube MahaNER corpus. " * 3),
              ("framework versions", "Transformers 4.30 " * 10),
              ("usage", "Pass a sentence to the pipeline and read the predicted entities. " * 3),
              ("extra", "Some other informative paragraph about evaluation results. " * 3)]
    kept = select_chunks(chunks, max_n=4)
    assert [s for s, _ in kept] == ["overview", "intended uses & limitations", "training and evaluation data", "usage"]
    assert len(select_chunks(chunks, max_n=2)) == 2                       # cap, in document order
    assert select_chunks([("citation", "x" * 200)]) == [] and select_chunks([]) == []


def test_every_vector_of_a_card_with_only_boilerplate_falls_back_to_the_metadata_chunk():
    card = "# Training hyperparameters\n" + "lr 1e-5 and so on and so forth. " * 30 + "\n# Framework versions\n" + "Transformers 4.3 " * 30
    vecs = build_vectors(RAW, card, fake_embed)
    assert len(vecs) == 1 and vecs[0]["metadata"]["section"] == "metadata"


def test_a_card_with_many_good_sections_yields_at_most_the_configured_number_of_chunks():
    from src.config import CFG

    card = "".join(f"# Part {i}\n" + f"Informative paragraph number {i} about this model and what it does well. " * 8 + "\n" for i in range(12))
    vecs = build_vectors(RAW, card, fake_embed)
    assert len(vecs) == CFG["embedding"]["max_chunks_per_model"]
