"""Table S8 - TCW with Crist (1985) and Sentinel-2 (Shi and Xu, 2019)
coefficients, and the class counts of the original FLOOD-HI training sample.

Input : data/exports/ROI{1,2}_v7_TCW_histogramas.geojson,
        data/exports/ROI1_v7_contagem_treino.csv (script 05),
        data/exports/ROI2_B_histogramas.geojson (FLOOD-HI + masks, for the paired difference)
Output: results/tableS8_tcw_coefficients.csv
"""
import numpy as np
import pandas as pd

from common import EXPORTS, RESULTS
from floodhi_eval import municipality_bootstrap, read_histograms, scores

V = "mediana_qa60"
T1 = read_histograms(EXPORTS / "ROI1_v7_TCW_histogramas.geojson")
T2 = read_histograms(EXPORTS / "ROI2_v7_TCW_histogramas.geojson")
rows, thr = [], {}
for index, name in (("TCW_CRIST", "TCW, Crist (1985)"), ("TCW_S2", "TCW, Shi and Xu (2019)")):
    for masked in (False, True):
        h1, h2 = T1[V, index], T2[V, index]
        t, f1_roi1 = h1.best_threshold(masked)
        thr[(index, masked)] = t
        z = scores(*h2.confusion(0, masked))
        tr = scores(*h2.confusion(t, masked))
        rows.append(dict(coefficients=name, masks=masked, auc_roi1=h1.auc(), auc_roi2=h2.auc(),
                         m_roi1=h1.m_statistic(), m_roi2=h2.m_statistic(), f1_zero_roi2=z["f1"],
                         threshold=t, f1_roi1_optimum=f1_roi1, f1_transferred_roi2=tr["f1"],
                         precision_roi2=tr["precision"], recall_roi2=tr["recall"]))
t8 = pd.DataFrame(rows)
t8.to_csv(RESULTS / "tableS8_tcw_coefficients.csv", index=False, lineterminator="\n")
print(t8.round(3).to_string(index=False))

# Paired municipality bootstrap in ROI-2 (transferred thresholds, with masks)
H1 = read_histograms(EXPORTS / "ROI1_B_histogramas.geojson")
H2 = read_histograms(EXPORTS / "ROI2_B_histogramas.geojson")
t_fhi, _ = H1[V, "FLOODHI"].best_threshold(True)
muns = T2.municipalities()
counts = {
    "FLOOD-HI + masks": np.array([H2.by_municipality[V, "FLOODHI", m].confusion(t_fhi, True) for m in muns]),
    "TCW S2 + masks": np.array([T2.by_municipality[V, "TCW_S2", m].confusion(thr["TCW_S2", True], True) for m in muns]),
    "TCW Crist + masks": np.array([T2.by_municipality[V, "TCW_CRIST", m].confusion(thr["TCW_CRIST", True], True) for m in muns]),
}
b = municipality_bootstrap(counts, reference="FLOOD-HI + masks", seed=1)
print("\n", b[["method", "f1", "d_f1", "d_lo", "d_hi", "wins", "sign_p"]].round(4).to_string(index=False))
b2 = municipality_bootstrap({k: counts[k] for k in ("TCW S2 + masks", "TCW Crist + masks")},
                            reference="TCW S2 + masks", seed=1)
print(b2[["method", "d_f1", "d_lo", "d_hi"]].round(4).to_string(index=False))

train = pd.read_csv(EXPORTS / "ROI1_v7_contagem_treino.csv").iloc[0]
print(f"\nOriginal training sample (seed 42, 30 m): {train.n_validos} valid points, "
      f"{train.n_inundados} flooded ({train.n_inundados / train.n_validos:.1%}), {train.n_secos} non-flooded")
