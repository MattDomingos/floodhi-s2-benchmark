"""Table S5 - agreement with pixels near the DAA boundary excluded.

Distance classes (script 03): 1 <= 15 m, 2 = 15-25 m, 3 = 25-35 m,
4 = 35-55 m, 5 > 55 m from the nearest pixel of the opposite DAA class.
Excluding a buffer of 10, 20, 30 or 50 m drops classes 1, 1-2, 1-3 or 1-4.

Input : data/exports/ROI{1,2}_v5_buffer_borda.geojson
Output: results/tableS5_boundary_buffer.csv
"""
import pandas as pd

from common import EXPORTS, RESULTS, ROIS
from floodhi_eval import read_grouped_sums, scores

KEEP = {0: [1, 2, 3, 4, 5], 10: [2, 3, 4, 5], 20: [3, 4, 5], 30: [4, 5], 50: [5]}
METHODS = {  # band prefix in the export -> method (thresholds transferred from ROI-1)
    "FHI_M_T": "FLOOD-HI + masks", "NDWI_M_T": "NDWI + masks", "MNDWI_M_T": "MNDWI + masks",
    "AWEI_M_T": "AWEIsh + masks", "TCW_M_T": "TCW + masks", "MASC": "Masks only",
    "FHI_T": "FLOOD-HI", "AWEI_T": "AWEIsh", "TCW_T": "TCW", "MNDWI_T": "MNDWI", "NDWI_T": "NDWI",
}

rows = []
for roi in ROIS:
    d = read_grouped_sums(EXPORTS / f"{roi}_v5_buffer_borda.geojson", "faixa")
    by = d.groupby("faixa").sum(numeric_only=True)
    for buffer, keep in KEEP.items():
        s = by.loc[by.index.isin(keep)].sum()
        row = dict(domain=roi, buffer_m=buffer,
                   valid_excluded=1 - s.n_valido / by.n_valido.sum(),
                   daa_excluded=1 - s.n_ref / by.n_ref.sum())
        for code, name in METHODS.items():
            row[name] = scores(*(s[f"{code}_{k}"] for k in ("TP", "FP", "FN", "TN")))["f1"]
        rows.append(row)
t = pd.DataFrame(rows)
t.to_csv(RESULTS / "tableS5_boundary_buffer.csv", index=False, lineterminator="\n")
print(t.round(3).T.to_string())
