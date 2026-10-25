"""Beginner guidance (D13): plain-language intent, clarifying questions, "Try it"
snippets, tooltips and relax-and-retry offers. Nothing here is LLM-generated; the
snippets are templates filled from `model_id` and `task` only."""

from __future__ import annotations

import re

from src.verify import SIZE_WORDS_MB, resolve_max_size_mb

# Task -> plain words for beginners.
TASK_LABELS = {
    "automatic-speech-recognition": "turn speech into text (speech recognition)",
    "translation": "translate text between languages",
    "text-classification": "classify text, e.g. detect sentiment",
    "token-classification": "find names, places and other items in text (NER)",
    "sentence-similarity": "measure how similar two sentences are",
}
# Short labels for the clickable options of the clarifying question.
TASK_OPTIONS = {
    "token-classification": "Find names in text (NER)",
    "text-classification": "Detect sentiment / classify text",
    "automatic-speech-recognition": "Transcribe speech",
    "translation": "Translate text",
    "sentence-similarity": "Compare sentence similarity",
}
LANG_NAMES = {
    "hi": "Hindi", "mr": "Marathi", "bn": "Bengali", "ta": "Tamil", "te": "Telugu",
    "gu": "Gujarati", "kn": "Kannada", "ml": "Malayalam", "pa": "Punjabi", "ur": "Urdu",
    "en": "English", "or": "Odia", "as": "Assamese", "fr": "French", "de": "German", "es": "Spanish",
    "ar": "Arabic", "zh": "Chinese", "ja": "Japanese", "ru": "Russian", "pt": "Portuguese",
    "ko": "Korean", "it": "Italian",
    # Indic and nearby languages that appear as tags in the corpus (data-quality report, 2026-10-21)
    "sat": "Santali", "mai": "Maithili", "bho": "Bhojpuri", "mni": "Manipuri", "brx": "Bodo", "doi": "Dogri",
    "kok": "Konkani", "ne": "Nepali", "sd": "Sindhi", "si": "Sinhala", "sa": "Sanskrit", "ks": "Kashmiri",
    "hne": "Chhattisgarhi", "awa": "Awadhi", "mag": "Magahi",
}
# Words people actually type for a language -> code (used by llm.backstop_constraints).
LANG_BY_NAME = {name.lower(): code for code, name in LANG_NAMES.items()}
LANG_BY_NAME.update({"bangla": "bn", "panjabi": "pa", "oriya": "or", "हिंदी": "hi", "हिन्दी": "hi", "मराठी": "mr",
                     "meitei": "mni", "বাংলা": "bn", "தமிழ்": "ta", "తెలుగు": "te"})

# Modalities and tasks the index does not cover (D5: five tasks). Without this, "image classifier" was read as
# text-classification and the user got text models marked as passing the task check. "segmentation" alone is NOT here:
# word / sentence segmentation is a text task; only the image kinds are. "video" alone is not either (ASR for video lectures).
_OUT_OF_SCOPE = re.compile(
    r"\b(?:images?|photos?|pictures?|ocr|computer vision|object detection|face recognition|pose estimation|depth estimation|"
    r"(?:semantic|instance|panoptic|medical) segmentation|text[- ]to[- ]image|image[- ]to[- ]text|diffusion|"
    r"video (?:classification|generation|understanding|detection))\b", re.I)
SCOPE_SUMMARY = ("speech recognition, translation, text classification (e.g. sentiment), named-entity recognition "
                 "(token classification) and sentence similarity")


def out_of_scope_message(query: str) -> str | None:
    """A plain-words refusal when the request is about something we do not index, else None."""
    if _OUT_OF_SCOPE.search(query or ""):
        return (f"This tool only searches models for {SCOPE_SUMMARY}. Image, vision and OCR models are not covered, "
                "so we show nothing rather than a model for a different task. Try the Hugging Face model search for those.")
    return None


# D13: 4-5 example queries on the start screen, balanced across English and Indic.
EXAMPLE_QUERIES = [
    "Fast English speech recognition under 500 MB",
    "English sentiment analysis for product reviews that I can use commercially",
    "Commercial Hindi to Marathi translation",
    "Speech recognition for Tamil under 1 GB",
    "Sentence embeddings for Bengali that I can modify and sell",
]

TOOLTIPS = {
    "license": "The terms under which the model may be used. We read the license declared "
              "on the model card; this is not legal advice.",
    "commercial": "Whether the declared license allows use in a product you sell or run "
                  "for profit. 'Conditional' means extra terms apply and you must read them.",
    "modifiable": "Whether the declared license lets you fine-tune or change the model. "
                  "Some licenses allow it but keep the result non-commercial.",
    "NER": "Named-entity recognition: finding names of people, places and organisations "
           "in text. The Hub calls this 'token-classification'.",
    "parameters": "The model's learned numbers. More parameters usually means a bigger "
                  "download and more memory.",
    "size": "Download size of the main weight files, in MB (1 MB = 1,000,000 bytes).",
    "LoRA": "A way to fine-tune by training a small add-on instead of the whole model, "
            "which needs far less GPU memory.",
    "unknown": "⚠️ The model card or metadata doesn't say. We don't guess.",
}

