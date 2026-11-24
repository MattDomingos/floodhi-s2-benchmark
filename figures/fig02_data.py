"""Fig. 2, step 1 - real-data inputs for the small graphics inside the workflow figure.

Reads the Earth Engine exports and writes figures/output/fig02_data.npz, which
fig02_workflow.py then draws. Run this script first.

Input : data/exports/ROI{1,2}_B_histogramas.geojson, ROI{1,2}_v4_*_30m.tif,
        ROI{1,2}_janela_{A,B,C}.png
Output: figures/output/fig02_data.npz
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
from common import EXPORTS  # noqa: E402
from floodhi_eval import read_histograms  # noqa: E402

UP = str(EXPORTS) + "/"
OUT = ROOT / "figures" / "output"
OUT.mkdir(exist_ok=True)
out = {}
H = {r: read_histograms(UP + f'{r}_B_histogramas.geojson') for r in ('ROI1', 'ROI2')}
V = 'mediana_qa60'
# class-conditional FLOOD-HI histogram, ROI-1
h1 = H['ROI1'][(V, 'FLOODHI')]
pos, neg = h1.class_histograms()
out['hist_edges'] = h1.edges; out['hist_pos'] = pos; out['hist_neg'] = neg
# F1 sweeps for FLOOD-HI + masks
for r in ('ROI1', 'ROI2'):
    h = H[r][(V, 'FLOODHI')]
    out[f'sweep_{r}'] = h.sweep(masked=True)
t1, f1 = H['ROI1'][(V, 'FLOODHI')].best_threshold(masked=True)
out['t_star'] = t1
print('FLOOD-HI + masks ROI-1 optimum', t1, f1)
tM, fM = H['ROI1'][(V, 'MNDWI')].best_threshold(masked=True)
print('MNDWI + masks ROI-1 optimum', tM, fM)
# ROC curves ROI-2
for idx in ('FLOODHI', 'NDWI', 'MNDWI', 'AWEI', 'TCW'):
    h = H['ROI2'][(V, idx)]
    p, n = h.class_histograms()
    tpr = np.r_[np.cumsum(p[::-1])[::-1] / p.sum(), 0]
    fpr = np.r_[np.cumsum(n[::-1])[::-1] / n.sum(), 0]
    out[f'roc_{idx}'] = np.vstack([fpr, tpr]); print(idx, 'AUC', round(h.auc(), 3))
# municipality bootstrap of paired dF1, FLOOD-HI + masks minus MNDWI + masks, transferred thresholds
bm = H['ROI2'].by_municipality
muns = sorted({k[2] for k in bm if k[0] == V and k[1] == 'FLOODHI'})
A = np.array([bm[(V, 'FLOODHI', m)].confusion(t1, True) for m in muns])
B = np.array([bm[(V, 'MNDWI', m)].confusion(tM, True) for m in muns])
f = lambda c: 2 * c[..., 0] / (2 * c[..., 0] + c[..., 1] + c[..., 2])
idx = np.random.default_rng(1).integers(0, len(muns), (2000, len(muns)))
d = f(A[idx].sum(1)) - f(B[idx].sum(1))
out['boot'] = d
print(len(muns), 'municipalities; dF1 =', round(f(A.sum(0)) - f(B.sum(0)), 4), 'CI', np.percentile(d, [2.5, 97.5]).round(4))

# thumbnails: land cover (0 out, 1 urban, 2 water, 3 farming, 4 natural veg, 5 other, 6 rice)
# error map (0 out, 1 TN, 2 FN, 3 FP, 4 TP)
for r in ('ROI1', 'ROI2'):
    out[f'lc_{r}'] = np.array(Image.open(UP + f'{r}_v4_uso_solo_30m.tif'))
    out[f'err_{r}'] = np.array(Image.open(UP + f'{r}_v4_mapa_erros_30m.tif'))
# true-colour crops from the example windows (top third of each PNG)
tc = []
for r in ('ROI1', 'ROI2'):
    for w in 'ABC':
        im = np.array(Image.open(UP + f'{r}_janela_{w}.png').convert('RGB'))[:600]
        tc.append(im)
out['truecolour'] = np.stack(tc)
np.savez_compressed(OUT / 'fig02_data.npz', **out)
print('written', OUT / 'fig02_data.npz')
