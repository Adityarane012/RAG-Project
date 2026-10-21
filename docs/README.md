# Documentation

| Read this | When |
|---|---|
| [PROJECT.md](PROJECT.md) | What we are building and how, users, scope, demo script, risks, viva questions |
| [decisions.md](decisions.md) | *Why* for every choice (D1–D24), with status |
| [architecture.md](architecture.md) | How the code is organised: modules, data model, graph, filter-vs-verify, failure modes |
| [implementation-plan.md](implementation-plan.md) | What is done, what is left, work packages with acceptance criteria, re-baselined calendar |
| [testing-strategy.md](testing-strategy.md) | Test layers, the edge-case catalogue (with status), live checks, extraction and poisoning tests |
| [data-pipeline.md](data-pipeline.md) | Hub → Pinecone: sampling, fetching, size rule, license map, languages, data-quality report |
| [evaluation-plan.md](evaluation-plan.md) | Query set, metrics, baselines, labelling, reproducibility, threats to validity |
| [demo-runbook.md](demo-runbook.md) | Demo script, checklists, failure playbook, Ollama switch |
| [security-and-limitations.md](security-and-limitations.md) | Threat model and what we do not claim |
| [development.md](development.md) | Setup, env vars, conventions, how-tos, troubleshooting |
| [data-notes.md](data-notes.md) | Template for live-check results and the data-quality report (fill in as you go) |

**Source of truth:** `decisions.md` for *why*, `PROJECT.md` for *what*, the code and
`config.yaml` for *how*. Where the implementation deliberately differs from the decision
docs, [architecture.md §11](architecture.md#11-where-the-implementation-deliberately-differs-from-the-decision-docs)
lists it. Keep these in sync: a change in behaviour is not finished until the relevant doc is.
