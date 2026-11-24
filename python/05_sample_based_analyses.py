"""Sample-based analyses on random points - mask check (Table S3, Fig. S1),
classifiers and masked indices on the same points (Table 7), and collinearity
of the FLOOD-HI inputs.

Input : data/exports/ROI{1,2}_v3_E_amostra_pareada.csv (script 02, export E)
Output: results/tableS3_mask_check.csv, results/table7_classifiers.csv,
        results/collinearity.csv
"""
import warnings

import numpy as np
import pandas as pd
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import f1_score, jaccard_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from common import EXPORTS, RESULTS

warnings.filterwarnings("ignore")
BANDS = ["B2", "B3", "B4", "B6", "B7", "B8", "B11", "B12"]
INPUTS = ["NDWI", "IMP", "AWEI", "TCW", "NDVI", "SAVI"]          # FLOOD-HI inputs
WEIGHTS = np.array([3.72, -2.67, 2.69, -1.77, -2.67, 3.30])      # Eq. (1)
V = "mediana_qa60"


def features(d, comp=V):
    """Bands of a composite and the indices of Table 3, from a sample table."""
    b = {k: d[f"{comp}_{k}"] for k in BANDS}
    nd = lambda x, y: (x - y) / (x + y)
    x = pd.DataFrame(b)
    x["NDWI"] = nd(b["B3"], b["B8"])
    x["MNDWI"] = nd(b["B3"], b["B11"])
    x["IMP"] = x.NDWI + nd(b["B2"], b["B8"])
    x["AWEI"] = b["B2"] + 2.5 * b["B3"] - 1.5 * (b["B8"] + b["B11"]) - 0.25 * b["B12"]
    x["TCW"] = (0.0315 * b["B2"] + 0.2021 * b["B3"] + 0.3102 * b["B4"] + 0.1594 * b["B8"]
                - 0.6806 * b["B11"] - 0.6109 * b["B12"])
    x["NDVI"] = nd(b["B8"], b["B4"])
    x["SAVI"] = 1.5 * (b["B8"] - b["B4"]) / (b["B8"] + b["B4"] + 0.5)
    x["FHI"] = x[INPUTS].values @ WEIGHTS
    x["MASK"] = (b["B11"] < 0.12) & (b["B6"] < 0.20) & (b["B7"] < 0.20) & (b["B8"] < 0.20)
    return x


s1 = pd.read_csv(EXPORTS / "ROI1_v3_E_amostra_pareada.csv")
s2 = pd.read_csv(EXPORTS / "ROI2_v3_E_amostra_pareada.csv")

# ---- Table S3 and Fig. S1: post hoc check of the masks (points valid in the QA60 composite)
rows = []
for roi, d in (("ROI-1", s1), ("ROI-2", s2)):
    d = d[d[f"valido_{V}"] == 1]
    x, y = features(d), d.REF.values
    masks = {"B11 < 0.12": x.B11 < 0.12, "B8 < 0.20": x.B8 < 0.20,
             "B6, B7 < 0.20": (x.B6 < 0.20) & (x.B7 < 0.20),
             "B11 < 0.12 and B8 < 0.20": (x.B11 < 0.12) & (x.B8 < 0.20),
             "Full mask (B11, B6, B7, B8)": x.MASK}
    for name, m in masks.items():
        rows.append(dict(domain=roi, n_points=len(y), mask=name, f1_mask_only=f1_score(y, m),
                         f1_floodhi_and_mask=f1_score(y, (x.FHI > 0) & m)))
    changed = (masks["Full mask (B11, B6, B7, B8)"] != masks["B11 < 0.12 and B8 < 0.20"]).mean()
    print(f"{roi}: n = {len(y)}; B6/B7 change the mask for {changed:.1%} of the points; "
          f"r(B8,B6) = {np.corrcoef(x.B8, x.B6)[0, 1]:.2f}, r(B8,B7) = {np.corrcoef(x.B8, x.B7)[0, 1]:.2f}")
    dry = d.REF == 0
    print(f"   dry points failing at least one condition: "
          + ", ".join(f"{lab} {(~x.MASK[dry & d.uso.isin(k)]).mean():.0%}" for k, lab in
                      (([4], "vegetation"), ([3, 6], "farming and rice"), ([1], "urban"))))
tS3 = pd.DataFrame(rows)
tS3.to_csv(RESULTS / "tableS3_mask_check.csv", index=False, lineterminator="\n")
print(tS3.round(3).to_string(index=False))

# grid search for the two-band rule in ROI-1, transferred to ROI-2
d1, d2 = s1[s1[f"valido_{V}"] == 1], s2[s2[f"valido_{V}"] == 1]
x1, y1, x2, y2 = features(d1), d1.REF.values, features(d2), d2.REF.values
grid = pd.DataFrame([(t11, t8, f1_score(y1, (x1.B11 < t11) & (x1.B8 < t8)))
                     for t11 in np.arange(0.04, 0.31, 0.02) for t8 in np.arange(0.08, 0.41, 0.02)],
                    columns=["b11", "b8", "f1"])
best = grid.loc[grid.f1.idxmax()]
near = grid[grid.f1 >= best.f1 - 0.02]
print(f"\nTwo-band grid optimum in ROI-1: B11 < {best.b11:.2f}, B8 < {best.b8:.2f}, F1 = {best.f1:.3f}; "
      f"within 0.02: B11 {near.b11.min():.2f}-{near.b11.max():.2f}, B8 {near.b8.min():.2f}-{near.b8.max():.2f}; "
      f"transferred F1 in ROI-2 = {f1_score(y2, (x2.B11 < best.b11) & (x2.B8 < best.b8)):.3f}")

