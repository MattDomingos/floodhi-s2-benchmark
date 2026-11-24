"""Fig. 2, step 2 - evaluation workflow (nine steps in three stages).

Draws the workflow diagram. The small graphics use real data prepared by
fig02_data.py, and the recall chart of step 9 reads the land-cover recall table
written by python/04_land_cover_and_municipalities.py.

Input : figures/output/fig02_data.npz, results/fig7_recall_by_land_cover.csv
Output: figures/output/Figure_2.png
"""
import csv
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, Polygon, Circle, Ellipse
from matplotlib.transforms import Affine2D

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "figures" / "output" / "Figure_2.png"
D = np.load(ROOT / "figures" / "output" / "fig02_data.npz")
RECALL_CSV = ROOT / "results" / "fig7_recall_by_land_cover.csv"

plt.rcParams.update({"font.family": "DejaVu Sans", "mathtext.fontset": "dejavusans",
                     "axes.linewidth": 0.5, "xtick.major.width": 0.4, "ytick.major.width": 0.4})

ROWS = [("#2C5F8D", "#EAF1F8"), ("#1F7A70", "#E4F2EF"), ("#5A4E8C", "#EEEBF6")]
SAMPLE, CHECK = "#D9822B", "#3d4b5c"
NAVY, GREY = "#1f3b73", "#cacaca"
AGR = {"TN": "#e4e4e4", "FN": "#e66101", "FP": "#c51b7d", "TP": "#2166ac"}
LC = {1: "#e31a1c", 2: "#2171b5", 3: "#fee08b", 4: "#41ab5d", 5: "#bdbdbd", 6: "#fdae6b"}
INK, MUTED = "#222222", "#555555"

FS_BODY, FS_HEAD, FS_SMALL, FS_TINY, FS_MIN = 6.2, 7.0, 6.0, 5.5, 5.3
W, H = 6.5, 6.35
fig = plt.figure(figsize=(W, H), dpi=300)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")

LBL_X, LBL_W = 0.02, 0.26
PX0 = LBL_X + LBL_W + 0.07
GAP = 0.20
PW = (W - 0.02 - PX0 - 2 * GAP) / 3
TOP = H - 0.02
LEG_H, RG, HH = 0.25, 0.24, 0.24
PH = (TOP - LEG_H - 2 * RG) / 3
COLX = [PX0 + i * (PW + GAP) for i in range(3)]
ROWY = [TOP - i * (PH + RG) for i in range(3)]
G_H = 0.86
checks = []          # (artist, panel x0, panel x1, label) for the overflow test
headers = []         # (title artist, chip x0, label)


def inset(x, y, w, h):
    a = fig.add_axes([x / W, y / H, w / W, h / H])
    a.patch.set_alpha(0)
    return a


def hexrgb(c):
    c = c.lstrip("#")
    return np.array([int(c[i:i + 2], 16) for i in (0, 2, 4)]) / 255


CUR = {}


def reg(t):
    checks.append((t, CUR["x0"], CUR["x1"], CUR["name"]))
    return t


def panel(r, c, num, title, rq=None):
    col = ROWS[r][0]
    x, yt = COLX[c], ROWY[r]
    CUR.update(x0=x, x1=x + PW, name=f"panel {num}")
    ax.add_patch(FancyBboxPatch((x, yt - PH), PW, PH, boxstyle="round,pad=0,rounding_size=0.055",
                                fc="white", ec=col, lw=0.9, zorder=2))
    ax.add_patch(FancyBboxPatch((x, yt - HH), PW, HH, boxstyle="round,pad=0,rounding_size=0.055",
                                fc=col, ec=col, lw=0.9, zorder=3))
    ax.add_patch(Rectangle((x, yt - HH), PW, HH / 2, fc=col, ec=col, lw=0.9, zorder=3))
    ax.add_patch(Circle((x + 0.125, yt - HH / 2), 0.085, fc="white", ec="none", zorder=4))
    ax.text(x + 0.125, yt - HH / 2 - 0.004, str(num), ha="center", va="center", fontsize=6.8,
            fontweight="bold", color=col, zorder=5)
    t = ax.text(x + 0.25, yt - HH / 2, title, ha="left", va="center", fontsize=FS_HEAD,
                fontweight="bold", color="white", zorder=5)
    chip_x0 = x + PW
    if rq:
        w = 0.075 + 0.05 * len(rq)
        chip_x0 = x + PW - w - 0.05
        ax.add_patch(FancyBboxPatch((chip_x0, yt - HH / 2 - 0.065), w, 0.13,
                                    boxstyle="round,pad=0,rounding_size=0.055", fc="white",
                                    ec="none", alpha=0.95, zorder=4))
        ax.text(chip_x0 + w / 2, yt - HH / 2 - 0.003, rq, ha="center", va="center",
                fontsize=5.8, fontweight="bold", color=col, zorder=5)
    headers.append((t, chip_x0, f"panel {num}"))
    return x, yt, x + 0.07, yt - HH - 0.05, PW - 0.14


