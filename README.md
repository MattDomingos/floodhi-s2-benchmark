# floodhi-s2-benchmark

Code and data for the paper

> Domingos, M., Coelho, G. P., Wendland, E. C., Lucas, M. C. *Assessing the added value of
> spectral-index fusion for Sentinel-2 flood mapping: A reproducible wall-to-wall evaluation
> of the 2024 Rio Grande do Sul State floods.* Computers & Geosciences (under review).

The study scores four water indices (NDWI, MNDWI, AWEI<sub>sh</sub>, TCW), a calibrated
six-index fusion (FLOOD-HI), NIR/SWIR reflectance masks and statistical classifiers against
the official Directly Affected Area (DAA) of the May 2024 floods in Rio Grande do Sul, Brazil.
Every valid 10 m pixel of two domains is evaluated: ROI-1 (calibration, 9 municipalities)
and ROI-2 (test, 14 municipalities).

The workflow has two parts:

1. **Google Earth Engine** (`gee/`) builds the Sentinel-2 composites, computes indices, masks
   and the reference, and exports class-conditional histograms, confusion counts and random
   point samples. Every wall-to-wall detector is scored on the same valid pixels.
2. **Python** (`python/`) reads those exports and derives every threshold, metric,
   uncertainty interval and table reported in the paper.

The Earth Engine exports used in the paper are archived in `data/exports/`, so the Python
part reproduces all reported numbers without an Earth Engine account.

## Quick start (Python only)

Requires Python 3.10 or later.

```bash
pip install -r python/requirements.txt
python run_all.py              # rewrites every table in results/ (a few minutes)
python run_all.py --figures    # also draws Figs. 2, 3 and 8 in figures/output/
```

Each script can also be run on its own from the `python/` folder, e.g.
`python 02_threshold_protocols.py`. Scripts print their tables and write them to `results/`.

## Repository layout

```
gee/                                  Earth Engine Code Editor scripts (JavaScript)
  00_export_spatial_inputs.js         exports the domain and DAA assets as GeoJSON (data/spatial/)
  01_wall_to_wall_evaluation.js       QA60 composite; histograms, confusion and observation counts
  02_composite_comparison.js          four composites; land-cover strata; random points
  03_boundary_buffer.js               agreement by distance to the DAA boundary
  04_example_windows_and_maps.js      automatic example windows; 30 m agreement maps
  05_tcw_sensitivity_and_training_sample.js   TCW with Sentinel-2 coefficients; training sample
  06_terrain_screen.js                slope and HAND screen of the DAA
python/
  floodhi_eval/                       reusable package (readers, metrics, histograms, bootstrap)
  01_zero_threshold.py ... 09_observation_counts.py   one script per group of results
  common.py, requirements.txt
figures/                              scripts for Figs. 2, 3 and 8 (output in figures/output/)
tools/                                shapefiles of data/spatial/ from the GeoJSON; check of the DAA
data/
  exports/                            Earth Engine exports used in the paper
  spatial/                            study domains and DAA used in the paper (GeoJSON, shapefile)
  README.md                           data dictionary
results/                              tables written by the Python scripts (incl. Data S1)
run_all.py                            runs every analysis script in order
```

## Which script produces which result

| Result in the paper | Earth Engine script (export) | Python script |
|---|---|---|
| Table 1, Fig. 3, Section 4.1 | 01 (A, C), 02 (B) | `09_observation_counts.py`, `figures/fig03_observations.py` |
| Table S1 (acquisitions) | 01 (A) | (read directly) |
| Table 5, Table S4 | 01 (C) | `01_zero_threshold.py` |
| Table 4, Table 6, Table S6, Table S7, Fig. 5 | 01 (B) | `02_threshold_protocols.py` |
| Fig. 6c, **Data S1** | 02 (B) | `03_composites_and_data_s1.py` |
| Fig. 7, Fig. 8, Table S2, recall by observations | 02 (S) | `04_land_cover_and_municipalities.py`, `figures/fig08_expected_recall.py` |
| Table 7, Table S3, Fig. S1, collinearity | 02 (E) | `05_sample_based_analyses.py` |
| Table S5 | 03 | `06_boundary_buffer.py` |
| Figs. 9, 10, S3 (example windows and maps) | 04 | (PNG and GeoTIFF exports) |
| Table S8, training-sample counts | 05 | `07_tcw_sensitivity.py` |
| Table S9 | 06 | `08_terrain_screen.py` |
| Fig. 2 (workflow) | 01, 04 | `figures/fig02_data.py`, then `figures/fig02_workflow.py` |

Data S1, the machine-readable file of thresholds, metrics and confusion counts for every
domain, composite, evaluation population, detector and thresholding protocol, is
`results/data_S1_thresholds_metrics_counts.csv`. It is written with fixed precision, so a
rerun gives an identical file. The values plotted in the figures without a script are in
the tables of `results/` listed above.

