"""Fig. 8 - observed vs land-cover-expected recall by municipality (descriptive).

Input : results/tableS2_municipalities.csv (python/04_land_cover_and_municipalities.py)
Output: figures/output/Figure_8.png
"""
from pathlib import Path

import pandas as pd, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7.5, "axes.linewidth": 0.7,
                     "xtick.major.width": 0.6, "ytick.major.width": 0.6})
ROOT = Path(__file__).resolve().parents[1]
(ROOT / "figures" / "output").mkdir(exist_ok=True)
t = pd.read_csv(ROOT / "results" / "tableS2_municipalities.csv")
STY = {"ROI1": dict(marker="o", color="#2d6bab", label="ROI-1 municipalities"),
       "ROI2": dict(marker="s", color="#b35429", label="ROI-2 municipalities")}
fig, ax = plt.subplots(figsize=(3.4, 3.4), dpi=300)
lo, hi = 0.15, 1.0
ax.plot([lo, hi], [lo, hi], ls="--", color="#555555", lw=0.9, zorder=1)
for dom, g in t.groupby("domain"):
    st = STY[dom]
    ax.scatter(g.expected_recall, g.recall, s=6 + g.daa_km2 * 0.09, marker=st["marker"], color=st["color"],
               edgecolor="white", linewidth=0.5, zorder=3)
LAB = {  # municipality: (dx, dy, ha)
    "Pantano Grande": (0.022, 0, "left"), "Cachoeira do Sul": (-0.026, 0.0, "right"),
    "Porto Alegre": (-0.02, 0, "right"), "São Sepé": (0.025, 0, "left"),
    "Santa Cruz do Sul": (0.022, 0.004, "left"), "Cachoeirinha": (-0.016, 0.0, "right"),
    "Guaíba": (-0.018, 0.018, "right"), "Santa Maria": (-0.025, -0.012, "right"),
    "Candelária": (0.026, -0.006, "left"), "Faxinal do Soturno": (0.02, 0, "left"),
}
for _, r in t.iterrows():
    if r.municipality in LAB:
        dx, dy, ha = LAB[r.municipality]
        ax.text(r.expected_recall + dx, r.recall + dy, r.municipality, ha=ha, va="center", fontsize=6.4,
                color="#222222", zorder=4,
                bbox=dict(fc="white", ec="none", pad=0.4, alpha=0.9) if r.municipality == "Cachoeirinha" else None)
ax.set_xlim(lo, hi); ax.set_ylim(lo, hi); ax.set_aspect("equal")
ticks = np.arange(0.2, 1.01, 0.2)
ax.set_xticks(ticks); ax.set_yticks(ticks)
ax.set_xlabel("Recall expected from land-cover mix")
ax.set_ylabel("Observed recall (FLOOD-HI + masks)")
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
h = [Line2D([], [], ls="", marker=STY[d]["marker"], color=STY[d]["color"], ms=4.5, label=STY[d]["label"])
     for d in ("ROI1", "ROI2")]
h.append(Line2D([], [], ls="--", color="#555555", lw=0.9, label="1:1 line"))
ax.legend(handles=h, loc="upper left", frameon=False, fontsize=6.6, handletextpad=0.4, borderaxespad=0.2)
fig.tight_layout(pad=0.3)
fig.savefig(ROOT / "figures" / "output" / "Figure_8.png", dpi=300, facecolor="white")
print("written", ROOT / "figures" / "output" / "Figure_8.png")
