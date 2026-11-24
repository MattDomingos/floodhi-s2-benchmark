"""Composite comparison (Fig. 6c) and Data S1 - thresholds, metrics and
confusion counts for every detector, composite, evaluation population,
domain and thresholding protocol.

Input : data/exports/ROI{1,2}_v3_B_histogramas.geojson (script 02, export B)
        data/exports/ROI{1,2}_C_matrizes_confusao.csv (script 01, export C)
Output: results/data_S1_thresholds_metrics_counts.csv,
        results/composites_transferred_f1.csv
"""
import pandas as pd

from common import COMPOSITES, EXPORTS, INDICES, RESULTS, label
from floodhi_eval import CONFIGS, read_confusion_csv, read_histograms, scores

H1 = read_histograms(EXPORTS / "ROI1_v3_B_histogramas.geojson")
H2 = read_histograms(EXPORTS / "ROI2_v3_B_histogramas.geojson")
POP = {"all": "all valid pixels", "common": "valid in all four composites"}

rows = []


def add(domain, comp, area, method, protocol, threshold, c):
    s = scores(*c)
    rows.append(dict(domain=domain, composite=comp, population=POP[area], method=method,
                     protocol=protocol, threshold=threshold, TP=c[0], FP=c[1], FN=c[2], TN=c[3],
                     N=s["n"], precision=s["precision"], recall=s["recall"], F1=s["f1"],
                     IoU=s["iou"], kappa=s["kappa"]))


for comp in COMPOSITES:
    for area in ("all", "common"):
        for i in INDICES:
            h1, h2 = H1[comp, i], H2[comp, i]
            for masked in (False, True):
                m = label(i, masked)
                t_tr, _ = h1.best_threshold(masked, area)     # each composite gets its own threshold
                t_or, _ = h2.best_threshold(masked, area)
                t_otsu = h2.otsu(area)
                add("ROI-1 (calibration)", comp, area, m, "zero", 0.0, h1.confusion(0, masked, area))
                add("ROI-1 (calibration)", comp, area, m, "F1-optimal in ROI-1", t_tr, h1.confusion(t_tr, masked, area))
                add("ROI-2 (test)", comp, area, m, "zero", 0.0, h2.confusion(0, masked, area))
                add("ROI-2 (test)", comp, area, m, "transferred from ROI-1", t_tr, h2.confusion(t_tr, masked, area))
                add("ROI-2 (test)", comp, area, m, "Otsu (ROI-2, all valid values)", t_otsu, h2.confusion(t_otsu, masked, area))
                add("ROI-2 (test)", comp, area, m, "oracle (ROI-2 labels, diagnostic)", t_or, h2.confusion(t_or, masked, area))
        add("ROI-1 (calibration)", comp, area, "Masks only", "no threshold", float("nan"), H1[comp, "FLOODHI"].masks_only(area))
        add("ROI-2 (test)", comp, area, "Masks only", "no threshold", float("nan"), H2[comp, "FLOODHI"].masks_only(area))

# Earth Engine counts at the zero threshold (index > 0), as in Tables 5 and S4. The histogram
# rows above use index >= 0; the two differ only for pixels whose index value is exactly zero.
for roi, domain in (("ROI1", "ROI-1 (calibration)"), ("ROI2", "ROI-2 (test)")):
    totals = read_confusion_csv(EXPORTS / f"{roi}_C_matrizes_confusao.csv").sum(numeric_only=True)
    for code, name in CONFIGS.items():
        c = tuple(totals[f"{code}_{k}"] for k in ("TP", "FP", "FN", "TN"))
        if name == "Masks only":
            add(domain, "mediana_qa60", "all", name, "no threshold, Earth Engine counts", float("nan"), c)
        else:
            add(domain, "mediana_qa60", "all", name, "zero, Earth Engine counts (index > 0)", 0.0, c)

data = pd.DataFrame(rows)
# Fixed precision, so that the file is byte-identical across platforms and library versions
# (the last digits of the float sums otherwise depend on the summation order).
data["threshold"] = data["threshold"].round(4)
data[["TP", "FP", "FN", "TN", "N"]] = data[["TP", "FP", "FN", "TN", "N"]].round(3)
data[["precision", "recall", "F1", "IoU", "kappa"]] = data[["precision", "recall", "F1", "IoU", "kappa"]].round(6)
data.to_csv(RESULTS / "data_S1_thresholds_metrics_counts.csv", index=False, lineterminator="\n")
print(f"Data S1: {len(data)} rows")

sel = data[(data.population == POP["common"]) &
           (((data.domain == "ROI-2 (test)") & data.protocol.isin(["transferred from ROI-1", "no threshold"])))]
fig6c = sel.pivot_table(index="method", columns="composite", values="F1")[list(COMPOSITES)]
fig6c.to_csv(RESULTS / "composites_transferred_f1.csv", lineterminator="\n")
print("\nF1 in ROI-2, transferred thresholds, area valid in all composites (Fig. 6c)\n", fig6c.round(3).to_string())
opt = data[(data.population == POP["common"]) & (data.protocol == "F1-optimal in ROI-1")]
print("\nF1 at the ROI-1 optimum (calibration fit)\n",
      opt.pivot_table(index="method", columns="composite", values="F1")[list(COMPOSITES)].round(3).to_string())