# ---- Table 7: detectors and classifiers on the same points (valid in all four composites)
c1, c2 = s1[s1.comum == 1], s2[s2.comum == 1]
X1, X2, y1, y2 = features(c1), features(c2), c1.REF.values, c2.REF.values
print(f"\nTable 7 points: ROI-1 {len(y1)} ({y1.sum()} flooded), ROI-2 {len(y2)} ({y2.sum()} flooded)")


def f1_threshold(score, y, candidates=None):
    """F1-maximising threshold on the training points (300 quantiles)."""
    cand = candidates if candidates is not None else score
    ts = np.unique(np.quantile(cand, np.linspace(0.01, 0.99, 300)))
    return ts[int(np.argmax([f1_score(y, score > t) for t in ts]))]


rows, preds = [], {}
LOW = -1e6
for col, name in (("FHI", "FLOOD-HI + masks"), ("NDWI", "NDWI + masks"), ("MNDWI", "MNDWI + masks"),
                  ("AWEI", "AWEIsh + masks"), ("TCW", "TCW + masks")):
    sc1, sc2 = np.where(X1.MASK, X1[col], LOW), np.where(X2.MASK, X2[col], LOW)
    t = f1_threshold(sc1, y1, X1[col][X1.MASK])
    preds[name] = sc2 > t
    rows.append(dict(model=name, group="indices and masks", f1_roi2=f1_score(y2, preds[name]),
                     iou_roi2=jaccard_score(y2, preds[name])))
preds["Masks only"] = X2.MASK.values
rows.append(dict(model="Masks only", group="indices and masks", f1_roi2=f1_score(y2, X2.MASK),
                 iou_roi2=jaccard_score(y2, X2.MASK)))


def evaluate(name, sc1, sc2, group):
    t = f1_threshold(sc1, y1)
    preds[name] = sc2 > t
    rows.append(dict(model=name, group=group, auc_roi1_training=roc_auc_score(y1, sc1),
                     auc_roi2=roc_auc_score(y2, sc2), f1_roi2=f1_score(y2, preds[name]),
                     iou_roi2=jaccard_score(y2, preds[name])))


evaluate("FLOOD-HI, Eq. (1), without masks", X1.FHI.values, X2.FHI.values, "indices and masks")
MODELS = [  # settings fixed in advance; scikit-learn defaults otherwise
    ("OLS with intercept / LDA, six inputs", LinearRegression(), INPUTS),
    ("Logistic regression, six inputs", make_pipeline(StandardScaler(), LogisticRegression(max_iter=3000)), INPUTS),
    ("Logistic regression, eight bands", make_pipeline(StandardScaler(), LogisticRegression(max_iter=3000)), BANDS),
    ("Random forest, eight bands", RandomForestClassifier(500, min_samples_leaf=5, random_state=0, n_jobs=-1), BANDS),
]
for name, model, cols in MODELS:
    model.fit(X1[cols], y1)
    score = (lambda X: model.predict_proba(X[cols])[:, 1]) if hasattr(model, "predict_proba") \
        else (lambda X: model.predict(X[cols]))
    evaluate(name, score(X1), score(X2), "classifiers")
lda = LinearDiscriminantAnalysis().fit(X1[INPUTS], y1)
print("LDA AUC ROI-2 (same ranking as OLS with intercept): "
      f"{roc_auc_score(y2, lda.predict_proba(X2[INPUTS])[:, 1]):.3f}")
t7 = pd.DataFrame(rows)
t7.to_csv(RESULTS / "table7_classifiers.csv", index=False, lineterminator="\n")
print(t7.round(3).to_string(index=False))

# paired bootstrap over test points: band-based classifiers minus FLOOD-HI + masks
rng = np.random.default_rng(3)
idx = rng.integers(0, len(y2), (2000, len(y2)))
ref = preds["FLOOD-HI + masks"]
for name in ("Logistic regression, eight bands", "Random forest, eight bands"):
    p = preds[name]
    diff = [f1_score(y2[i], p[i]) - f1_score(y2[i], ref[i]) for i in idx]
    print(f"{name} - FLOOD-HI + masks: {f1_score(y2, p) - f1_score(y2, ref):.3f} "
          f"[{np.percentile(diff, 2.5):.3f}, {np.percentile(diff, 97.5):.3f}]")

# ---- Collinearity of the FLOOD-HI inputs and refit without intercept (ROI-1 training points)
X, y = X1[INPUTS].values, y1
Z = (X - X.mean(0)) / X.std(0)
vif = [1 / (1 - LinearRegression().fit(np.delete(Z, j, 1), Z[:, j]).score(np.delete(Z, j, 1), Z[:, j]))
       for j in range(len(INPUTS))]
refit, *_ = np.linalg.lstsq(X, y, rcond=None)
col = pd.DataFrame(dict(input=INPUTS, vif=vif, weight_eq1=WEIGHTS, weight_refit_no_intercept=refit))
col.round(6).to_csv(RESULTS / "collinearity.csv", index=False, lineterminator="\n")  # least-squares refit: last digits vary between runs
print("\n", col.round(2).to_string(index=False), f"\ncondition number (standardised) = {np.linalg.cond(Z):.0f}")
