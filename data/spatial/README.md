# Spatial inputs

The study domains and the DAA exactly as used in the Earth Engine runs of the paper.

| Layer | Files | Features | Content |
|---|---|---|---|
| ROI-1 domain | `ROI1_municipalities.*` | 9 | Municipalities of the calibration domain (IBGE municipal boundaries; name in `NM_MUN`) |
| ROI-1 DAA | `ROI1_DAA.*` | 9 | Directly Affected Area clipped to each ROI-1 municipality |
| ROI-2 domain | `ROI2_municipalities.*` | 14 | Municipalities of the test domain |
| ROI-2 DAA | `ROI2_DAA.*` | 14 | Directly Affected Area clipped to each ROI-2 municipality |

Coordinates are geographic (WGS 84 longitude, latitude). Attributes are the IBGE municipal
attributes (`CD_MUN`, `NM_MUN`, `AREA_KM2`, ...).

## Two formats

* **GeoJSON** (`.geojson`): the Earth Engine table assets read by scripts 01-06, exported
  unchanged with `gee/00_export_spatial_inputs.js`. These are the reference files.
* **Shapefile** (`.shp`, `.shx`, `.dbf`, `.prj`, `.cpg`): written from the GeoJSON files by
  `tools/spatial_shapefiles.py`, for upload to Earth Engine or use in a GIS.

Clipping the DAA to the municipal boundaries left most DAA features as geometry collections:
polygons plus line and point fragments along the boundaries. A shapefile holds a single
geometry type, so each shapefile record keeps all polygon parts of its feature and drops the
fragments, which have no area. The polygon coordinates are those of the GeoJSON.

`python tools/check_spatial_inputs.py` compares, municipality by municipality, the area of the
DAA polygons with the DAA area painted at 10 m by the Earth Engine scripts (`n_ref` of export C
of script 01). They agree within 0.2% for every municipality; in total 919.6 vs 918.7 km2 in
ROI-1 and 3024.0 vs 3024.3 km2 in ROI-2. The fragments therefore add nothing to the reference.

## Source

The DAA comes from the layer "ADA 03/09/2024" (version of 3 September 2024) of the Rio Grande
do Sul State Spatial Data Infrastructure (IEDE-RS, SPGG-RS), metadata record
`63862411-8B51-4E08-A4BA-D624783C453A`. The full statewide layer is available from IEDE-RS
and is not redistributed here.

To rerun the Earth Engine scripts with these files, upload each shapefile as a table asset
(Assets > New > Shape files, selecting the `.shp`, `.shx`, `.dbf`, `.prj` and `.cpg` together)
and put the four asset paths in the `ASSETS` block at the top of scripts 01-06.