def bullet(x, y, kind):
    if kind == "s":
        ax.add_patch(Polygon([(x, y + 0.048), (x + 0.048, y), (x, y - 0.048), (x - 0.048, y)],
                             closed=True, fc=SAMPLE, ec="none", zorder=4))
    else:
        ax.add_patch(Circle((x, y), 0.038, fc=CHECK, ec="none", zorder=4))
    ax.text(x, y - 0.002, "✓", ha="center", va="center", fontsize=4.4, color="white",
            fontweight="bold", zorder=5)


def checklist(c_x, items, y0):
    y, LS = y0, 0.113
    for text, kind in items:
        lines = text.split("\n")
        bullet(c_x + 0.11, y, kind)
        for k, line in enumerate(lines):
            reg(ax.text(c_x + 0.19, y - k * LS, line, ha="left", va="center", fontsize=FS_BODY,
                        color=INK, zorder=5))
        y -= LS * len(lines) + 0.03
    return y


def block_arrow(xa, yc, col):
    L, w, hw = GAP - 0.05, 0.055, 0.105
    x0 = xa + 0.025
    pts = [(x0, yc + w), (x0 + L * 0.5, yc + w), (x0 + L * 0.5, yc + hw), (x0 + L, yc),
           (x0 + L * 0.5, yc - hw), (x0 + L * 0.5, yc - w), (x0, yc - w)]
    ax.add_patch(Polygon(pts, closed=True, fc=col, ec="none", alpha=0.9, zorder=1))


def elbow(r_from, c_from, c_to, col="#8a8a8a"):
    yb = ROWY[r_from] - PH
    ym = yb - RG / 2
    xs, xe = COLX[c_from] + PW / 2, COLX[c_to] + PW / 2
    ax.plot([xs, xs, xe, xe], [yb, ym, ym, yb - RG + 0.045], color=col, lw=1.2,
            solid_joinstyle="round", zorder=1)
    ax.add_patch(Polygon([(xe - 0.05, yb - RG + 0.07), (xe + 0.05, yb - RG + 0.07), (xe, yb - RG + 0.005)],
                         closed=True, fc=col, ec="none", zorder=1))


def row_label(r, letter, label):
    col = ROWS[r][0]
    yt = ROWY[r]
    ax.add_patch(FancyBboxPatch((LBL_X, yt - PH), LBL_W, PH, boxstyle="round,pad=0,rounding_size=0.06",
                                fc=col, ec="none", zorder=2))
    cx = LBL_X + LBL_W / 2
    ax.add_patch(Circle((cx, yt - 0.15), 0.092, fc="white", ec="none", zorder=3))
    ax.text(cx, yt - 0.153, letter, ha="center", va="center", fontsize=7.4, fontweight="bold",
            color=col, zorder=4)
    ax.text(cx, yt - 0.27 - (PH - 0.27) / 2, label, ha="center", va="center", rotation=90,
            fontsize=7.2, fontweight="bold", color="white", zorder=4)


def thumb_rgba(arr, colours, factor):
    h, w = arr.shape
    h2, w2 = h // factor, w // factor
    a = arr[:h2 * factor, :w2 * factor].reshape(h2, factor, w2, factor)
    rgb = np.zeros((h2, w2, 3)); inside = np.zeros((h2, w2))
    for code, colr in colours.items():
        frac = (a == code).mean(axis=(1, 3))
        rgb += frac[..., None] * hexrgb(colr)
        inside += frac
    rgba = np.zeros((h2, w2, 4))
    ok = inside > 0
    rgba[ok, :3] = rgb[ok] / inside[ok, None]
    rgba[..., 3] = np.clip(inside * 1.6, 0, 1)
    return rgba


