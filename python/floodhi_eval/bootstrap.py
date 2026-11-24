"""Municipality-level bootstrap and sign tests.

Pixels are spatially autocorrelated, so the municipality is the resampling
unit. Replicates resample municipalities with replacement and pool their
confusion counts; all methods share the same replicates, so paired
differences are computed within each replicate. Intervals assume independence
between municipalities and are therefore approximate.
"""
import numpy as np
import pandas as pd
from scipy.stats import binomtest

from .metrics import f1, scores


def municipality_bootstrap(counts, reference, n_rep=2000, seed=1):
    """``counts`` maps a method name to an array (n_municipalities, 4) of
    TP, FP, FN, TN. Returns F1 with 95% CI, the paired difference
    F1(reference) - F1(method) with 95% CI, municipality wins of the reference
    and the two-sided exact sign-test p-value."""
    names = list(counts)
    n_mun = counts[reference].shape[0]
    idx = np.random.default_rng(seed).integers(0, n_mun, (n_rep, n_mun))
    ref = counts[reference]
    rows = []
    for name in names:
        c = counts[name]
        pooled = scores(*c.sum(0))
        boot = np.array([f1(c[i].sum(0)) for i in idx])
        row = dict(method=name, **pooled,
                   f1_lo=np.percentile(boot, 2.5), f1_hi=np.percentile(boot, 97.5))
        if name != reference:
            diff = np.array([f1(ref[i].sum(0)) - f1(c[i].sum(0)) for i in idx])
            wins = int(sum(f1(ref[k]) > f1(c[k]) for k in range(n_mun)))
            row.update(d_f1=f1(ref.sum(0)) - pooled["f1"],
                       d_lo=np.percentile(diff, 2.5), d_hi=np.percentile(diff, 97.5),
                       wins=wins, sign_p=binomtest(wins, n_mun).pvalue)
        rows.append(row)
    return pd.DataFrame(rows)
