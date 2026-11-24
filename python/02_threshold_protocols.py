"""Tables 4, 6, S6 and S7 - separability, threshold protocols, municipality
bootstrap and sensitivity to the histogram bin width (QA60 median composite,
all valid pixels).

Input : data/exports/ROI{1,2}_B_histogramas.geojson (script 01, export B)
Output: results/table4_separability.csv, results/table6_benchmark.csv,
        results/tableS6_protocols_roi2.csv, results/tableS7_bin_width.csv,
        results/transferred_thresholds.csv
"""
import numpy as np
import pandas as pd

from common import EXPORTS, INDICES, RESULTS, label
from floodhi_eval import municipality_bootstrap, read_histograms, scores

V = "mediana_qa60"
H1 = read_histograms(EXPORTS / "ROI1_B_histogramas.geojson")
H2 = read_histograms(EXPORTS / "ROI2_B_histogramas.geojson")

# Table 4 - class separability over all valid pixels
sep = pd.DataFrame([dict(index=i, auc_roi1=H1[V, i].auc(), auc_roi2=H2[V, i].auc(),
                         m_roi1=H1[V, i].m_statistic(), m_roi2=H2[V, i].m_statistic())
                    for i in INDICES])
sep.to_csv(RESULTS / "table4_separability.csv", index=False, lineterminator="\n")
print("Table 4\n", sep.round(3).to_string(index=False))

# Thresholds: zero, transferred from ROI-1, Otsu in ROI-2, oracle in ROI-2
rows, thresholds = [], {}
for i in INDICES:
    for masked in (True, False):
        t_tr, f1_roi1 = H1[V, i].best_threshold(masked)
        t_otsu = H2[V, i].otsu()
        t_or, _ = H2[V, i].best_threshold(masked)
        thresholds[label(i, masked)] = (i, masked, t_tr)
        row = dict(method=label(i, masked), f1_roi1_optimum=f1_roi1)
        for prot, t in (("zero", 0.0), ("transferred", t_tr), ("otsu", t_otsu), ("oracle", t_or)):
            s = scores(*H2[V, i].confusion(t, masked))
            row.update({f"{prot}_threshold": t, f"{prot}_f1": s["f1"], f"{prot}_iou": s["iou"]})
        rows.append(row)
s = scores(*H2[V, "FLOODHI"].masks_only())
rows.append(dict(method="Masks only", transferred_f1=s["f1"], transferred_iou=s["iou"]))
s6 = pd.DataFrame(rows)
s6.to_csv(RESULTS / "tableS6_protocols_roi2.csv", index=False, lineterminator="\n")
pd.DataFrame([dict(method=k, index=v[0], masked=v[1], threshold=v[2]) for k, v in thresholds.items()]
             ).to_csv(RESULTS / "transferred_thresholds.csv", index=False, lineterminator="\n")
print("\nTable S6 (ROI-2)\n", s6.round(3).to_string(index=False))

# Table 6 - transferred thresholds with municipality bootstrap (ROI-2)
muns = H2.municipalities()
counts = {}
for name, (i, masked, t) in thresholds.items():
    counts[name] = np.array([H2.by_municipality[V, i, m].confusion(t, masked) for m in muns])
counts["Masks only"] = np.array([H2.by_municipality[V, "FLOODHI", m].masks_only() for m in muns])
t6 = municipality_bootstrap(counts, reference="FLOOD-HI + masks", n_rep=2000, seed=1)
t6["threshold"] = t6.method.map({k: v[2] for k, v in thresholds.items()})
t6 = t6.sort_values("f1", ascending=False)
t6.to_csv(RESULTS / "table6_benchmark.csv", index=False, lineterminator="\n")
cols = ["method", "threshold", "precision", "recall", "f1", "f1_lo", "f1_hi", "iou", "kappa",
        "d_f1", "d_lo", "d_hi", "wins", "sign_p"]
print("\nTable 6 (ROI-2, municipality bootstrap)\n", t6[cols].round(3).to_string(index=False))

# FLOOD-HI + masks over the thresholds shown in Fig. 5b
e = H2[V, "FLOODHI"].edges
f = H2[V, "FLOODHI"].sweep(masked=True)
sel = (e >= -1.5) & (e < 0)
print(f"\nFLOOD-HI + masks, ROI-2, thresholds -1.5 to 0: F1 {f[sel].min():.3f} to {f[sel].max():.3f}")

# Table S7 - coarsen the bins by 2 and 4 and repeat the threshold transfer
rows = []
for factor in (1, 2, 4):
    res = {}
    for i, masked in [("FLOODHI", True), ("NDWI", True), ("MNDWI", True), ("AWEI", True),
                      ("TCW", True), ("FLOODHI", False)]:
        h1, h2 = H1[V, i].coarsen(factor), H2[V, i].coarsen(factor)
        t, _ = h1.best_threshold(masked)
        res[label(i, masked)] = (t, scores(*h2.confusion(t, masked))["f1"])
    ref = res["FLOOD-HI + masks"][1]
    for name, (t, f1v) in res.items():
        rows.append(dict(factor=factor, method=name, threshold=t, f1_roi2=f1v, d_f1=ref - f1v))
s7 = pd.DataFrame(rows)
s7.to_csv(RESULTS / "tableS7_bin_width.csv", index=False, lineterminator="\n")
print("\nTable S7\n", s7.pivot(index="method", columns="factor", values=["threshold", "f1_roi2", "d_f1"]).round(4).to_string())