def show_img(img, x, y, w, h=None):
    if h is None:
        h = w * img.shape[0] / img.shape[1]
    ax.imshow(img, extent=(x, x + w, y, y + h), zorder=5, interpolation="lanczos")
    return h


def label(x, y, s, **kw):
    kw.setdefault("fontsize", FS_TINY); kw.setdefault("color", MUTED)
    kw.setdefault("ha", "center"); kw.setdefault("va", "top")
    return reg(ax.text(x, y, s, zorder=6, **kw))


def clean(a, keep=("bottom", "left")):
    for s in ("top", "right", "bottom", "left"):
        a.spines[s].set_visible(s in keep)
    a.set_xticks([]); a.set_yticks([])


row_label(0, "A", "Data and detectors")
row_label(1, "B", "Evaluation design")
row_label(2, "C", "Analysis")
for r in range(3):
    for c in range(2):
        block_arrow(COLX[c] + PW, ROWY[r] - HH - (PH - HH) / 2, ROWS[r][0])
elbow(0, 2, 0)
elbow(1, 2, 0)
TC = D["truecolour"]
rng = np.random.default_rng(7)
BUL = lambda gt: gt - G_H - 0.07

# ------------------------------------------------------------------ 1 Inputs
x, yt, gx, gt, gw = panel(0, 0, 1, "Inputs")
sw, sdx, sdh, step = 0.40, 0.17, 0.20, 0.075
base_y = gt - G_H + 0.27
for k, im in enumerate([TC[1], TC[4], TC[2], TC[3]]):
    y0 = base_y + k * step
    M = np.array([[sw, sdx, gx], [0, sdh, y0], [0, 0, 1]])
    ax.imshow(im[150:450, 150:450], extent=(0, 1, 0, 1), transform=Affine2D(M) + ax.transData,
              zorder=5 + k, interpolation="lanczos")
    ax.add_patch(Polygon([(gx, y0), (gx + sw, y0), (gx + sw + sdx, y0 + sdh), (gx + sdx, y0 + sdh)],
                         closed=True, fc="none", ec="white", lw=0.6, zorder=5 + k))
label(gx + (sw + sdx) / 2, base_y - 0.03, "Sentinel-2\nL2A", linespacing=1.0)
daa_cols = {1: "#d6d6d6", 3: "#d6d6d6", 2: "#2c6db0", 4: "#2c6db0"}
t1 = thumb_rgba(D["err_ROI1"], daa_cols, 12)
t2 = thumb_rgba(D["err_ROI2"], daa_cols, 26)
x1 = gx + sw + sdx + 0.08
show_img(t1, x1, base_y, 0.46)
label(x1 + 0.23, base_y - 0.03, "ROI-1\ncalibration", linespacing=1.0)
x2 = x1 + 0.55
show_img(t2, x2, base_y + 0.03, 0.54)
label(x2 + 0.27, base_y - 0.03, "ROI-2\ntest", linespacing=1.0)
checklist(x, [("45 acquisitions, 28 Apr–11 May 2024", "w"),
              ("DAA (blue) rasterised to the 10 m grid", "w"),
              ("MapBiomas 2023 land cover", "w"),
              ("23 municipalities, 18 189 km²", "w")], BUL(gt))

# ------------------------------------------------------------------ 2 Composites and masks
x, yt, gx, gt, gw = panel(0, 1, 2, "Composites and masks", "RQ4")
ts, tg = 0.185, 0.032
ty = gt - 0.40
dates = ["29 Apr", "1 May", "4 May", "6 May", "9 May", "11 May"]
cloud = [0.55, 1.0, 0.6, 0.0, 0.35, 1.0]
label(gx + (6 * ts + 5 * tg) / 2, gt - 0.02, "Observations after cloud masking", style="italic")
for k in range(6):
    xx = gx + k * (ts + tg)
    ax.imshow(TC[4][100 + 40 * k:100 + 40 * k + 220, 120:340], extent=(xx, xx + ts, ty, ty + ts),
              zorder=5, interpolation="lanczos")
    clip = Rectangle((xx, ty), ts, ts, transform=ax.transData)
    if cloud[k] >= 1:
        ax.add_patch(Rectangle((xx, ty), ts, ts, fc="white", ec="none", alpha=0.93, zorder=6))
    elif cloud[k] > 0:
        for _ in range(int(cloud[k] * 7)):
            cx, cy = xx + rng.uniform(0.02, ts - 0.02), ty + rng.uniform(0.02, ts - 0.02)
            el = Ellipse((cx, cy), rng.uniform(0.07, 0.12), rng.uniform(0.05, 0.08),
                         fc="white", ec="none", alpha=0.92, zorder=6)
            ax.add_patch(el)
            el.set_clip_path(clip)
    ax.add_patch(Rectangle((xx, ty), ts, ts, fc="none", ec="#9a9a9a", lw=0.4, zorder=7))
    d, m = dates[k].split()
    label(xx + ts / 2, ty - 0.02, d + "\n" + m, linespacing=0.95,
          fontweight="bold" if k == 3 else "normal", color=INK if k == 3 else MUTED)
