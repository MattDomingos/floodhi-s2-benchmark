# Data dictionary

`exports/` holds the Earth Engine exports used in the paper, and `spatial/` the study domains
and DAA polygons read by the Earth Engine scripts (see `spatial/README.md`). Field names are kept as in the
original runs (Portuguese abbreviations) so that archived exports and new runs are
interchangeable. `ROI1` is the calibration domain and `ROI2` the test domain.

| File | Script | Content |
|---|---|---|
| `ROI*_A_cenas_sentinel2.csv` | 01 | Sentinel-2 acquisitions: date (`data`), tile, satellite, processing baseline, scene cloud percentage and QA60 cloud fraction inside the domain (`frac_nuvem_qa60_na_roi`). |
| `ROI*_B_histogramas.geojson` | 01 | One feature per municipality (`NM_MUN`) and index (`indice`); `groups` lists histograms (`[bin lower edge, pixel count]`) for `grupo` = 2 × reference + mask (0 dry/rejected, 1 dry/passed, 2 flooded/rejected, 3 flooded/passed). |
| `ROI*_C_matrizes_confusao.csv` | 01 | Per municipality, confusion counts at the zero threshold (`<detector>_<TP/FP/FN/TN>`) and domain counts (`n_total` all pixels, `n_valido` valid pixels, `n_ref_valido` valid DAA pixels, `obs0` ... `obs3mais` pixels with 0, 1, 2 and three or more cloud-free observations, `ref_obs*` the same inside the DAA). |
| `ROI*_D_mapa_observacoes_validas.tif` | 01 | Number of cloud-free observations per pixel, 30 m. |
| `ROI*_v3_B_histogramas.geojson` | 02 | As export B, per composite (`variante`), with `grupo` = 4 × reference + 2 × mask + common area. |
| `ROI*_v3_S_estratos.geojson` | 02 | Per municipality, band sums grouped by `estrato` = 10 × land cover + cloud-free observations (0, 1, 2, 3 = three or more); band names in `bandas` (`<composite>__<detector>_<TP/FP/FN/TN>`, `n_ref` DAA pixels). |
| `ROI*_v3_E_amostra_pareada.csv` | 02 | 6,000 random points: `REF` (DAA), `uso` (land cover), `obs`, `comum` (valid in all composites), bands `<composite>_<band>` (−1 = no data) and validity flags `valido_<composite>`. |
| `ROI*_v4_celulas.csv`, `ROI*_v4_*_30m.tif` | 04 | Grid-cell statistics for the example windows; 30 m agreement (1 TN, 2 FN, 3 FP, 4 TP) and land-cover maps. |
| `ROI*_janela_{A,B,C}.png` | 04 | Example windows A, B and C (true colour, land cover, agreement of FLOOD-HI + masks with the DAA), saved from the links printed by the script. |
| `ROI*_v5_buffer_borda.geojson` | 03 | Band sums grouped by distance class to the DAA boundary (`faixa`). |
| `ROI*_v7_TCW_histogramas.geojson`, `ROI1_v7_contagem_treino.csv` | 05 | TCW histograms with Crist and Sentinel-2 coefficients; counts of the original training sample. |
| `ROI*_v8_relevo_daa.geojson` | 06 | Band sums grouped by terrain class (`classe` = 5 × slope class + HAND class). |

Land-cover codes (`uso`): 1 urban, 2 water bodies (MapBiomas 26, 31, 33), 3 farming and pasture, 4 natural
vegetation, 5 other, 6 irrigated rice. Composite codes: `mediana_qa60` (median, QA60),
`mediana_cs` (median, Cloud Score+), `dia06_cs` (6 May 2024), `maxagua_cs` (maximum MNDWI).
Counts are pixel-equivalents of 10 m pixels; pixels on municipal boundaries are weighted by
the fraction of their area inside, so counts may be fractional.
