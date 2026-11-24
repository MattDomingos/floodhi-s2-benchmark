"""Check that the DAA polygons in data/spatial match the reference used in the paper.

Usage (from the repository folder):
    python tools/check_spatial_inputs.py

For each municipality, compares the area of the polygon parts of the DAA layer
(data/spatial/ROI*_DAA.geojson, ellipsoidal area on WGS 84) with the DAA area
painted at 10 m by the Earth Engine scripts (n_ref in the confusion-count export
of script 01). Differences of a few tenths of a percent come from rasterisation.
Line and point fragments of the DAA features have no area and are ignored, as
they are by ee.Image.paint.
"""
import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
A, F = 6378137.0, 1 / 298.257223563                  # WGS 84
E2 = F * (2 - F)
E = math.sqrt(E2)


def q(phi):
    s = math.sin(phi)
    return (1 - E2) * (s / (1 - E2 * s * s) - math.log((1 - E * s) / (1 + E * s)) / (2 * E))


QP = q(math.pi / 2)
RQ = A * math.sqrt(QP / 2)                            # authalic radius


def ring_area(ring):
    """Area (m2) of a lon/lat ring, exact for an equal-area (authalic) projection."""
    pts = [(math.radians(x), q(math.radians(y)) / QP) for x, y in ring]
    return abs(0.5 * sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]))) * RQ * RQ


def polygons(g):
    if not g:
        return []
    if g["type"] == "Polygon":
        return [g["coordinates"]]
    if g["type"] == "MultiPolygon":
        return g["coordinates"]
    if g["type"] == "GeometryCollection":
        return [p for x in g["geometries"] for p in polygons(x)]
    return []


for roi in ("ROI1", "ROI2"):
    with open(ROOT / "data" / "exports" / f"{roi}_C_matrizes_confusao.csv", newline="", encoding="utf-8") as fh:
        painted = {row["NM_MUN"]: float(row["n_ref"]) * 1e-4 for row in csv.DictReader(fh)}   # km2
    feats = json.loads((ROOT / "data" / "spatial" / f"{roi}_DAA.geojson").read_text(encoding="utf-8"))["features"]
    print(f"\n{roi}: DAA area by municipality (km2)")
    print(f"{'municipality':26s} {'polygons':>9s} {'painted':>9s} {'diff':>7s}")
    tot_p = tot_r = 0.0
    for ft in feats:
        name = ft["properties"]["NM_MUN"]
        area = sum(ring_area(p[0]) - sum(ring_area(h) for h in p[1:]) for p in polygons(ft["geometry"])) / 1e6
        ref = painted[name]
        tot_p, tot_r = tot_p + area, tot_r + ref
        print(f"{name:26s} {area:9.2f} {ref:9.2f} {100 * (area - ref) / ref:+6.2f}%")
    print(f"{'total':26s} {tot_p:9.1f} {tot_r:9.1f} {100 * (tot_p - tot_r) / tot_r:+6.2f}%")
