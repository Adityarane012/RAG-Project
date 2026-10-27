"""Tiny diagram toolkit on matplotlib: boxes, arrows, consistent semantics (LLM = orange, code = blue, data = grey, user/UI = teal)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
matplotlib.rcParams["font.family"] = ["Liberation Sans", "DejaVu Sans"]
matplotlib.rcParams["svg.fonttype"] = "none"

INK, MUTED, GRID = "#1b1b1b", "#555555", "#d9d9d9"
KIND = {  # fill, edge
    "code": ("#dbe9fb", "#2a78d6"), "llm": ("#fde5d9", "#eb6834"), "data": ("#ececec", "#7a7a7a"),
    "ui": ("#d7f0e8", "#1baf7a"), "pass": ("#dff0df", "#008300"), "fail": ("#fbe0e0", "#e34948"),
    "unk": ("#fdf0cc", "#c98500"), "plain": ("#ffffff", "#7a7a7a"), "note": ("#f6f6f6", "#bdbdbd"),
}

def canvas(w, h, dpi=220, ylim=None):
    fig = plt.figure(figsize=(w, h), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 100); ax.set_ylim(0, ylim or 100 * h / w); ax.axis("off")
    return fig, ax

def esc(t):
    return t.replace("$", r"\$")

def box(ax, x, y, w, h, text, kind="code", fs=8.5, bold=False, align="center", r=1.2, lw=1.1, color=None, ls="-"):
    fc, ec = KIND[kind]
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", fc=fc, ec=ec, lw=lw, ls=ls, zorder=2))
    ha = {"center": "center", "left": "left"}[align]
    tx = x + w / 2 if align == "center" else x + 1.2
    ax.text(tx, y + h / 2, esc(text), ha=ha, va="center", fontsize=fs, color=color or INK, fontweight="bold" if bold else "normal", zorder=3, linespacing=1.25)
    return (x, y, w, h)

def arrow(ax, p, q, text=None, fs=7.5, style="-|>", color=MUTED, lw=1.1, rad=0.0, tdx=0, tdy=1.2, ls="-"):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=9, color=color, lw=lw, connectionstyle=f"arc3,rad={rad}", zorder=1, linestyle=ls))
    if text:
        ax.text((p[0] + q[0]) / 2 + tdx, (p[1] + q[1]) / 2 + tdy, text, ha="center", va="center", fontsize=fs, color=MUTED, zorder=4,
                bbox=dict(fc="white", ec="none", pad=0.6))

def label(ax, x, y, text, fs=8, color=MUTED, ha="left", bold=False, italic=False):
    ax.text(x, y, esc(text), fontsize=fs, color=color, ha=ha, va="center", fontweight="bold" if bold else "normal", fontstyle="italic" if italic else "normal")

def legend(ax, x, y, items, fs=7.2, dx=15):
    for i, (kind, text) in enumerate(items):
        fc, ec = KIND[kind]
        ax.add_patch(FancyBboxPatch((x + i * dx, y), 2.4, 2.0, boxstyle="round,pad=0,rounding_size=0.5", fc=fc, ec=ec, lw=1, zorder=2))
        ax.text(x + i * dx + 3.3, y + 1.0, text, fontsize=fs, va="center", color=MUTED)

def save(fig, name):
    fig.savefig(f"figs/{name}.png", dpi=220, facecolor="white"); plt.close(fig)

def diamond(ax, cx, cy, w, h, text, kind="unk", fs=7.4):
    from matplotlib.patches import Polygon
    fc, ec = KIND[kind]
    ax.add_patch(Polygon([(cx, cy + h / 2), (cx + w / 2, cy), (cx, cy - h / 2), (cx - w / 2, cy)], closed=True, fc=fc, ec=ec, lw=1.1, zorder=2))
    ax.text(cx, cy, esc(text), ha="center", va="center", fontsize=fs, color=INK, zorder=3, linespacing=1.2)

def term(ax, x, y, w, h, text, fs=7.8):
    return box(ax, x, y, w, h, text, "ui", fs, bold=True, r=h / 2)