# D14: official how-to-fine-tune pages, one per task. Not yet checked against the live
# sites (no network when written); confirm each opens before the demo.
TASK_GUIDES = {
    "automatic-speech-recognition": "https://huggingface.co/docs/transformers/tasks/asr",
    "translation": "https://huggingface.co/docs/transformers/tasks/translation",
    "text-classification": "https://huggingface.co/docs/transformers/tasks/sequence_classification",
    "token-classification": "https://huggingface.co/docs/transformers/tasks/token_classification",
    "sentence-similarity": "https://www.sbert.net/docs/sentence_transformer/training_overview.html",
}


def _lang(code: str) -> str:
    return LANG_NAMES.get(code, code)


def describe_intent(c: dict) -> str:
    """"We understood: ..." in plain words, shown above the results (editable in the UI)."""
    parts = []
    if c.get("task"):
        parts.append(f"you want a model to {TASK_LABELS[c['task']]}")
    else:
        parts.append("you want a model (we're not sure what for yet)")
    if c.get("direction"):
        parts.append(f"from {_lang(c['direction'][0])} to {_lang(c['direction'][1])}")
    elif c.get("langs"):
        parts.append("for " + " and ".join(_lang(x) for x in c["langs"]))
    limit = resolve_max_size_mb(c.get("max_size_mb"), c.get("size_word"))
    if limit is not None:
        word = c.get("size_word")
        label = f"{limit:g} MB"
        parts.append(f"no bigger than {label}" + (f" (we read \"{word}\" as this)" if word and c.get("max_size_mb") is None else ""))
    if c.get("commercial"):
        parts.append("usable commercially")
    if c.get("modifiable"):
        parts.append("that you're allowed to modify")
    return "We understood: " + ", ".join(parts) + "."


def clarifying_question(c: dict) -> dict | None:
    """One question with clickable options when the task or a key constraint is
    missing (D13, D15), else None. Returns {"field", "question", "options"}."""
    if not c.get("task"):
        return {
            "field": "task",
            "question": "What should the model do?",
            "options": dict(TASK_OPTIONS),  # task -> label
        }
    if c["task"] == "translation" and len({*(c.get("langs") or []), *(c.get("direction") or [])}) < 2:
        return {
            "field": "langs",
            "question": "Which languages should it translate between?",
            "options": {},  # free text; the UI offers language pickers
        }
    return None


def relaxation_offer(c: dict) -> dict | None:
    """The one constraint to offer relaxing when nothing passes (D13). Order: size,
    then modifiable, then commercial. Task and languages are never relaxed.
    Returns {"field", "new_value", "message"} or None."""
    limit = resolve_max_size_mb(c.get("max_size_mb"), c.get("size_word"))
    if limit is not None:
        bigger = sorted(v for v in set(SIZE_WORDS_MB.values()) if v > limit)
        if bigger:
            new = bigger[0]
            return {"field": "max_size_mb", "new_value": new,
                    "message": f"No model meets all constraints. Relax the size limit to {new:g} MB?"}
    for right, text in (("modifiable", "the modification requirement"),
                        ("commercial", "the commercial-use requirement")):
        if c.get(right):
            return {"field": right, "new_value": None,
                    "message": f"No model meets all constraints. Drop {text}?"}
    return None


_SAFE_MODEL_ID = re.compile(r"^[\w.\-]+(/[\w.\-]+)?$")


def try_it_snippet(model_id: str, task: str) -> str:
    """A ~5-line runnable snippet from a fixed template (D13). The id comes from the
    Hub, so it is validated before being placed in code."""
    if not _SAFE_MODEL_ID.fullmatch(model_id):
        raise ValueError(f"Refusing to build a snippet for odd model id: {model_id!r}")
    if task == "sentence-similarity":
        # Not a `transformers` pipeline task; these models load with sentence-transformers.
        return (
            "from sentence_transformers import SentenceTransformer, util\n\n"
            f'model = SentenceTransformer("{model_id}")\n'
            'emb = model.encode(["first sentence", "second sentence"])\n'
            "print(util.cos_sim(emb[0], emb[1]))\n"
        )
    template = {
        "automatic-speech-recognition": 'pipe("audio.wav")',
        "translation": 'pipe("Text to translate")',
        "text-classification": 'pipe("Text to classify")',
        "token-classification": 'pipe("Text to scan for names")',
    }
    if task not in template:
        raise ValueError(f"No snippet template for task: {task!r}")
    extra = ', aggregation_strategy="simple"' if task == "token-classification" else ""
    return (
        "from transformers import pipeline\n\n"
        f'pipe = pipeline("{task}", model="{model_id}"{extra})\n'
        f"print({template[task]})\n"
    )


def model_page_url(model_id: str) -> str:
    """Link to the model page, which hosts its inference widget when it has one."""
    return f"https://huggingface.co/{model_id}"
