"""Table 5 and Table S4 - agreement with every threshold fixed at zero.

Input : data/exports/ROI{1,2}_C_matrizes_confusao.csv (script 01, export C)
Output: results/table5_zero_threshold.csv, results/tableS4_confusion_counts.csv
"""
import pandas as pd

from common import EXPORTS, RESULTS, ROIS
from floodhi_eval import CONFIGS, read_confusion_csv, scores

rows = []
for roi in ROIS:
    totals = read_confusion_csv(EXPORTS / f"{roi}_C_matrizes_confusao.csv").sum(numeric_only=True)
    n_check, p_check = set(), set()
    for code, name in CONFIGS.items():
        tp, fp, fn, tn = (totals[f"{code}_{k}"] for k in ("TP", "FP", "FN", "TN"))
        n_check.add(round(tp + fp + fn + tn, 3))
        p_check.add(round(tp + fn, 3))
        rows.append(dict(domain=roi, method=name, TP=tp, FP=fp, FN=fn, TN=tn, **scores(tp, fp, fn, tn)))
    # Every method must be scored on the same pixels (same N and same DAA positives).
    print(f"{roi}: distinct N = {len(n_check)}, distinct TP+FN = {len(p_check)} (both must be 1)")

table = pd.DataFrame(rows)
table.to_csv(RESULTS / "table5_zero_threshold.csv", index=False, lineterminator="\n")
table[["domain", "method", "TP", "FP", "FN", "TN", "n"]].round(0).to_csv(
    RESULTS / "tableS4_confusion_counts.csv", index=False, lineterminator="\n")
cols = ["domain", "method", "precision", "recall", "f1", "iou", "kappa", "qd", "ad"]
print(table[cols].round(3).to_string(index=False))
