"""Class-conditional histograms exported from Earth Engine.

Each histogram holds the number of valid pixels per index bin, split by
reference class (DAA = 0/1), mask status (rejected/passed) and, for the
composite comparison, membership of the area valid in all four composites.
Because confusion counts are exact at bin edges, thresholds are always
searched on the bin edges, and a pixel is labelled water when its index value
is at or above the threshold.
"""
import ast
import json
from dataclasses import dataclass, field

import numpy as np

from .metrics import scores

_EPS = 1e-12


@dataclass
class Histogram:
    """Histogram of one index.

    ``counts`` has shape (2, 2, 2, n_bins) indexed as
    [reference class, mask passed, valid in all composites, bin].
    """
    edges: np.ndarray
    counts: np.ndarray
    has_common: bool = False

    def _area(self, area):
        if area == "all":
            return self.counts.sum(axis=2)
        if area == "common":
            if not self.has_common:
                raise ValueError("This export has no common-area information.")
            return self.counts[:, :, 1, :]
        raise ValueError("area must be 'all' or 'common'")

    def confusion(self, threshold, masked, area="all"):
        """Confusion counts (TP, FP, FN, TN) for ``index >= threshold``.

        With ``masked=True`` a pixel must also pass the reflectance masks;
        mask-rejected pixels remain negative predictions."""
        c = self._area(area)
        above = self.edges >= threshold - _EPS
        pos, neg = c[1], c[0]
        if masked:
            tp, fp = pos[1][above].sum(), neg[1][above].sum()
        else:
            tp, fp = pos[:, above].sum(), neg[:, above].sum()
        p, n = pos.sum(), neg.sum()
        return np.array([tp, fp, p - tp, n - fp])

    def masks_only(self, area="all"):
        """Confusion counts of the reflectance masks used as a detector."""
        c = self._area(area)
        tp, fp = c[1, 1].sum(), c[0, 1].sum()
        return np.array([tp, fp, c[1].sum() - tp, c[0].sum() - fp])

    def sweep(self, masked, area="all", metric="f1"):
        """Metric at every bin edge."""
        return np.array([scores(*self.confusion(t, masked, area))[metric] for t in self.edges])

    def best_threshold(self, masked, area="all"):
        """F1-maximising bin edge; ties are resolved to the lowest edge."""
        s = self.sweep(masked, area)
        k = int(np.nanargmax(s))
        return self.edges[k], s[k]

    def class_histograms(self, area="all"):
        c = self._area(area)
        return c[1].sum(axis=0), c[0].sum(axis=0)

    def auc(self, area="all"):
        """Area under the ROC curve built from the bin edges."""
        pos, neg = self.class_histograms(area)
        tpr = np.r_[np.cumsum(pos[::-1])[::-1] / pos.sum(), 0]
        fpr = np.r_[np.cumsum(neg[::-1])[::-1] / neg.sum(), 0]
        return -np.trapezoid(tpr, fpr)

    def m_statistic(self, area="all"):
        """Kaufman and Remer (1994) separability, from bin centres."""
        pos, neg = self.class_histograms(area)
        mid = self.edges + (self.edges[1] - self.edges[0]) / 2
        mu = lambda w: (w * mid).sum() / w.sum()
        sd = lambda w: np.sqrt((w * (mid - mu(w)) ** 2).sum() / w.sum())
        return abs(mu(pos) - mu(neg)) / (sd(pos) + sd(neg))

    def otsu(self, area="all"):
        """Otsu (1979) threshold from all valid index values, without labels
        and including mask-rejected pixels."""
        c = self._area(area).sum(axis=(0, 1))
        mid = self.edges + (self.edges[1] - self.edges[0]) / 2
        w0 = np.cumsum(c)
        w1 = c.sum() - w0
        m0 = np.cumsum(c * mid) / np.maximum(w0, 1e-9)
        m1 = (np.sum(c * mid) - np.cumsum(c * mid)) / np.maximum(w1, 1e-9)
        between = w0 * w1 * (m0 - m1) ** 2
        return self.edges[int(np.argmax(between[:-1])) + 1]

    def coarsen(self, factor):
        """Merge consecutive bins; the remainder is added to the last bin."""
        nb = len(self.edges) // factor * factor
        counts = self.counts[..., :nb].reshape(*self.counts.shape[:3], -1, factor).sum(-1)
        if len(self.edges) > nb:
            counts[..., -1] += self.counts[..., nb:].sum(-1)
        return Histogram(self.edges[:nb:factor], counts, self.has_common)


@dataclass
class HistogramSet:
    """All histograms of one export, pooled and per municipality."""
    pooled: dict = field(default_factory=dict)          # (variant, index) -> Histogram
    by_municipality: dict = field(default_factory=dict)  # (variant, index, municipality) -> Histogram

    def __getitem__(self, key):
        return self.pooled[key]

    def municipalities(self):
        return sorted({k[2] for k in self.by_municipality})


def _decode(group, has_common):
    """Group codes: ref*4 + mask*2 + common (composite export) or ref*2 + mask."""
    if has_common:
        return group // 4, (group // 2) % 2, group % 2
    return group // 2, group % 2, 0


def read_histograms(path, default_variant="mediana_qa60"):
    """Read a histogram export (scripts 01, 02 and 05) into a HistogramSet."""
    data = json.load(open(path, encoding="utf-8"))
    pooled, by_mun = {}, {}
    for feat in data["features"]:
        p = feat["properties"]
        groups = p["groups"]
        groups = ast.literal_eval(groups) if isinstance(groups, str) else groups
        has_common = "variante" in p
        variant = p.get("variante", default_variant)
        key = (variant, p["indice"])
        for g in groups:
            h = np.asarray(g["histogram"], float)
            r, m, c = _decode(int(g["grupo"]), has_common)
            for store, k in ((pooled, key), (by_mun, key + (p["NM_MUN"],))):
                if k not in store:
                    store[k] = Histogram(h[:, 0], np.zeros((2, 2, 2, len(h))), has_common)
                store[k].counts[r, m, c] += h[:, 1]
    return HistogramSet(pooled, by_mun)
