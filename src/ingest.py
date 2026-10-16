"""Pull model metadata and cards for the 5 in-scope tasks (D5, D6).

Corpus = top ~1,000 models per task by downloads, plus every model in those
tasks tagged with an Indic language. Verify the counts on day 1.
"""

from __future__ import annotations

from src.normalize import INDIC_LANGS

TASKS = (
    "automatic-speech-recognition",
    "translation",
    "text-classification",
    "token-classification",
    "sentence-similarity",
)
TOP_N = 1000


def candidate_ids(api) -> set[str]:
    """Union of top-N per task and all Indic-tagged models per task (D6).

    `api` is a huggingface_hub.HfApi.
    """
    ids: set[str] = set()
    for task in TASKS:
        for m in api.list_models(pipeline_tag=task, sort="downloads", limit=TOP_N):
            ids.add(m.id)
        for lang in INDIC_LANGS:
            for m in api.list_models(pipeline_tag=task, language=lang):
                ids.add(m.id)
    return ids


def main() -> None:
    # TODO day 1: print per-task counts to confirm the ~5-8k estimate, then fetch
    # model_info(files_metadata=True) and the README card for each id into data/raw/.
    raise NotImplementedError


if __name__ == "__main__":
    main()
