"""Fig. 7, Fig. 8 and Table S2 - agreement by land-cover stratum, by number
of cloud-free observations and by municipality (zero threshold).

Input : data/exports/ROI{1,2}_v3_S_estratos.geojson (script 02, export S)
Output: results/fig7_recall_by_land_cover.csv, results/fig7_shares.csv,
        results/recall_by_observations.csv, results/tableS2_municipalities.csv
"""
import pandas as pd
from scipy.stats import pearsonr

from common import EXPORTS, LAND_COVER, RESULTS, ROIS
from floodhi_eval import read_grouped_sums

DETECTORS = {"FHI_M": "FLOOD-HI + masks", "MASC": "Masks only",
             "MNDWI_M": "MNDWI + masks", "TCW": "TCW"}


def counts(df, comp, det):
    return {k: df[f"{comp}__{det}_{k}"] for k in ("TP", "FP", "FN", "TN")}


recall_rows, share_rows, obs_rows, mun_rows = [], [], [], []
for roi in ROIS:
    s = read_grouped_sums(EXPORTS / f"{roi}_v3_S_estratos.geojson", "estrato")
    s["land_cover"] = s.estrato // 10
    s["n_obs"] = s.estrato % 10            # 0, 1, 2, 3 = three or more
    by_lc = s.groupby("land_cover").sum(numeric_only=True)
    for comp in ("mediana_qa60", "dia06_cs"):
        for det, name in DETECTORS.items():
            c = counts(by_lc, comp, det)
            for lc in by_lc.index:
                recall_rows.append(dict(domain=roi, composite=comp, detector=name,
                                        land_cover=LAND_COVER[lc],
                                        recall=c["TP"][lc] / (c["TP"][lc] + c["FN"][lc]),
                                        precision=c["TP"][lc] / (c["TP"][lc] + c["FP"][lc])))
    fn = by_lc["mediana_qa60__FHI_M_FN"]
    for lc in by_lc.index:
        share_rows.append(dict(domain=roi, land_cover=LAND_COVER[lc],
                               share_of_area=by_lc.n_total[lc] / by_lc.n_total.sum(),
                               share_of_daa=by_lc.n_ref[lc] / by_lc.n_ref.sum(),
                               share_of_omissions=fn[lc] / fn.sum()))
    by_obs = s.groupby("n_obs").sum(numeric_only=True)
    c = counts(by_obs, "mediana_qa60", "FHI_M")
    for k in by_obs.index:
        if c["TP"][k] + c["FN"][k] == 0:
            continue                       # no valid pixels without observations
        obs_rows.append(dict(domain=roi, cloud_free_observations=["0", "1", "2", ">=3"][k],
                             recall=c["TP"][k] / (c["TP"][k] + c["FN"][k])))
    # Expected recall (Eq. 2): municipal DAA shares by stratum x domain-wide stratum recall
    tp, fnv = by_lc["mediana_qa60__FHI_M_TP"], by_lc["mediana_qa60__FHI_M_FN"]
    r_c = tp / (tp + fnv)
    for mun, g in s.groupby("municipality"):
        gl = g.groupby("land_cover").sum(numeric_only=True)
        pos = gl["mediana_qa60__FHI_M_TP"] + gl["mediana_qa60__FHI_M_FN"]
        tot = g.sum(numeric_only=True)
        tpm, fpm, fnm = (tot[f"mediana_qa60__FHI_M_{k}"] for k in ("TP", "FP", "FN"))
        mun_rows.append(dict(domain=roi, municipality=mun, daa_km2=tot.n_ref / 1e4,
                             precision=tpm / (tpm + fpm), recall=tpm / (tpm + fnm),
                             expected_recall=(pos / pos.sum() * r_c.reindex(pos.index)).sum(),
                             f1=2 * tpm / (2 * tpm + fpm + fnm)))

pd.DataFrame(recall_rows).to_csv(RESULTS / "fig7_recall_by_land_cover.csv", index=False, lineterminator="\n")
pd.DataFrame(share_rows).to_csv(RESULTS / "fig7_shares.csv", index=False, lineterminator="\n")
pd.DataFrame(obs_rows).to_csv(RESULTS / "recall_by_observations.csv", index=False, lineterminator="\n")
mun = pd.DataFrame(mun_rows)
mun.to_csv(RESULTS / "tableS2_municipalities.csv", index=False, lineterminator="\n")

rc = pd.DataFrame(recall_rows)
print(rc[rc.composite == "mediana_qa60"].pivot_table(index="land_cover", columns=["detector", "domain"],
                                                     values="recall").round(2).to_string())
print("\n", pd.DataFrame(share_rows).round(3).to_string(index=False))
print("\n", pd.DataFrame(obs_rows).round(3).to_string(index=False))
print("\nTable S2\n", mun.round(2).to_string(index=False))
r, _ = pearsonr(mun.recall, mun.expected_recall)
print(f"\nObserved vs expected recall: r = {r:.2f}, n = {len(mun)} (descriptive association)")
