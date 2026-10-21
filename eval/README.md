# Evaluation (D11, D19)

- `queries.jsonl`: ~120 queries, **written before any tuning**. One JSON object per line:
  `{"id": "q001", "query": "...", "kind": "normal|impossible|vague", "source": "teammate|classmate"}`.
  ~100 from the teammate not building the pipeline (incl. ~10 impossible, ~15 vague),
  ~20 from classmates who haven't seen the system. Deliberately not seeded here.
- `labels/`: manual relevance labels (~50 queries) and faithfulness checks (~30 answers).
- `baselines/`: saved results for naive RAG, keyword + filters, and the HF Hub filters
  (run the Hub once and save it, since the Hub changes).
- `metrics.py`: the automatic metrics, as pure functions shared by all systems.
- `run_eval.py`: one script that regenerates the results table.
