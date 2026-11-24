"""Shared paths and names for the analysis scripts."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPORTS = ROOT / "data" / "exports"      # Earth Engine exports (see data/README.md)
RESULTS = ROOT / "results"               # tables written by the scripts
RESULTS.mkdir(exist_ok=True)

ROIS = ("ROI1", "ROI2")                  # ROI-1 calibration, ROI-2 test
INDICES = ("FLOODHI", "NDWI", "MNDWI", "AWEI", "TCW")
COMPOSITES = {                           # composite codes used in the exports
    "mediana_qa60": "Median, QA60",
    "mediana_cs": "Median, Cloud Score+",
    "dia06_cs": "6 May only, Cloud Score+",
    "maxagua_cs": "Maximum water (MNDWI), Cloud Score+",
}
LAND_COVER = {1: "Urban", 2: "Water bodies", 3: "Farming and pasture",
              4: "Natural vegetation", 5: "Other", 6: "Irrigated rice"}


def label(index, masked):
    name = {"FLOODHI": "FLOOD-HI", "AWEI": "AWEIsh"}.get(index, index)
    return name + (" + masks" if masked else "")
