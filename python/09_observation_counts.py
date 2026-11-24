"""Domains, valid coverage and cloud-free observations (Table 1, Section 4.1, Fig. 3c).

Table 1: area, DAA area and share, and valid coverage of each domain under each
composite (a pixel is valid when every band has at least one usable observation),
plus the area valid in all four composites (Section 3.2).
Fig. 3c: share of the domain area and of the DAA area with 0, 1, 2 and >= 3
QA60-clear observations.

Input : data/exports/ROI{1,2}_C_matrizes_confusao.csv (script 01, export C)
        data/exports/ROI{1,2}_v3_B_histogramas.geojson (script 02, export B)
Output: results/table1_domains.csv, results/observation_shares.csv
"""
import pandas as pd

from common import COMPOSITES, EXPORTS, RESULTS, ROIS
from floodhi_eval import read_histograms

PIXEL_KM2 = 1e-4                      # one 10 m pixel-equivalent
CLASSES = ["0", "1", "2", ">=3"]
domains, shares = [], []
for roi in ROIS:
    c = pd.read_csv(EXPORTS / f"{roi}_C_matrizes_confusao.csv")
    n_total, n_daa = c["n_total"].sum(), c["n_ref"].sum()
    row = dict(domain=roi, area_km2=n_total * PIXEL_KM2, daa_km2=n_daa * PIXEL_KM2,
               daa_share_pct=100 * n_daa / n_total)
    hist = read_histograms(EXPORTS / f"{roi}_v3_B_histogramas.geojson")
    for comp in COMPOSITES:
        counts = hist[comp, "FLOODHI"].counts        # every valid pixel, by class and mask
        row[f"valid_{comp}_pct"] = 100 * counts.sum() / n_total
    row["valid_all_four_pct"] = 100 * counts[:, :, 1, :].sum() / n_total
    domains.append(row)

    area = c[["obs0", "obs1", "obs2", "obs3mais"]].sum().to_numpy()
    daa = c[["ref_obs0", "ref_obs1", "ref_obs2", "ref_obs3mais"]].sum().to_numpy()
    for k, name in enumerate(CLASSES):
        shares.append(dict(domain=roi, cloud_free_observations=name,
                           share_of_domain_pct=100 * area[k] / area.sum(),
                           share_of_daa_pct=100 * daa[k] / daa.sum()))

table1 = pd.DataFrame(domains)
table1.round(4).to_csv(RESULTS / "table1_domains.csv", index=False, lineterminator="\n")
obs = pd.DataFrame(shares)
obs.round(4).to_csv(RESULTS / "observation_shares.csv", index=False, lineterminator="\n")

print("Table 1 - domains and valid coverage (%)")
print(table1.round(1).T.to_string(header=False))
print("\nFig. 3c - share (%) of each domain and of its DAA by number of QA60-clear observations")
print(obs.round(1).to_string(index=False))