## Running the Earth Engine scripts

1. Upload the four shapefiles of `data/spatial/` as table assets in your Earth Engine
   project (Assets > New > Shape files; select the `.shp`, `.shx`, `.dbf`, `.prj` and `.cpg`
   of a layer together).
2. In each script, put the four asset paths in the `ASSETS` block, set `DOMAIN = 'ROI1'`,
   click Run and start the export tasks in the *Tasks* tab. Repeat with `DOMAIN = 'ROI2'`.
3. Download the exports from Google Drive (folder `FLOODHI_exports`) into `data/exports/`.
   File names are set by the scripts and expected by the Python code. Script 04 also prints
   links to the example-window PNGs; save them as `ROI1_janela_A.png`, etc.

`gee/00_export_spatial_inputs.js` exported the GeoJSON files of `data/spatial/` from the
assets of the original runs, and `tools/spatial_shapefiles.py` wrote the shapefiles from them
(see `data/spatial/README.md`). Neither is needed for reproduction.
`python tools/check_spatial_inputs.py` checks, municipality by municipality, that the DAA
polygons give the DAA area painted by the Earth Engine scripts.

## Reproducibility settings

* All reductions run at a fixed 10 m scale in EPSG:32722 (WGS 84 / UTM zone 22S), with
  `tileScale` 4 (8 in scripts 03 and 06) and without `bestEffort`, so Earth Engine never
  coarsens the working resolution. Where a pixel limit applies (`reduceRegion`, image
  exports), `maxPixels` is 1e10. If a task fails for lack of memory, raise `TILE_SCALE`.
* Random elements are fixed: Earth Engine random points and the training sample use seed 42;
  the municipality bootstrap uses NumPy seed 1 (2000 replicates); the test-point bootstrap
  of Table 7 uses NumPy seed 3 (2000 replicates); the random forest uses `random_state=0`.
* The archived results were produced with Python 3.13, NumPy 2.5, pandas 3.0, SciPy 1.18,
  scikit-learn 1.9 and Matplotlib 3.11. Other versions give the same tables, except possibly
  in the last digits of the random-forest row of Table 7.

## Key methodological choices

* **One pixel population.** A pixel is evaluated if it lies inside the domain and all eight
  bands of the composite have at least one cloud-free observation. This mask is built from
  the composite alone, before any detector is applied. Predictions are unmasked before
  scoring, so mask-rejected pixels count as negatives instead of being dropped.
* **Pixel code.** Each pixel is encoded as 2 × prediction + reference (0 TN, 1 FN, 2 FP, 3 TP).
* **Thresholds from histograms.** Index values are clamped into each histogram range, so the
  histograms hold every valid pixel; confusion counts are exact at bin edges, and all
  threshold searches use those edges (ties resolved to the lowest edge). A pixel is labelled
  water when its index value is at or above the threshold. The zero protocol uses
  index > 0, as in the original FLOOD-HI rule.
* **Threshold transfer.** Thresholds are selected on ROI-1 and applied unchanged to ROI-2. The
  oracle protocol uses ROI-2 labels and is reported only as a diagnostic.
* **Uncertainty.** Pixels are spatially autocorrelated, so intervals come from a bootstrap of
  the 14 ROI-2 municipalities. They assume independence between municipalities and are
  approximate.

## Data sources

* Sentinel-2 Level-2A surface reflectance (`COPERNICUS/S2_SR_HARMONIZED`) and Cloud Score+
  (`GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED`), Google Earth Engine catalogue.
* MapBiomas Collection 9 land cover, 2023 (`projects/mapbiomas-public/assets/brazil/lulc/collection9/mapbiomas_collection90_integration_v1`).
* Copernicus GLO-30 DEM and MERIT Hydro (HAND), Google Earth Engine catalogue.
* Directly Affected Area (DAA), layer "ADA 03/09/2024" (version of 3 September 2024), State
  Spatial Data Infrastructure of Rio Grande do Sul (IEDE-RS, SPGG-RS), metadata record
  `63862411-8B51-4E08-A4BA-D624783C453A`. The polygons inside the two domains are in
  `data/spatial/`.
* Municipal boundaries: IBGE.

## Citation and licence

Please cite the paper and the archived release of this repository. Each release is archived
on Zenodo; the DOI of the version used in the paper is given in its Code availability
section and on the Zenodo record linked from the GitHub release page. Citation metadata are
in `CITATION.cff`.

Code is released under the MIT licence (see `LICENSE`). Third-party data keep their own terms.

## Contact

Mateus Domingos, School of Technology, Universidade Estadual de Campinas (mdomingos32@gmail.com).
