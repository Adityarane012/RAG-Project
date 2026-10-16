"""LLM access behind one interface, with an on-disk cache (D2, D7).

The LLM only (a) extracts constraints into JSON and (b) writes explanations.
Switching Groq <-> Ollama is the LLM_PROVIDER env var; nothing else changes.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

CACHE_DIR = Path(os.getenv("LLM_CACHE_DIR", ".cache/llm"))

EXTRACT_PROMPT = """Extract the hard constraints and the soft preference from a request \
for a Hugging Face model. Reply with JSON only, using exactly these keys:
  "task": one of "automatic-speech-recognition", "translation", "text-classification",
          "token-classification", "sentence-similarity", or null
  "langs": list of ISO 639-1 codes, or []
  "max_size_mb": number or null
  "commercial": true if commercial use is required, else null
  "soft_query": the remaining soft preference as a short search phrase

Request: {query}"""


def _cache_path(provider: str, model: str, prompt: str) -> Path:
    key = hashlib.sha256(f"{provider}\n{model}\n{prompt}".encode()).hexdigest()
    return CACHE_DIR / f"{key}.json"


def _call_groq(prompt: str, model: str) -> str:
    from groq import Groq

    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"},
    )
    return resp.choices[0].message.content


def _call_ollama(prompt: str, model: str) -> str:
    import requests

    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    resp = requests.post(
        f"{host}/api/generate",
        json={"model": model, "prompt": prompt, "format": "json", "stream": False,
              "options": {"temperature": 0}},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["response"]


_PROVIDERS = {
    "groq": (_call_groq, "GROQ_MODEL"),
    "ollama": (_call_ollama, "OLLAMA_MODEL"),
}


def complete(prompt: str) -> str:
    """Raw completion from the configured provider, cached by (provider, model, prompt)."""
    provider = os.getenv("LLM_PROVIDER", "groq")
    call, model_var = _PROVIDERS[provider]
    model = os.environ[model_var]

    path = _cache_path(provider, model, prompt)
    if path.exists():
        return json.loads(path.read_text())["response"]

    response = call(prompt, model)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"provider": provider, "model": model,
                                "prompt": prompt, "response": response}))
    return response


def extract_constraints(query: str) -> dict:
    """Natural-language request -> {task, langs, max_size_mb, commercial, soft_query}.

    Raises ValueError when the model's reply is not valid JSON, so JSON parse
    success can be measured (D7 day-2 test).
    """
    raw = complete(EXTRACT_PROMPT.format(query=query))
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM did not return valid JSON: {raw!r}") from e
    return {
        "task": data.get("task"),
        "langs": [lang.lower() for lang in data.get("langs") or []],
        "max_size_mb": data.get("max_size_mb"),
        "commercial": data.get("commercial"),
        "soft_query": data.get("soft_query") or query,
    }
