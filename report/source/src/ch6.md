# Conclusion and Future Scope

## Work carried out

This project designed, built and evaluated **HF Model Finder**, a constraint-verified retrieval-augmented system for finding Hugging Face models. A data pipeline turned the Hub into a checksummed snapshot of 15,991 models over eleven tasks, with size, licence rights, languages and translation direction normalised and every missing value marked unknown; 48,179 card chunks were embedded with a multilingual model and indexed in Pinecone and in an exact local index with the same filter semantics. A LangGraph pipeline parses a request with a language model and a deterministic backstop, asks clarifying questions when needed, retrieves with filters that keep unknowns, re-ranks, verifies a pool of 100 models in code, shows five, and explains them with cited, budgeted card excerpts under a prompt-injection defence. A Streamlit interface adds the plain-language reading of the request, the side-by-side comparison with naive RAG, starter snippets, adaptation information and a check-a-model mode. The system was tested by 335 offline tests and evaluated against four baselines on 100 queries fixed before tuning.

## Conclusions

The results of Chapter 4 support the following conclusions, each with the limits stated there.

1. **Verification in code removes constraint violations that retrieval alone cannot.** On the 75 normal queries the full system recommended no model that fails a requested constraint, while naive RAG failed one on 50.4% of its recommendations and the Hub's own filters on 25.9% to 32.8%. Because verdicts are computed from metadata and never from model output, the property holds regardless of what the language model or a model card says.
2. **Honest unknowns are better than guesses and than silence.** 83.3% of the system's recommendations were fully verified and the remaining 16.7% were shown with an explicit unknown. On the 12 queries for which no model in the corpus can fully pass, the system never claimed verification and said so in a banner, while the baselines recommended violating models for 63.3% to 75.0% of their recommendations.
3. **Verifying wide and showing narrow matters.** Semantic search cannot see size, licence or direction; verifying 100 models instead of five raised fully verified answers from 72.3% to 83.3% and repaired the translation queries.
4. **Verification did not cost relevance.** In a blind study graded by language-model judges (not humans), the full system had the highest mean grade (1.28 of 2) and the highest share of queries with a clearly suitable model (81.6%); agreement between two judging passes was high (kappa 0.874 unweighted, 0.945 quadratic-weighted), which shows consistent judging but not agreement with human raters.
5. **Beginners are served by design, not by documentation.** The system asked a clarifying question on all 15 vague queries, shows how it understood the request, offers editable fields, runnable snippets and a memory estimate for fine-tuning, and refuses out-of-scope requests with nothing shown.
6. **Explanations are useful but not evidence.** 81.6% of the claims in explanations were supported by the card text shown, and half of the explanations were entirely supported; the design therefore keeps all licence, size and language facts in the verified table and forbids the explanation from stating them.

## Limitations

The main limitations are summarised in @tab:limits. In brief: relevance and faithfulness were judged by language models; one person wrote the queries and built the system; the 100-query evaluation covers five of the eleven tasks; verdicts depend on declared metadata and 27% to 30% of sizes, 20% of rights and most translation directions are unknown; the abstain and relax paths do not fire on this corpus; the hosted re-ranker's monthly quota is exhausted, so new searches are not re-ranked; and the snapshot is a sample of the Hub dated 25 October 2026.

## Future scope

The following extensions follow directly from the limitations and are listed in the order in which they would add the most evidence or value.

1. **Human validation of the grades.** Re-grade a sample (for example one query per task, about 40 pairs) with human annotators, report agreement with the language-model judges, and replace the judged figures where they differ. This is the single most useful strengthening of the evidence.
2. **Extend the evaluation to all eleven tasks.** Write queries for vision, text generation, summarization and question answering before tuning, include queries from people other than the builder, and repeat the study with the new tasks included.
3. **Make unknowns smaller without guessing.** Parse GGUF and ONNX sizes as separate, labelled sizes, read the licence text for the common custom licences marked `other`, infer translation direction from card text with a verified extraction step, and keep the unknown verdict wherever the evidence is not explicit.
4. **A stronger abstention policy.** Allow the system to abstain, or to offer a relaxation, when no candidate is fully verified and some constraint is known to fail for most candidates, and measure it on queries that are impossible by a known failure.
5. **Keep the index fresh.** Replace the one-off snapshot by an incremental pipeline that re-fetches changed models, with the checksummed snapshot retained for reproducibility, and add live fetching of a model outside the snapshot to the check-a-model mode.
6. **Wider coverage.** Add tasks that are currently mapped to the nearest task or refused (for example feature-extraction embeddings, audio classification and zero-shot classification), and a sampling strategy for text generation that does not rely on download counts alone.
7. **Benchmark scores as information.** Show author-reported evaluation results labelled as unverified (the code exists but is not shown), and study whether independently re-run benchmark numbers could become a verified signal.
8. **A user study.** Observe developers and students using the tool on their own requests and compare time to a suitable, usable model with the Hub's search; the present evaluation measures correctness of the list, not the user's experience.
9. **Local re-ranking and offline use.** Run the cross-encoder on a GPU or replace it with a smaller model so that re-ranking has no quota, and complete the rehearsal of the fully local mode (local index, local embeddings, local language model).
10. **Publish the evaluation.** Release the snapshot, queries, parses and grades as a small benchmark for constraint-aware model search.

## Closing remark

The project began from a simple observation: a developer's request is a mixture of facts and preferences, and a system that treats facts as preferences will sometimes be wrong in ways the user cannot see. The remedy built here is modest and general. Let the language model do what it is good at, which is reading a request and describing a card; let code do what it must, which is checking facts; and show the user, in the same table, what is known, what is not, and what is false. The measurements in this report suggest that this separation costs little and removes a whole class of errors.