xe = gx + 6 * ts + 5 * tg
ax.annotate("", xy=(xe + 0.13, ty + ts / 2), xytext=(xe + 0.015, ty + ts / 2),
            arrowprops=dict(arrowstyle="-|>", color=ROWS[0][0], lw=0.9, mutation_scale=6), zorder=7)
cs = 0.29
ax.imshow(TC[4][60:540, 60:540], extent=(xe + 0.15, xe + 0.15 + cs, ty - 0.05, ty - 0.05 + cs),
          zorder=5, interpolation="lanczos")
ax.add_patch(Rectangle((xe + 0.15, ty - 0.05), cs, cs, fc="none", ec=ROWS[0][0], lw=0.7, zorder=7))
label(xe + 0.15 + cs / 2, ty - 0.07, "Composite", color=INK)
checklist(x, [("Median, QA60 (primary)", "w"),
              ("Median, Cloud Score+ (cs_cdf ≥ 0.60)", "w"),
              ("Single date, 6 May, Cloud Score+", "w"),
              ("Maximum MNDWI, Cloud Score+", "w")], BUL(gt))

# ------------------------------------------------------------------ 3 Detectors
x, yt, gx, gt, gw = panel(0, 2, 3, "Detectors", "RQ1")
names = ["NDWI", "IMP", r"AWEI$_{\rm sh}$", "TCW", "NDVI", "SAVI"]
wts = np.array([3.72, -2.67, 2.69, -1.77, -2.67, 3.30])
label(gx + gw / 2, gt - 0.02, "FLOOD-HI weights, Eq. (1)", style="italic")
a = inset(gx + 0.46, gt - G_H + 0.05, gw - 0.82, G_H - 0.22)
yy = np.arange(len(wts))[::-1]
a.barh(yy, wts, height=0.64, color=[ROWS[0][0] if v > 0 else "#9fb6cc" for v in wts])
a.axvline(0, color="#555555", lw=0.5)
a.set_xlim(-3.0, 3.9); a.set_ylim(-0.6, len(wts) - 0.4)
clean(a, keep=())
a.set_yticks(yy); a.set_yticklabels(names, fontsize=FS_TINY, color=INK)
a.tick_params(axis="y", length=0, pad=1.5)
for yv, v in zip(yy, wts):
    reg(a.text(4.1, yv, f"{v:+.2f}".replace("-", "−"), va="center", ha="left", fontsize=FS_TINY,
               color=ROWS[0][0] if v > 0 else "#6f88a3", clip_on=False))
checklist(x, [("Indices: NDWI, MNDWI, AWEI$_{\\rm sh}$, TCW", "w"),
              ("Rules: B11 < 0.12; B6, B7, B8 < 0.20", "w"),
              ("With and without rules; rules alone", "w"),
              ("Classifiers: OLS, LDA, logistic, RF", "s")], BUL(gt))

# ------------------------------------------------------------------ 4 Evaluation population
x, yt, gx, gt, gw = panel(1, 0, 4, "Evaluation population", "RQ2")
agr_cols = {1: AGR["TN"], 2: AGR["FN"], 3: AGR["FP"], 4: AGR["TP"]}
ta = thumb_rgba(D["err_ROI1"], agr_cols, 9)
th = 0.60
tw = th * ta.shape[1] / ta.shape[0]
ty0 = gt - G_H + 0.17
show_img(ta, gx, ty0, tw, th)
label(gx + tw / 2, ty0 - 0.015, "ROI-1")
cw, chh = 0.26, 0.21
mx = x + PW - 0.46 - cw
my = gt - 0.17
label(mx + cw, gt - 0.005, "Reference (DAA)", color=INK)
for j, lab in enumerate(["1", "0"]):
    label(mx + cw / 2 + j * cw, gt - 0.09, lab)
