"""Fig. 3 - Sentinel-2 acquisitions and cloud-free observations per pixel.

(a, b) Clear-sky fraction of each tile on each acquisition date, computed as the
       share of the tile footprint inside ROI-1 / ROI-2 that QA60 flags as clear.
       Where a tile was delivered as two granules on 9 May, the first granule is
       shown (Table S1).
(c)    Share of the domain area and of the DAA area with 0, 1, 2 and >= 3
       QA60-clear observations (values printed above the bars).

Input : data/exports/ROI{1,2}_A_cenas_sentinel2.csv (script 01, export A)
        data/exports/ROI{1,2}_C_matrizes_confusao.csv (script 01, export C)
Output: figures/output/Figure_3.png
        results/observation_shares.csv (written by python/09_observation_counts.py)
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
from common import EXPORTS  # noqa: E402

OUT = ROOT / "figures" / "output"
OUT.mkdir(exist_ok=True)

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7.6, "axes.linewidth": 0.7,
                     "xtick.major.width": 0.7, "ytick.major.width": 0.7,
                     "xtick.major.size": 3, "ytick.major.size": 3})

CMAP = LinearSegmentedColormap.from_list(
    "clear", ["#f0f0f0", "#c6dbef", "#6baed6", "#2b7bba", "#08519c"])
NORM = Normalize(0, 1)
BAND = "#fde7c4"                                   # 6 May 2024
TILES = {"ROI1": ["22JEM", "22JDN", "22JDM"],
         "ROI2": ["22JCN", "22JCM", "22JBN", "22JBM", "21JYH", "21JYG"]}
SERIES = [("ROI1", "area", "ROI-1 area", "#9ecae1"), ("ROI1", "daa", "ROI-1 DAA", "#08519c"),
          ("ROI2", "area", "ROI-2 area", "#fdae6b"), ("ROI2", "daa", "ROI-2 DAA", "#a63603")]
CATS = ["0", "1", "2", "≥3"]


def acquisitions(roi):
    """Clear fraction per tile and date; first granule when a tile has two."""
    a = pd.read_csv(EXPORTS / f"{roi}_A_cenas_sentinel2.csv")
    a = a.sort_values("system:index").drop_duplicates(["data", "tile"], keep="first")
    a["date"] = pd.to_datetime(a["data"])
    a["clear"] = 1 - a["frac_nuvem_qa60_na_roi"]
    return a


def observation_shares(roi):
    """Percentage of domain and DAA pixel-equivalents with 0, 1, 2, >=3 clear observations."""
    c = pd.read_csv(EXPORTS / f"{roi}_C_matrizes_confusao.csv")
    area = c[["obs0", "obs1", "obs2", "obs3mais"]].sum().to_numpy()
    daa = c[["ref_obs0", "ref_obs1", "ref_obs2", "ref_obs3mais"]].sum().to_numpy()
    return {"area": 100 * area / area.sum(), "daa": 100 * daa / daa.sum()}


def tile_panel(ax, roi, title, ylabel):
    a = acquisitions(roi)
    tiles = TILES[roi]
    y = {t: len(tiles) - 1 - i for i, t in enumerate(tiles)}
    x0, x1 = pd.Timestamp("2024-04-27"), pd.Timestamp("2024-05-12")
    for d in pd.to_datetime(["2024-04-28", "2024-05-02", "2024-05-06", "2024-05-10"]):
        ax.axvline(d, color="#dddddd", lw=0.7, zorder=0)
    ax.axvspan(pd.Timestamp("2024-05-05 12:00"), pd.Timestamp("2024-05-06 12:00"), color=BAND, zorder=0.5, lw=0)
    ax.scatter(a["date"], [y[t] for t in a["tile"]], c=CMAP(NORM(a["clear"])), marker="s", s=62,
               edgecolors="#555555", linewidths=0.6, zorder=3)
    ax.set_xlim(x0, x1)
    ax.set_ylim(-0.7, len(tiles) - 1 + 0.7)
    ax.set_yticks(range(len(tiles)))
    ax.set_yticklabels(tiles[::-1])
    ax.set_xticks(pd.to_datetime(["2024-04-28", "2024-05-02", "2024-05-06", "2024-05-10"]))
    ax.xaxis.set_major_formatter(plt.FuncFormatter(            # "6 May" (portable, no %-d)
        lambda v, _: f"{mdates.num2date(v).day} {mdates.num2date(v):%b}"))
    ax.set_xlabel("Acquisition date (2024)")
    if ylabel:
        ax.set_ylabel("Sentinel-2 tile")
    ax.set_title(title, fontweight="bold", fontsize=8.6, pad=6)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def bars_panel(ax):
    x = np.arange(len(CATS))
    w = 0.19
    for k, (roi, pop, name, colour) in enumerate(SERIES):
        v = observation_shares(roi)[pop]
        xs = x + (k - 1.5) * w
        ax.bar(xs, v, w, color=colour, label=name, zorder=2)
        for xi, vi in zip(xs, v):
            txt = f"{vi:.1f}" if vi < 10 else f"{vi:.0f}"
            ax.text(xi, vi + 1.2, txt, ha="center", va="bottom", rotation=90, fontsize=5.6, color="#333333")
    for b in (0.5, 1.5, 2.5):
        ax.axvline(b, color="#e3e3e3", lw=0.7, zorder=0)
    ax.set_xticks(x)
    ax.set_xticklabels(CATS)
    ax.set_xlim(-0.55, len(CATS) - 0.45)
    ax.set_ylim(0, 100)
    ax.set_yticks(range(0, 101, 20))
    ax.set_ylabel("Share (%)")
    ax.set_xlabel("Cloud-free observations (QA60)")
    ax.set_title("(c) Valid observations per pixel", fontweight="bold", fontsize=8.6, pad=6)
    ax.legend(loc="upper right", frameon=False, fontsize=6.8, handlelength=1.4, borderaxespad=0.1,
              labelspacing=0.35)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


fig = plt.figure(figsize=(7.24, 2.96), dpi=300)
ax_a = fig.add_axes([0.088, 0.333, 0.222, 0.597])
ax_b = fig.add_axes([0.399, 0.333, 0.222, 0.597])
ax_c = fig.add_axes([0.715, 0.131, 0.265, 0.799])
cax = fig.add_axes([0.14, 0.137, 0.24, 0.033])
tile_panel(ax_a, "ROI1", "(a) ROI-1 acquisitions", True)
tile_panel(ax_b, "ROI2", "(b) ROI-2 acquisitions", False)
bars_panel(ax_c)
cb = fig.colorbar(plt.cm.ScalarMappable(norm=NORM, cmap=CMAP), cax=cax, orientation="horizontal")
cb.set_ticks(np.arange(0, 1.01, 0.2))
cb.outline.set_linewidth(0.7)
cb.set_label("Fraction of the tile footprint within the ROI that QA60 flags as clear", fontsize=6.8)
fig.savefig(OUT / "Figure_3.png", dpi=300, facecolor="white")
print("written", OUT / "Figure_3.png")
for roi in ("ROI1", "ROI2"):
    s = observation_shares(roi)
    print(roi, "area %", s["area"].round(2), " DAA %", s["daa"].round(2))
