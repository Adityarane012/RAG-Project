# Appendix C: List of Components

@tab:c_software to @tab:c_data list the software, hardware and service components, and the data artefacts, that make up the project. Versions are those installed in the environment in which the results were produced.

::: table c_software size=9 cols=3.4,2,5.6
Software components.
| Component | Version | Purpose in the project |
|:--|:-:|:--|
| Python | 3.13 | Implementation language |
| LangGraph | 1.2 | State-graph orchestration of the query pipeline |
| Streamlit | 1.66 | Web interface |
| Pinecone Python client | 10.1 | Vector store, hosted embeddings, hosted re-ranking |
| Groq Python client | 1.7 | Language-model inference |
| huggingface_hub | 2.2 | Hub listing and downloads |
| sentence-transformers | 6.2 | Optional local embeddings and re-ranker |
| Transformers | 4.57 / 5.20 | Try-it smoke test |
| NumPy | 2.5 | Vector arithmetic in the exact local index |
| PyYAML, requests, python-dotenv | – | Configuration, HTTP, environment file |
| pytest | 9.1 | 335 offline tests |
| Playwright (Chromium) | – | Screenshots for this report |
| LibreOffice, python-docx, matplotlib | – | Generation of this document and its figures |
:::

::: table c_hardware size=9 cols=3.4,7
Hardware and hosted-service components.
| Component | Specification |
|:--|:--|
| Development container | 4 virtual CPUs, 16 GB RAM, no GPU, Linux 6.x |
| Pinecone Starter | Serverless vector index (48,179 vectors); hosted `multilingual-e5-large` and `bge-reranker-v2-m3` |
| Groq free tier | `gpt-oss-20b` and `gpt-oss-120b` inference |
| Hugging Face Hub | Public API for model metadata and cards |
| Ollama (optional) | Local language-model runtime, not used for the reported results |
:::

::: table c_data size=9 cols=3.8,6.6
Data artefacts in the repository.
| Artefact | Content |
|:--|:--|
| `data/snapshot-2026-10-25/records.jsonl.gz` | Normalised snapshot, 15,991 records |
| `eval/queries.jsonl` | The 100 evaluation queries (committed before tuning) |
| `eval/extraction_test.jsonl` | Constraint-extraction test cases |
| `eval/results/` | Raw and summarised results of every run, frozen parses, relevance and faithfulness reports, smoke-test outputs |
| `eval/labels/` | Relevance sheet, grades of both passes, faithfulness grades, one-line reasons from the judges, provenance note |
| `demo/plan.json`, `demo/cache/` | Ten demonstration scenarios and their recorded runs |
| `docs/` | Design log (D1 to D24), architecture, data notes, evaluation plan, security and limitations |
:::
