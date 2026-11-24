"""Agreement metrics computed from confusion counts (TP, FP, FN, TN).

Counts are pixel-equivalents and may be fractional, because Earth Engine
weights pixels on region boundaries by the fraction of their area inside.
"""
import numpy as np


def f1(counts):
    """F1 score from a sequence (TP, FP, FN, TN)."""
    tp, fp, fn = counts[0], counts[1], counts[2]
    denom = 2 * tp + fp + fn
    return 2 * tp / denom if denom > 0 else np.nan


def scores(tp, fp, fn, tn):
    """Return precision, recall, F1, IoU, Cohen's kappa and the quantity (QD)
    and allocation (AD) disagreement of Pontius and Millones (2011)."""
    n = tp + fp + fn + tn
    po = (tp + tn) / n
    pe = ((tp + fp) * (tp + fn) + (tn + fn) * (tn + fp)) / n ** 2
    qd = abs(fp - fn) / n
    return {
        "precision": tp / (tp + fp) if tp + fp > 0 else np.nan,
        "recall": tp / (tp + fn) if tp + fn > 0 else np.nan,
        "f1": f1((tp, fp, fn, tn)),
        "iou": tp / (tp + fp + fn) if tp + fp + fn > 0 else np.nan,
        "kappa": (po - pe) / (1 - pe),
        "qd": qd,
        "ad": (fp + fn) / n - qd,
        "n": n,
    }
