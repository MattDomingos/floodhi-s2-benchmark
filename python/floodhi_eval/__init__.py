"""Evaluation utilities for the FLOOD-HI / Sentinel-2 flood-mapping benchmark.

The package reads the tables exported by the Google Earth Engine scripts in
``gee/`` and derives every threshold, metric and uncertainty estimate reported
in the paper.
"""
from .metrics import scores, f1
from .histograms import Histogram, HistogramSet, read_histograms
from .io import read_confusion_csv, read_grouped_sums, read_sample, CONFIGS
from .bootstrap import municipality_bootstrap

__all__ = ["scores", "f1", "Histogram", "HistogramSet", "read_histograms",
           "read_confusion_csv", "read_grouped_sums", "read_sample", "CONFIGS",
           "municipality_bootstrap"]