cells = [[("TP", 3, AGR["TP"]), ("FP", 2, AGR["FP"])], [("FN", 1, AGR["FN"]), ("TN", 0, AGR["TN"])]]
for i in range(2):
    for j in range(2):
        lab, code, colr = cells[i][j]
        yy0 = my - (i + 1) * chh
        ax.add_patch(Rectangle((mx + j * cw, yy0), cw, chh, fc=colr, ec="white", lw=0.8, zorder=5))
        ax.text(mx + j * cw + cw / 2, yy0 + chh / 2, f"{lab}\n{code}", ha="center", va="center",
                fontsize=FS_TINY, fontweight="bold", zorder=6, linespacing=0.95,
                color="white" if lab != "TN" else INK)
    reg(ax.text(mx - 0.035, my - (i + 0.5) * chh, ["1", "0"][i], ha="right", va="center",
                fontsize=FS_TINY, color=MUTED, zorder=6))
reg(ax.text(mx - 0.14, my - chh, "Prediction", rotation=90, ha="center", va="center", fontsize=FS_TINY,
            color=INK, zorder=6))
label(mx + cw, my - 2 * chh - 0.025, "code = 2 × prediction\n+ reference", linespacing=1.0)
checklist(x, [("Every valid 10 m pixel, EPSG:32722", "w"),
              ("Same valid pixels for all\nwall-to-wall detectors", "w"),
              ("Rule-rejected pixels kept as negatives", "w"),
              ("Identical totals checked per method", "w")], BUL(gt))

# ------------------------------------------------------------------ 5 Exports
x, yt, gx, gt, gw = panel(1, 1, 5, "Exported tables", "RQ2")


def table_icon(x0, y0, w, h, col):
    ax.add_patch(FancyBboxPatch((x0, y0), w, h, boxstyle="round,pad=0,rounding_size=0.02",
                                fc="white", ec=col, lw=0.7, zorder=5))
    ax.add_patch(Rectangle((x0, y0 + h * 0.78), w, h * 0.22, fc=col, ec="none", zorder=5))
    for k in range(1, 4):
        ax.plot([x0, x0 + w], [y0 + h * 0.78 * k / 4] * 2, color=col, lw=0.35, alpha=0.6, zorder=6)
    for k in range(1, 3):
        ax.plot([x0 + w * k / 3] * 2, [y0, y0 + h * 0.78], color=col, lw=0.35, alpha=0.6, zorder=6)


iy = gt - G_H + 0.27
table_icon(gx + 0.02, iy, 0.28, 0.34, ROWS[1][0])
label(gx + 0.16, iy - 0.03, "Confusion\ncounts", linespacing=1.0)
e, p, n = D["hist_edges"], D["hist_pos"], D["hist_neg"]
k = 5
nb = len(e) // k
ec = e[:nb * k:k] + 0.025
pp = p[:nb * k].reshape(nb, k).sum(1); nn = n[:nb * k].reshape(nb, k).sum(1)
a = inset(gx + 0.38, iy - 0.005, 0.96, 0.40)
sel = (ec > -1.4) & (ec < 1.6)
a.fill_between(ec[sel], nn[sel] / nn.sum(), step="mid", color=GREY, lw=0)
a.plot(ec[sel], pp[sel] / pp.sum(), color=NAVY, lw=0.9, drawstyle="steps-mid")
a.set_xlim(-1.4, 1.6); a.set_ylim(0, max(nn.max() / nn.sum(), pp.max() / pp.sum()) * 1.12)
clean(a, keep=("bottom",))
reg(a.text(0.0, 1.02, "outside DAA", transform=a.transAxes, fontsize=FS_MIN, color="#6f6f6f", va="bottom"))
reg(a.text(1.0, 1.02, "inside DAA", transform=a.transAxes, fontsize=FS_MIN, color=NAVY, va="bottom",
           ha="right"))
