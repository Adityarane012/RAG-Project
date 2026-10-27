import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
matplotlib.rcParams["font.family"] = ["Liberation Sans", "DejaVu Sans"]
INK, MUTED, GRID = "#1b1b1b", "#555555", "#e3e3e3"
BLUE, ORANGE, AQUA, YEL, MAG, GREEN, VIOLET, RED = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"
AMBER = "#c98500"
SYS = [("ours", "Ours (verified RAG)", BLUE), ("naive", "Naive RAG", ORANGE), ("keyword", "Keyword + filters", AQUA),
       ("hf_basic", "HF Hub basic", YEL), ("hf_licensed", "HF Hub licensed", MAG)]

def base(w=6.6, h=3.2):
    fig, ax = plt.subplots(figsize=(w, h), dpi=220)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    ax.spines["left"].set_color("#999999"); ax.spines["bottom"].set_color("#999999")
    ax.tick_params(colors=MUTED, labelsize=8, length=3)
    ax.set_facecolor("white")
    return fig, ax

def save(fig, name):
    fig.savefig(f"figs/{name}.png", dpi=220, facecolor="white", bbox_inches="tight", pad_inches=0.08); plt.close(fig)

def corpus():
    rows = [("automatic-speech-recognition", 2476, 993), ("translation", 1074, 812), ("text-classification", 1262, 355),
            ("token-classification", 1125, 284), ("sentence-similarity", 1175, 208), ("text-generation", 739, 396),
            ("question-answering", 814, 263), ("summarization", 885, 130), ("object-detection", 254, 746),
            ("image-classification", 938, 62), ("image-segmentation", 537, 463)]
    fig, ax = base(6.6, 3.7)
    n = len(rows)
    for i, (t, k, u) in enumerate(rows):
        y = n - 1 - i
        ax.barh(y, k, color=BLUE, height=0.62, linewidth=0)
        ax.barh(y, u, left=k, color=YEL, height=0.62, linewidth=0, hatch="////", edgecolor="white")
        ax.text(k / 2, y, f"{k:,}", ha="center", va="center", fontsize=7.4, color="white")
        ax.text(k + u + 40, y, f"{u:,} unknown size ({100*u/(k+u):.0f}%)", ha="left", va="center", fontsize=7.2, color=MUTED)
    ax.set_yticks(range(n)); ax.set_yticklabels([r[0] for r in rows][::-1], fontsize=8, color=INK)
    ax.set_xlim(0, 4300); ax.set_xlabel("models in the snapshot (15,991 in all)", fontsize=8, color=MUTED)
    ax.grid(axis="x", color=GRID, lw=0.6); ax.set_axisbelow(True)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=BLUE, label="size known"), Patch(facecolor=YEL, hatch="////", edgecolor="white", label="size unknown")],
              loc="lower right", frameon=False, fontsize=8, labelcolor=MUTED)
    save(fig, "chart_corpus")

def main():
    d = {"ours": (83.3, 16.7, 0.0), "naive": (29.1, 20.5, 50.4), "keyword": (38.0, 62.0, 0.0),
         "hf_basic": (53.6, 13.6, 32.8), "hf_licensed": (59.5, 14.7, 25.9)}
    fig, ax = base(6.6, 2.9)
    n = len(SYS)
    for i, (k, name, _) in enumerate(SYS):
        y = n - 1 - i
        p, u, f = d[k]
        ax.barh(y, p, color=GREEN, height=0.62, linewidth=0)
        ax.barh(y, u, left=p, color=YEL, height=0.62, linewidth=0, hatch="////", edgecolor="white")
        ax.barh(y, f, left=p + u, color=RED, height=0.62, linewidth=0)
        ax.text(p / 2, y, f"{p:.1f}", ha="center", va="center", fontsize=8, color="white", fontweight="bold")
        if u > 6: ax.text(p + u / 2, y, f"{u:.1f}", ha="center", va="center", fontsize=8, color=INK)
        if f > 6: ax.text(p + u + f / 2, y, f"{f:.1f}", ha="center", va="center", fontsize=8, color="white", fontweight="bold")
    ax.set_yticks(range(n)); ax.set_yticklabels([s[1] for s in SYS][::-1], fontsize=8.4, color=INK)
    ax.set_xlim(0, 100); ax.set_xlabel("% of recommended models (75 normal queries; judged by verify())", fontsize=8, color=MUTED)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=GREEN, label="fully verified"), Patch(facecolor=YEL, hatch="////", edgecolor="white", label="unknown (flagged)"), Patch(color=RED, label="violates a constraint")],
              loc="upper center", bbox_to_anchor=(0.5, 1.2), ncol=3, frameon=False, fontsize=8, labelcolor=MUTED)
    save(fig, "chart_main")

