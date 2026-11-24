"""Write the shapefiles of data/spatial/ from the GeoJSON exports of the Earth Engine assets.

The DAA assets store most features as geometry collections (polygons plus a few
zero-area lines and points left by clipping). Earth Engine cannot export such
features to a shapefile, so the shapefiles are written here from the complete
GeoJSON copies exported by gee/00_export_spatial_inputs.js:

* every feature is kept, in the same order and with the same attributes;
* only the polygon parts of each geometry are written (lines and points have
  no area, so they do not change the painted reference of scripts 01-06);
* rings follow the shapefile convention (outer rings clockwise, holes
  counter-clockwise); coordinates are WGS 84 longitude/latitude.

The script also prints, for each layer, the feature count, the geometry types
and the polygon area, as a check against Table 1.

Input : data/spatial/{ROI1,ROI2}_{municipalities,DAA}.geojson
Output: data/spatial/{ROI1,ROI2}_{municipalities,DAA}.shp, .shx, .dbf, .prj, .cpg
Usage : python tools/spatial_shapefiles.py   (from the repository folder; standard library only)
"""
import json
import math
import struct
from pathlib import Path

SPATIAL = Path(__file__).resolve().parents[1] / "data" / "spatial"
LAYERS = ["ROI1_municipalities", "ROI1_DAA", "ROI2_municipalities", "ROI2_DAA"]
PRJ = ('GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],'
       'PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]')
DBF_DATE = (126, 11, 23)                     # fixed date (2026-11-23) so the output is reproducible
EARTH_R = 6371007.2                          # authalic radius (m), for the area check


# ---------------------------------------------------------------- geometry
def polygons_of(geom):
    """List of polygons (each a list of rings) in a GeoJSON geometry; lines and points are skipped."""
    if geom is None:
        return []
    kind = geom["type"]
    if kind == "Polygon":
        return [geom["coordinates"]]
    if kind == "MultiPolygon":
        return list(geom["coordinates"])
    if kind == "GeometryCollection":
        return [p for g in geom["geometries"] for p in polygons_of(g)]
    return []


def geometry_types(geom):
    if geom["type"] == "GeometryCollection":
        return "GeometryCollection(" + ",".join(sorted({g["type"] for g in geom["geometries"]})) + ")"
    return geom["type"]


def signed_area(ring):
    """Shoelace area in degrees^2: positive for counter-clockwise rings."""
    return 0.5 * sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(ring, ring[1:]))


def spherical_area_km2(ring):
    a = sum(math.radians(x2 - x1) * (2 + math.sin(math.radians(y1)) + math.sin(math.radians(y2)))
            for (x1, y1), (x2, y2) in zip(ring, ring[1:]))
    return abs(a) * EARTH_R ** 2 / 2 / 1e6


def shapefile_rings(polygons):
    rings, area = [], 0.0
    for poly in polygons:
        for k, ring in enumerate(poly):
            ring = [(float(c[0]), float(c[1])) for c in ring]
            if ring[0] != ring[-1]:
                ring.append(ring[0])
            if len(ring) < 4:
                continue
            outer = k == 0
            clockwise = signed_area(ring) < 0
            if clockwise != outer:                 # outer: clockwise; hole: counter-clockwise
                ring = ring[::-1]
            rings.append(ring)
            area += spherical_area_km2(ring) * (1 if outer else -1)
    return rings, area


# ---------------------------------------------------------------- shapefile
def polygon_record(rings):
    pts = [p for r in rings for p in r]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    bbox = (min(xs), min(ys), max(xs), max(ys)) if pts else (0.0, 0.0, 0.0, 0.0)
    parts, n = [], 0
    for r in rings:
        parts.append(n)
        n += len(r)
    if not rings:                                  # null shape
        return struct.pack("<i", 0), None
    body = struct.pack("<i4d2i", 5, *bbox, len(rings), len(pts))
    body += struct.pack(f"<{len(parts)}i", *parts)
    body += b"".join(struct.pack("<2d", x, y) for x, y in pts)
    return body, bbox


def header(file_len_bytes, bbox):
    return (struct.pack(">7i", 9994, 0, 0, 0, 0, 0, file_len_bytes // 2)
            + struct.pack("<2i", 1000, 5) + struct.pack("<4d", *bbox) + struct.pack("<4d", 0, 0, 0, 0))


def write_shp_shx(stem, records):
    shp, shx, offset = [], [], 100
    boxes = [b for _, b in records if b]
    bbox = (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))
    for i, (body, _) in enumerate(records, start=1):
        shp.append(struct.pack(">2i", i, len(body) // 2) + body)
        shx.append(struct.pack(">2i", offset // 2, len(body) // 2))
        offset += 8 + len(body)
    shp_bytes = b"".join(shp)
    stem.with_suffix(".shp").write_bytes(header(100 + len(shp_bytes), bbox) + shp_bytes)
    stem.with_suffix(".shx").write_bytes(header(100 + 8 * len(records), bbox) + b"".join(shx))


# ---------------------------------------------------------------- dBase
def write_dbf(stem, props):
    names = list(props[0].keys())
    fields = []
    for name in names:
        values = [p.get(name) for p in props]
        if all(isinstance(v, (int, float)) or v is None for v in values):
            text = [("" if v is None else repr(float(v))) for v in values]
            decimals = max((len(t.split(".")[1]) for t in text if "." in t), default=0)
            decimals = min(decimals, 15)
            text = [("" if v is None else f"{float(v):.{decimals}f}") for v in values]
            width = max(max(len(t) for t in text), 1)
            fields.append((name, "N", min(width, 20), decimals, text))
        else:
            enc = [("" if v is None else str(v)).encode("utf-8") for v in values]
            width = max(max(len(e) for e in enc), 1)
            fields.append((name, "C", min(width, 254), 0, enc))
    record_len = 1 + sum(f[2] for f in fields)
    head_len = 32 + 32 * len(fields) + 1
    out = bytearray(struct.pack("<B3BIHH20x", 3, *DBF_DATE, len(props), head_len, record_len))
    for name, ftype, width, dec, _ in fields:
        out += struct.pack("<11sc4xBB14x", name.encode("ascii")[:10], ftype.encode(), width, dec)
    out += b"\r"
    for i in range(len(props)):
        out += b" "
        for name, ftype, width, dec, vals in fields:
            v = vals[i]
            if ftype == "C":
                out += v[:width].ljust(width, b" ")
            else:
                out += v.encode("ascii").rjust(width, b" ")
    out += b"\x1a"
    stem.with_suffix(".dbf").write_bytes(bytes(out))
    stem.with_suffix(".cpg").write_text("UTF-8", encoding="ascii")


# ---------------------------------------------------------------- main
for layer in LAYERS:
    src = SPATIAL / f"{layer}.geojson"
    data = json.loads(src.read_text(encoding="utf-8"))
    feats = data["features"]
    types, records, area = {}, [], 0.0
    for f in feats:
        t = geometry_types(f["geometry"])
        types[t] = types.get(t, 0) + 1
        rings, a = shapefile_rings(polygons_of(f["geometry"]))
        records.append(polygon_record(rings))
        area += a
    stem = SPATIAL / layer
    write_shp_shx(stem, records)
    write_dbf(stem, [f["properties"] for f in feats])
    stem.with_suffix(".prj").write_text(PRJ, encoding="ascii")
    print(f"{layer}: {len(feats)} features, polygon area {area:,.1f} km2 (sphere); geometry types {types}")