label(gx + 0.86, iy - 0.03, "Class-conditional\nhistograms", linespacing=1.0)
px0, py0, pr = gx + gw - 0.15, iy + 0.17, 0.15
ax.add_patch(Circle((px0, py0), pr, fc=ROWS[1][1], ec=ROWS[1][0], lw=0.6, zorder=5))
pts = rng.uniform(-1, 1, (60, 2)); pts = pts[(pts ** 2).sum(1) < 0.8]
ax.scatter(px0 + pts[:, 0] * pr, py0 + pts[:, 1] * pr, s=1.6, c=SAMPLE, zorder=6, lw=0)
label(px0, iy - 0.03, "Sample\npoints", linespacing=1.0)
checklist(x, [("Confusion counts per municipality", "w"),
              ("Histograms by DAA class, rule status\nand common valid area", "w"),
              ("5763 ROI-1 and 5328 ROI-2 points", "s")], BUL(gt))

# ------------------------------------------------------------------ 6 Thresholds
x, yt, gx, gt, gw = panel(1, 2, 6, "Threshold protocols", "RQ1–2")
a = inset(gx + 0.18, gt - G_H + 0.15, gw - 0.24, G_H - 0.20)
sel = (e > -1.3) & (e < 1.3)
s1, s2 = D["sweep_ROI1"], D["sweep_ROI2"]
a.plot(e[sel], s1[sel], color=ROWS[1][0], lw=1.0)
a.plot(e[sel], s2[sel], color="#7d7d7d", lw=1.0, ls=(0, (3, 1.5)))
t = float(D["t_star"])
i = int(np.argmin(abs(e - t)))
a.axvline(t, color=ROWS[1][0], lw=0.5, ls=":")
a.axvline(0, color="#b0b0b0", lw=0.4)
a.plot([t], [s1[i]], "o", ms=2.6, color=ROWS[1][0])
a.plot([t], [s2[i]], "o", ms=2.6, color="#7d7d7d")
a.annotate("", xy=(t + 0.02, s2[i] + 0.012), xytext=(t + 0.02, s1[i] - 0.012),
           arrowprops=dict(arrowstyle="-|>", color=SAMPLE, lw=0.8, mutation_scale=5))
reg(a.text(t - 0.07, (s1[i] + s2[i]) / 2, "transfer", fontsize=FS_MIN, color="#b5651d", va="center",
           ha="right"))
from matplotlib.lines import Line2D
leg = a.legend(handles=[Line2D([], [], color=ROWS[1][0], lw=1.0, label="ROI-1 (calibration)"),
                        Line2D([], [], color="#7d7d7d", lw=1.0, ls=(0, (3, 1.5)), label="ROI-2 (test)")],
               loc="lower left", fontsize=FS_MIN, frameon=True, facecolor="white", edgecolor="none",
               framealpha=1, handlelength=1.6, handletextpad=0.4, borderpad=0.25, labelspacing=0.2,
               borderaxespad=0.15)
leg.set_zorder(10)
reg(a.text(0.03, 0.80, "0", fontsize=FS_MIN, color="#8a8a8a", ha="left", va="top"))
a.set_xlim(-1.3, 1.3); a.set_ylim(0.56, 0.80)
clean(a)
a.set_xlabel("FLOOD-HI threshold", fontsize=FS_TINY, labelpad=1, color=MUTED)
a.set_ylabel("$F_1$", fontsize=FS_TINY, labelpad=1, color=MUTED)
checklist(x, [("Zero: index > 0 (original rule)", "w"),
              ("Transferred: $F_1$-optimal in ROI-1,\napplied unchanged to ROI-2", "w"),
              ("Otsu: per domain, without labels", "w"),
              ("Oracle: ROI-2 optimum, diagnostic", "w")], BUL(gt))

# ------------------------------------------------------------------ 7 Metrics
x, yt, gx, gt, gw = panel(2, 0, 7, "Agreement metrics", "RQ1")
a = inset(gx + 0.15, gt - G_H + 0.15, 0.62, 0.62)
for idx, colr, lw in (("NDWI", "#c7c7c7", 0.6), ("TCW", "#c7c7c7", 0.6), ("AWEI", "#c7c7c7", 0.6),
                      ("MNDWI", "#9e9e9e", 0.7), ("FLOODHI", NAVY, 1.1)):
    r_ = D[f"roc_{idx}"]
    a.plot(r_[0], r_[1], color=colr, lw=lw)
