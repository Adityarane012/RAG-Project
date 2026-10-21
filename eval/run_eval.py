"""One script -> the results table (D21). Needs a data snapshot, config.yaml and the
query set; nothing else.

Planned flow, per query in eval/queries.jsonl and per system in D19
(naive RAG, keyword + filters, HF Hub filters, ours):
  1. get that system's top-5 models
  2. re-verify each with src.verify.verify() against the query's parsed constraints
  3. score with eval.metrics, then write eval/results/<snapshot-date>.md
Relevance and faithfulness need manual labels in eval/labels/ (D11).
"""

from eval.metrics import load_queries  # noqa: F401


def main() -> None:
    raise NotImplementedError("Wire up after the pipeline and baselines exist")


if __name__ == "__main__":
    main()
