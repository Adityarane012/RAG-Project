# HF Model Finder

Constraint-verified RAG for finding Hugging Face models. Ask in natural language
("a Marathi NER model under 500 MB, usable commercially, good on noisy social-media
text") and get back models that **provably** meet the hard constraints, with an
honest ✅ / ❌ / ⚠️ table for each one.

- **What & how:** [PROJECT.md](PROJECT.md)
- **Why:** [decisions.md](decisions.md)

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in the keys
```

## Layout

```
├── PROJECT.md          # what & how
├── decisions.md        # why
├── data/               # raw + normalized metadata (gitignored)
├── eval/               # queries.jsonl, labels, results
├── src/
│   ├── ingest.py       # pull metadata + cards from the Hub
│   ├── normalize.py    # size, license map, languages
│   ├── index.py        # chunk, embed, upsert to Pinecone
│   ├── llm.py          # extract_constraints(), provider switch, cache
│   ├── retrieve.py     # Pinecone metadata filters (D12) + search
│   └── verify.py       # pass / fail / unknown
├── tests/
└── app.py              # UI (Streamlit or Gradio, still open)
```

## Tests

```bash
pytest
```