def violations():
    cons = ["size", "task", "languages", "commercial"]
    d = {"naive": [50.4, 24.1, 19.4, 4.0], "hf_basic": [80.0, 0, 0, 13.3], "hf_licensed": [71.9, 0, 0, 0]}
    names = {"naive": ("Naive RAG", ORANGE), "hf_basic": ("HF Hub basic", YEL), "hf_licensed": ("HF Hub licensed", MAG)}
    fig, ax = base(6.6, 3.0)
    w = 0.26
    for j, k in enumerate(["naive", "hf_basic", "hf_licensed"]):
        xs = [i + (j - 1) * (w + 0.03) for i in range(len(cons))]
        ax.bar(xs, d[k], width=w, color=names[k][1], label=names[k][0], linewidth=0)
        for x, v in zip(xs, d[k]):
            ax.text(x, v + 1.5, f"{v:.1f}" if v else "0", ha="center", va="bottom", fontsize=7.6, color=INK)
    ax.set_xticks(range(len(cons))); ax.set_xticklabels(cons, fontsize=8.6, color=INK)
    ax.set_ylim(0, 95); ax.set_ylabel("% of recommendations failing it", fontsize=8, color=MUTED)
    ax.grid(axis="y", color=GRID, lw=0.6); ax.set_axisbelow(True)
    ax.legend(loc="upper right", frameon=False, fontsize=8, labelcolor=MUTED)
    ax.text(0.0, -0.22, "Ours and keyword + filters: 0.0 on every constraint. Direction and modifiable: 0.0 for all five systems.", transform=ax.transAxes, fontsize=7.6, color=MUTED)
    save(fig, "chart_violations")

def relevance():
    names = ["HF Hub\nlicensed", "Naive\nRAG", "Keyword\n+ filters", "Ours"]
    cols = [MAG, ORANGE, AQUA, BLUE]
    panels = [("Mean grade (0 to 2)", [0.685, 0.865, 1.061, 1.284], "{:.2f}", 2.0),
              ("Queries with a grade-2 model (%)", [22.5, 67.5, 65.0, 81.6], "{:.1f}", 100),
              ("Models graded 1 or 2 (%)", [61.5, 51.5, 70.1, 76.8], "{:.1f}", 100)]
    fig, axs = plt.subplots(1, 3, figsize=(6.6, 2.6), dpi=220)
    for ax, (t, v, f, top) in zip(axs, panels):
        for s in ("top", "right"): ax.spines[s].set_visible(False)
        ax.spines["left"].set_color("#999999"); ax.spines["bottom"].set_color("#999999")
        ax.bar(range(4), v, color=cols, width=0.68, linewidth=0)
        for i, x in enumerate(v): ax.text(i, x + top * 0.02, f.format(x), ha="center", va="bottom", fontsize=7.6, color=INK)
        ax.set_ylim(0, top * 1.12); ax.set_xticks(range(4)); ax.set_xticklabels(names, fontsize=6.6, color=INK)
        ax.set_title(t, fontsize=7.8, color=INK, loc="left"); ax.tick_params(axis="y", labelsize=7, colors=MUTED, length=2)
        ax.grid(axis="y", color=GRID, lw=0.6); ax.set_axisbelow(True)
    fig.tight_layout(w_pad=1.2)
    save(fig, "chart_relevance")

def noverified():
    d = {"ours": (0.0, 100.0), "naive": (73.3, 26.7), "keyword": (0.0, 100.0), "hf_basic": (75.0, 25.0), "hf_licensed": (63.3, 36.7)}
    fig, ax = base(6.6, 2.7)
    n = len(SYS)
    for i, (k, name, _) in enumerate(SYS):
        y = n - 1 - i
        f, u = d[k]
        ax.barh(y, f, color=RED, height=0.62, linewidth=0)
        ax.barh(y, u, left=f, color=YEL, height=0.62, linewidth=0, hatch="////", edgecolor="white")
        if f > 6: ax.text(f / 2, y, f"{f:.1f}", ha="center", va="center", fontsize=8, color="white", fontweight="bold")
        ax.text(f + u / 2, y, f"{u:.1f}", ha="center", va="center", fontsize=8, color=INK)
    ax.set_yticks(range(n)); ax.set_yticklabels([s[1] for s in SYS][::-1], fontsize=8.4, color=INK)
    ax.set_xlim(0, 100); ax.set_xlabel("% of recommended models for the 12 queries where no model in the corpus fully passes", fontsize=8, color=MUTED)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=RED, label="violates a constraint"), Patch(facecolor=YEL, hatch="////", edgecolor="white", label="unknown (flagged)")],
              loc="upper center", bbox_to_anchor=(0.5, 1.2), ncol=2, frameon=False, fontsize=8, labelcolor=MUTED)
    save(fig, "chart_noverified")

def tryit():
    rows = [("image-classification", 3, 3), ("text-generation", 3, 3), ("question-answering", 3, 3), ("token-classification", 3, 3),
            ("object-detection", 2, 3), ("image-segmentation", 2, 3), ("summarization", 2, 3), ("text-classification", 1, 3),
            ("sentence-similarity", 1, 3), ("translation", 0, 2), ("automatic-speech-recognition", 0, 3)]
    fig, ax = base(6.6, 3.0)
    n = len(rows)
    for i, (t, ok, tot) in enumerate(rows):
        y = n - 1 - i
        ax.barh(y, ok, color=GREEN, height=0.62, linewidth=0)
        ax.barh(y, tot - ok, left=ok, color=RED, height=0.62, linewidth=0, alpha=0.85)
        ax.text(tot + 0.1, y, f"{ok} of {tot} ran", ha="left", va="center", fontsize=7.8, color=MUTED)
    ax.set_yticks(range(n)); ax.set_yticklabels([r[0] for r in rows][::-1], fontsize=8, color=INK)
    ax.set_xlim(0, 4.2); ax.set_xticks([0, 1, 2, 3]); ax.set_xlabel("small safetensors models tried per task (20 of 32 ran)", fontsize=8, color=MUTED)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=GREEN, label="template ran"), Patch(color=RED, alpha=0.85, label="failed")], loc="center right", frameon=False, fontsize=8, labelcolor=MUTED)
    save(fig, "chart_tryit")

if __name__ == "__main__":
    corpus(); main(); violations(); relevance(); noverified(); tryit()
