"""Terrain screen of the DAA (comment on mass movements) - share of the DAA
and of the omissions of FLOOD-HI + masks (zero threshold) on steep slopes high
above the drainage, where inundation is unlikely.

Classes (script 06): slope 0 <5, 1 5-10, 2 10-15, 3 15-20, 4 >=20 degrees;
HAND 0 <5, 1 5-10, 2 10-20, 3 20-30, 4 >=30 m; class = 5 * slope + HAND.

Input : data/exports/ROI{1,2}_v8_relevo_daa.geojson
Output: results/tableS9_terrain_screen.csv, results/terrain_screen_municipalities.csv
"""
import pandas as pd

from common import EXPORTS, RESULTS, ROIS
from floodhi_eval import read_grouped_sums

SCREENS = {  # name -> (minimum slope class, minimum HAND class)
    "slope >= 15 deg and HAND >= 20 m": (3, 3),
    "slope >= 10 deg and HAND >= 10 m": (2, 2),
    "slope >= 20 deg and HAND >= 30 m": (4, 4),
}

rows, mun_rows = [], []
for roi in ROIS:
    d = read_grouped_sums(EXPORTS / f"{roi}_v8_relevo_daa.geojson", "classe")
    d["slope"], d["hand"] = d.classe // 5, d.classe % 5
    tot = d[["n_daa", "tp", "fn"]].sum()
    for name, (s_min, h_min) in SCREENS.items():
        steep = (d.slope >= s_min) & (d.hand >= h_min)
        a, b = d[steep][["n_daa", "tp", "fn"]].sum(), d[~steep][["n_daa", "tp", "fn"]].sum()
        rows.append(dict(domain=roi, screen=name, share_of_daa=a.n_daa / tot.n_daa,
                         share_of_omissions=a.fn / tot.fn, recall_inside=a.tp / max(a.n_daa, 1),
                         recall_all=tot.tp / tot.n_daa, recall_excluding=b.tp / b.n_daa))
    steep = (d.slope >= 2) & (d.hand >= 2)
    for mun, g in d.groupby("municipality"):
        flat = g[~steep.loc[g.index]]
        mun_rows.append(dict(domain=roi, municipality=mun,
                             daa_share_steep=1 - flat.n_daa.sum() / g.n_daa.sum(),
                             recall_all=g.tp.sum() / g.n_daa.sum(),
                             recall_excluding_steep=flat.tp.sum() / flat.n_daa.sum()))
t = pd.DataFrame(rows)
t.to_csv(RESULTS / "tableS9_terrain_screen.csv", index=False, lineterminator="\n")
m = pd.DataFrame(mun_rows).sort_values("daa_share_steep", ascending=False)
m.to_csv(RESULTS / "terrain_screen_municipalities.csv", index=False, lineterminator="\n")
print(t.round(4).to_string(index=False))
print("\nScreen slope >= 10 deg and HAND >= 10 m, by municipality\n", m.round(3).head(8).to_string(index=False))
