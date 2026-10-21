# Demo runbook

The grading emphasis is a **working demo**. This is the script, the checklists and the
failure playbook. Items marked **(not built)** need work first; see
[implementation-plan.md](implementation-plan.md) WP9.

## 1. Setup the day before

- [ ] `git pull`; `pip install -r requirements.txt`; `pytest` is green.
- [ ] `.env` filled: `PINECONE_API_KEY`, `GROQ_API_KEY`, `LLM_PROVIDER=groq` (models are pinned in `config.yaml`: Groq `openai/gpt-oss-20b`, Ollama `qwen2.5:7b-instruct`).
- [ ] `config.yaml`: `pinecone.namespace: prod`, `snapshot_date` set (shown in the UI).
- [ ] Pinecone `prod` namespace populated and untouched since the last rehearsal (experiments live in `exp-*`).
- [ ] The embedding model is downloaded locally (first load needs the network and is slow).
- [ ] **Record the demo.** With live services run `RECORD=1 streamlit run app.py` and play every planned query **and its follow-ups** (the clarifying answer, accepting a relax offer). Each final state is saved under `demo/cache/`; commit that folder. Re-record after *any* index or config change, because a recording is a snapshot of what the system did then.
- [ ] Check it: `REPLAY=1 streamlit run app.py` with Wi-Fi off shows every demo query. The page says "Replay mode".
- [ ] Also warm the LLM cache (the same run does it) and copy `.cache/llm/` to the demo laptop; it is gitignored.
- [ ] Ollama installed on the demo laptop; the model pulled (`ollama pull <OLLAMA_MODEL>`); `ollama serve` works.
- [ ] Rehearse the provider switch (§4) once end to end.
- [ ] Screenshots of a good run saved as a last resort.

## 2. Five minutes before

- [ ] `streamlit run app.py` starts without error; the page shows the disclaimer and snapshot date.
- [ ] Run one example query to warm the embedding model and Pinecone connection.
- [ ] Close other heavy apps; plug in power; disable notifications.
- [ ] Have the baseline results table open in a second tab.

## 3. Demo script

Expected outcomes below are **targets to verify in rehearsal**, not recorded results.
Fill in the right-hand column during the first rehearsal.

| # | Query / action | What to point out | Observed in rehearsal |
|---|---|---|---|
| 1 | *"Small sentiment model for Hindi I can use in a commercial app."* | "small" became **≤ 500 MB** from a fixed table (shown in the intent line). Naive RAG on the left suggests a non-commercial or oversized model; ours shows ≥3 models with a ✅/❌/⚠️ table and card citations. | |
| 2 | *"Commercial Hindi→Marathi translation."* | NLLB-200 (believed CC-BY-NC, **verify**) is absent from ours but present on the left. Direction shows ⚠️ unless the card states it. | |
| 3 | **Beginner:** *"I want a Hindi model."* | One clarifying question with clickable options; then the parsed intent in plain words and a "Try it" snippet. | |
| 4 | **Build on it:** expand a recommended model | modifiable right, "fine-tune of …", LoRA fits a free Colab T4 ✅ (estimate: lower bound), task-guide link. | |
| 5 | **Check a model:** paste a well-known model id **(not built)** | Instant rights table, no retrieval. | |
| 6 | An impossible query | "No model meets all constraints; relax the size limit to 1 GB?" then accept or decline. | |
| 7 | Close on the baseline table | Violation rate @5 for the four systems. | |

Talking points to have ready: why verification is in code (D2); what ⚠️ means (D3/D12);
the disclaimer (not legal advice); the prompt-injection defence and its limits (D17).

## 4. Failure playbook

| Symptom | Cause | Action |
|---|---|---|
| Extraction errors / HTTP 429 from Groq | Rate limit | Cached queries still work. For new queries: stop the app, `export LLM_PROVIDER=ollama`, restart. Extraction quality may differ: keep to planned queries |
| Explanations missing but the table shows | LLM down at the explain step | Expected degradation; the UI warns. Continue: the verified table is the point |
| Spinner never ends on first query | Embedding model still loading (cold start) | Wait; this is why §2 warms it |
| Pinecone timeout / no network | Venue Wi-Fi | Restart with `REPLAY=1` (recorded runs, no network). Say so out loud: it is a replay of a recorded run, not a live computation. Unplanned queries show "No recording" in this mode |
| Wrong constraint parsed (e.g. size dropped) | LLM extraction miss | Edit the shown intent (once built) or rephrase; mention that the intent line exists to catch exactly this |
| "Search isn't wired up" | `get_graph()` not wired / import error | Check the terminal; fall back to screenshots |
| Different results from rehearsal | Index or snapshot changed | Confirm namespace `prod` and `snapshot_date` |
| Streamlit state looks stale | Old session | Click an example query (it resets the loop); or reload the page |

## 5. Switching to Ollama (rehearse this)

```bash
ollama pull qwen2.5:7b-instruct      # once, ahead of time (qwen2.5:3b on an 8 GB laptop)
export LLM_PROVIDER=ollama
# only for the small model:  export OLLAMA_MODEL=qwen2.5:3b
streamlit run app.py
```

Nothing else changes: the provider is behind `llm.complete`. Expect slower extraction and
possibly different JSON quality; the `clean_constraints` validator turns bad fields into
"no constraint" rather than crashing, but check the shown intent after each query.

## 6. After the demo

- Archive the terminal log and screenshots with the write-up.
- Do not re-index `prod` until grading is finished.
