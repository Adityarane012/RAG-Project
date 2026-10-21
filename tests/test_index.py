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
