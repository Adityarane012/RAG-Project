# Demo runbook

The grading emphasis is a **working demo**. This is the script, the checklists and the
failure playbook. The demo is recorded (`demo/cache/`, plan in `demo/plan.json`) and replay was verified with the network
broken; what is left is to rehearse it (see [implementation-plan.md](implementation-plan.md), H5).

## 1. Setup the day before

- [ ] `git pull`; `pip install -r requirements.txt`; `pytest` is green.
- [ ] `.env` filled: `PINECONE_API_KEY`, `GROQ_API_KEY`, `LLM_PROVIDER=groq` (models are pinned in `config.yaml`: Groq `openai/gpt-oss-20b`, Ollama `qwen2.5:7b-instruct`).
- [ ] `config.yaml`: `pinecone.namespace: prod`, `snapshot_date` set (shown in the UI).
- [ ] Pinecone `prod` namespace populated and untouched since the last rehearsal (experiments live in `exp-*`).
- [ ] Embeddings and reranking are hosted by Pinecone, so no local model download is needed; `INDEX_BACKEND=pinecone` uses the live index, `local` uses `data/localindex/` (copy it to the demo laptop if you want a fallback that needs no vector database).
- [ ] **Record the demo.** With live services run `RECORD=1 streamlit run app.py` and play every planned query **and its follow-ups** (the clarifying answer, accepting a relax offer). Each final state is saved under `demo/cache/`; commit that folder. Re-record after *any* index or config change, because a recording is a snapshot of what the system did then.
- [ ] Check it: `REPLAY=1 streamlit run app.py` with Wi-Fi off shows every demo query. The page says "Replay mode".
- [ ] Also warm the LLM cache (the same run does it) and copy `.cache/llm/` to the demo laptop; it is gitignored.
- [ ] Ollama installed on the demo laptop; the model pulled (`ollama pull <OLLAMA_MODEL>`); `ollama serve` works.
- [ ] Rehearse the provider switch (§4) once end to end.
- [ ] Screenshots of a good run saved as a last resort.

## 2. Five minutes before

- [ ] `streamlit run app.py` starts without error; the page shows the disclaimer and snapshot date.
- [ ] Run one example query to warm the connections.
- [ ] Close other heavy apps; plug in power; disable notifications.
- [ ] Have the baseline results table open in a second tab.

## 3. Demo script

The right-hand column is what the **recorded run of 2026-10-21** shows (live Pinecone, `gpt-oss-20b` explanations). A live run can
differ slightly (approximate search, model nondeterminism); say so if it does.

| # | Query / action | What to point out | Recorded |
|---|---|---|---|
| 1 | *"Small sentiment model for Hindi I can use in a commercial app."* | "small" became **≤ 500 MB** from a fixed table (shown in the intent line). Naive RAG on the left vs ours with a ✅/❌/⚠️ table and card citations | Ours: 5 of 5 fully verified. Naive: 4 of 5 fail the size limit |
| 2 | *"Commercial Hindi to Marathi translation."* | Direction is ⚠️ unless the model name states it; the banner says no model is fully verified. Naive shows two models failing commercial use (NLLB-based) | Ours: 5 ⚠️ (direction unknown), none ❌. Naive: 3 ❌, 1 ⚠️ |
| 3 | **Beginner:** *"I want a Hindi model."* | One clarifying question with clickable options; then the intent in plain words and a "Try it" snippet | Asks for the task; after choosing text classification it answers |
| 4 | *"Marathi NER model I can use commercially."* (with naive comparison) | Verified Marathi NER models (the L3Cube family) versus naive RAG returning speech-recognition models for a text task | Ours: 5 of 5 pass. Naive: 4 of 5 fail the task check |
| 5 | **Impossible:** *"Hindi to Marathi translation under 1 MB."* | Nothing can be verified, so every result is ⚠️ (size unknown) and the banner says no model is fully verified. The system does not invent an answer | 5 results, all ⚠️, banner shown |
| 6 | *"Urdu to English translation I can use in a product."* | `opus-mt-ur-en` states its direction in its name, so direction is ✅; the others are ⚠️ | 2 fully verified, 3 ⚠️ |
| 7 | **Build on it:** *"Tamil NER model I can fine-tune."*, expand a model | modifiable right, "fine-tune of …", LoRA estimate (a lower bound), task-guide link | 5 of 5 pass |
| 8 | **Check a model:** paste a model id in the "Check a model" tab | Instant rights table, no retrieval | not part of the recording; rehearse live |
| 9 | Close on the results table | Violation, unknown, fully verified for the five systems (`eval/results/results-v2.md`) | ours 0.0 / 16.7 / 83.3 |

Talking points to have ready: why verification is in code (D2); what ⚠️ means (D3/D12);
the disclaimer (not legal advice); the prompt-injection defence and its limits (D17).

## 4. Failure playbook

| Symptom | Cause | Action |
|---|---|---|
| Extraction errors / HTTP 429 from Groq | Rate limit | Cached queries still work. For new queries: stop the app, `export LLM_PROVIDER=ollama`, restart. Extraction quality may differ: keep to planned queries |
| Explanations missing but the table shows | LLM down at the explain step | Expected degradation; the UI warns. Continue: the verified table is the point |
| Spinner never ends on first query | Cold connections or a Groq rate-limit wait (the throttle sleeps rather than failing) | Wait up to 30 s; this is why §2 warms it |
| Pinecone timeout / no network | Venue Wi-Fi | Restart with `REPLAY=1` (recorded runs, no network). Say so out loud: it is a replay of a recorded run, not a live computation. Unplanned queries show "No recording" in this mode |
| Wrong constraint parsed (e.g. size dropped) | LLM extraction miss | Edit the shown intent (once built) or rephrase; mention that the intent line exists to catch exactly this |
| "Search is unavailable: …" | Missing key, no network, or an import error (the message says which) | Check the terminal; switch to `REPLAY=1` |
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
