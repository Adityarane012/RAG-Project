from dg import *
fig, ax = canvas(6.6, 4.9)
# titles
label(ax, 2, 70.5, "OFFLINE: built once per snapshot", 8.6, INK, bold=True)
label(ax, 56, 70.5, "ONLINE: every query", 8.6, INK, bold=True)
# offline column
box(ax, 2, 61, 46, 7, "Hugging Face Hub API\n11 task tags: top-1,000 by downloads + Indic-tagged", "data", 7.6)
box(ax, 2, 49, 46, 8, "ingest + normalize + clean\nmetadata, size rule, license rights,\nlanguages; unknowns marked, never guessed", "code", 7.6)
box(ax, 2, 38, 46, 7, "chunk by card section (≤ 4 chunks per model)\n48,179 chunks, 15,990 models", "code", 7.6)
box(ax, 2, 27, 46, 7, "embed: multilingual-e5-large (1,024-d)\ncontent-hash cache", "code", 7.6)
box(ax, 2, 14, 46, 9, "vector index with metadata\nPinecone (prod) or exact local index\n+ checksummed snapshot (sha256)", "data", 7.6)
for y0, y1 in [(61, 57), (49, 45), (38, 34), (27, 23)]:
    arrow(ax, (25, y0), (25, y1))
# online column
box(ax, 57, 61, 41, 7, "User request (natural language)", "ui", 7.8)
box(ax, 57, 50, 41, 8, "LLM: extract constraints (JSON)\n+ deterministic backstop", "llm", 7.6)
box(ax, 57, 39, 41, 8, "filtered search (unknowns kept)\n+ rerank; verify a pool of 100 models", "code", 7.6)
box(ax, 57, 28, 41, 8, "CODE verifies every constraint\npass / fail / unknown → rank → top 5", "code", 7.6, bold=True)
box(ax, 57, 17, 41, 8, "LLM: cited explanation\ncard text treated as untrusted data", "llm", 7.6)
box(ax, 57, 6, 41, 8, "Streamlit UI: pass-fail-unknown table,\nTry it, Build on it, naive-RAG comparison", "ui", 7.6)
for y0, y1 in [(61, 58), (50, 47), (39, 36), (28, 25), (17, 14)]:
    arrow(ax, (77.5, y0), (77.5, y1))
arrow(ax, (48, 18.5), (57, 43), None, rad=-0.3)
ax.text(52.6, 33.0, "vectors +\nmetadata\n(queried)", fontsize=6.8, color=MUTED, ha="center", va="center", bbox=dict(fc="white", ec="none", pad=0.5), zorder=5)
legend(ax, 2, 1.5, [("code", "code (deterministic)"), ("llm", "LLM (untrusted output)"), ("data", "data store / source"), ("ui", "user / interface")], dx=24)
save(fig, "fig_block")