a.plot([0, 1], [0, 1], color="#bbbbbb", lw=0.4, ls="--")
a.set_xlim(0, 1); a.set_ylim(0, 1)
clean(a)
a.set_xlabel("FPR", fontsize=FS_TINY, labelpad=1, color=MUTED)
a.set_ylabel("TPR", fontsize=FS_TINY, labelpad=1, color=MUTED)
reg(a.text(0.35, 0.12, "ROC, ROI-2", fontsize=FS_MIN, color=MUTED, transform=a.transAxes))
fx = gx + 0.88
for k, s in enumerate((r"$F_1 = \frac{2\,TP}{2\,TP + FP + FN}$", r"$IoU = \frac{TP}{TP + FP + FN}$",
                       r"$M = \frac{|\mu_1 - \mu_0|}{\sigma_1 + \sigma_0}$")):
    reg(ax.text(fx, gt - 0.13 - k * 0.25, s, fontsize=6.3, color=INK, va="center", zorder=6))
checklist(x, [("Precision, recall, $F_1$, IoU, kappa", "w"),
              ("Quantity and allocation disagreement", "w"),
              ("AUC and M-statistic of separability", "w"),
              ("Read as agreement with the DAA", "w")], BUL(gt))

# ------------------------------------------------------------------ 8 Uncertainty
x, yt, gx, gt, gw = panel(2, 1, 8, "Uncertainty", "RQ2")
b = D["boot"]
a = inset(gx + 0.03, gt - G_H + 0.15, 0.98, 0.60)
lo, hi = np.percentile(b, [2.5, 97.5])
cnt, edges = np.histogram(b, bins=40)
a.bar(edges[:-1], cnt, width=np.diff(edges), align="edge", color="#c9c3df", lw=0)
ci = (edges[:-1] >= lo) & (edges[1:] <= hi)
a.bar(edges[:-1][ci], cnt[ci], width=np.diff(edges)[ci], align="edge", color=ROWS[2][0], alpha=0.75, lw=0)
a.axvline(0, color="#b03030", lw=0.6, ls="--")
clean(a, keep=("bottom",))
a.set_xlabel(r"paired $\Delta F_1$", fontsize=FS_TINY, labelpad=1, color=MUTED)
a.annotate("", xy=(lo, cnt.max() * 1.08), xytext=(hi, cnt.max() * 1.08),
           arrowprops=dict(arrowstyle="<->", color=ROWS[2][0], lw=0.6, mutation_scale=4))
