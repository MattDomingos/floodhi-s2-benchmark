"""Readers for the tabular Earth Engine exports.

Field names in the exports are kept as in the original runs (Portuguese
abbreviations), so that archived exports and new runs are interchangeable.
See ``data/README.md`` for a data dictionary.
"""
import ast
import json

import pandas as pd

# Detector configurations in the confusion-count export of script 01
# (threshold fixed at zero). "_M" = combined with the reflectance masks.
CONFIGS = {
    "FHI_M": "FLOOD-HI + masks", "FHI": "FLOOD-HI", "MASC": "Masks only",
    "MNDWI": "MNDWI", "MNDWI_M": "MNDWI + masks", "TCW": "TCW", "TCW_M": "TCW + masks",
    "AWEI": "AWEIsh", "AWEI_M": "AWEIsh + masks", "NDWI": "NDWI", "NDWI_M": "NDWI + masks",
}


def read_confusion_csv(path):
    """Per-municipality confusion counts at the zero threshold (script 01, export C)."""
    return pd.read_csv(path)


def read_grouped_sums(path, group_field):
    """Read a grouped-sum export (scripts 02, 04 and 06) into a long table.

    Each feature is a municipality; ``groups`` holds one list of band sums per
    group (land-cover/observation stratum, boundary-distance class or terrain
    class), with band names listed in the ``bandas`` property."""
    data = json.load(open(path, encoding="utf-8"))
    rows = []
    for feat in data["features"]:
        p = feat["properties"]
        names = p["bandas"].split(",")
        groups = p["groups"]
        groups = ast.literal_eval(groups) if isinstance(groups, str) else groups
        for g in groups:
            row = dict(zip(names, g["sum"]))
            row[group_field] = int(g[group_field])
            row["municipality"] = p["NM_MUN"]
            rows.append(row)
    return pd.DataFrame(rows)


def read_sample(path):
    """Random-point sample with reference label, land cover and band values."""
    return pd.read_csv(path)