reg(a.text((lo + hi) / 2, cnt.max() * 1.13, "95% CI", fontsize=FS_MIN, ha="center", color=ROWS[2][0]))
reg(a.text(0, cnt.max() * 0.98, " 0", fontsize=FS_MIN, color="#b03030", va="top"))
a.set_ylim(0, cnt.max() * 1.36)
gx2 = gx + 1.10
label(gx2 + 0.32, gt - 0.02, "One replicate", style="italic")
draws = np.bincount(np.random.default_rng(1).integers(0, 14, 14), minlength=14)
for k in range(14):
    cx, cy = gx2 + (k % 4) * 0.165, gt - 0.24 - (k // 4) * 0.125
    shade = ["#ffffff", "#c9c3df", "#8f84bd", ROWS[2][0]][min(draws[k], 3)]
    ax.add_patch(Rectangle((cx, cy), 0.14, 0.105, fc=shade, ec=ROWS[2][0], lw=0.4, zorder=5))
    if draws[k] > 1:
        ax.text(cx + 0.07, cy + 0.052, f"×{draws[k]}", fontsize=FS_MIN, ha="center",
                va="center", color="white", zorder=6)
label(gx2 + 0.32, gt - 0.24 - 3 * 0.125 - 0.02, "14 ROI-2\nmunicipalities", linespacing=1.0)
checklist(x, [("Municipality bootstrap, 2000 replicates", "w"),
              ("95% CI for $F_1$ and paired differences", "w"),
              ("Exact sign test of municipal wins", "w"),
              ("Test-point bootstrap, 2000 replicates", "s")], BUL(gt))

# ------------------------------------------------------------------ 9 Diagnosis
x, yt, gx, gt, gw = panel(2, 2, 9, "Diagnosis", "RQ3–4")
with open(RECALL_CSV, newline="", encoding="utf-8") as f:
    R = {r["land_cover"]: float(r["recall"]) for r in csv.DictReader(f)
         if r["domain"] == "ROI2" and r["composite"] == "mediana_qa60" and r["detector"] == "FLOOD-HI + masks"}
label(gx + gw / 2, gt - 0.02, "ROI-2; zero index threshold", style="italic", color=INK)
tl = thumb_rgba(D["lc_ROI2"], LC, 14)
th = 0.42
tw = th * tl.shape[1] / tl.shape[0]
show_img(tl, gx - 0.02, gt - G_H + 0.20, tw, th)
label(gx - 0.02 + tw / 2, gt - G_H + 0.18, "Land cover")
rec = [("Water bodies", R["Water bodies"], LC[2]), ("Irrigated rice", R["Irrigated rice"], LC[6]),
       ("Farming", R["Farming and pasture"], LC[3]), ("Natural veg.", R["Natural vegetation"], LC[4]),
       ("Urban", R["Urban"], LC[1])]
bx0 = gx + tw + 0.62
a = inset(bx0, gt - G_H + 0.10, x + PW - 0.22 - bx0, G_H - 0.36)
yy = np.arange(len(rec))[::-1]
a.barh(yy, [r_[1] for r_ in rec], color=[r_[2] for r_ in rec], height=0.72, ec="#888888", lw=0.25)
a.set_xlim(0, 1); a.set_ylim(-0.55, len(rec) - 0.45)
clean(a, keep=("left",))
a.set_yticks(yy); a.set_yticklabels([r_[0] for r_ in rec], fontsize=FS_MIN, color=INK)
a.tick_params(axis="y", length=0, pad=1.5)
for yv, r_ in zip(yy, rec):
    reg(a.text(r_[1] + 0.04, yv, f"{r_[1]:.2f}", fontsize=FS_MIN, va="center", color=INK, clip_on=False))
label((gx + tw + 0.05 + x + PW - 0.05) / 2, gt - 0.17, "Recall, FLOOD-HI + rules", color=MUTED)
checklist(x, [("Recall by land cover and by number\nof clear observations", "w"),
              ("Boundary buffers and terrain screen", "w"),
              ("Observed vs expected recall by\nmunicipality; example windows", "w")], BUL(gt))

# ------------------------------------------------------------------ legend
ly, lx = 0.11, PX0 + 0.02
bullet(lx, ly, "w")
ax.text(lx + 0.08, ly, "Wall-to-wall, every valid pixel", fontsize=FS_BODY, va="center", color=INK)
lx2 = lx + 1.95
bullet(lx2, ly, "s")
ax.text(lx2 + 0.08, ly, "Sample-based, paired points", fontsize=FS_BODY, va="center", color=INK)
lx3 = lx2 + 1.8
ax.add_patch(FancyBboxPatch((lx3 - 0.02, ly - 0.065), 0.29, 0.13, boxstyle="round,pad=0,rounding_size=0.055",
                            fc="white", ec="#777777", lw=0.6, zorder=4))
ax.text(lx3 + 0.125, ly - 0.002, "RQ", fontsize=5.8, fontweight="bold", color="#555555",
        ha="center", va="center", zorder=5)
ax.text(lx3 + 0.34, ly, "Research question addressed", fontsize=FS_BODY, va="center", color=INK)

# ------------------------------------------------------------------ checks
fig.canvas.draw()
rend = fig.canvas.get_renderer()
inv = ax.transData.inverted()
problems = 0
for t, x0, x1, name in checks:
    bb = t.get_window_extent(rend)
    (l, _), (rr, _) = inv.transform((bb.x0, bb.y0)), inv.transform((bb.x1, bb.y1))
    if l < x0 + 0.02 or rr > x1 - 0.02:
        problems += 1
        print(f"OUTSIDE {name}: {t.get_text()!r} spans {l - x0:.3f}..{rr - x0:.3f} of {PW:.3f}")
for t, chip_x0, name in headers:
    bb = t.get_window_extent(rend)
    right = inv.transform((bb.x1, bb.y1))[0]
    gap = chip_x0 - right
    print(f"{name}: gap between title and RQ tag {gap:.3f} in")
    if gap < 0.08:
        problems += 1
for a_ in fig.axes[1:]:
    for t in a_.get_yticklabels():
        if t.get_text() and t.get_fontsize() < FS_MIN:
            print("small tick", t.get_text())
small = [t for t in fig.findobj(matplotlib.text.Text) if t.get_text().strip() and t.get_visible()
         and t.get_fontsize() < FS_MIN and t.get_text() != "✓"]
print("texts below", FS_MIN, "pt:", sorted({(round(t.get_fontsize(), 1), t.get_text()) for t in small}))
print("problems", problems)
fig.savefig(OUT, dpi=300, facecolor="white")
print("saved", OUT)
