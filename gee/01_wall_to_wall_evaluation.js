/**
 * 01 - Wall-to-wall evaluation (QA60 median composite)
 * -----------------------------------------------------------------------------
 * Paper: "Assessing the added value of spectral-index fusion for Sentinel-2
 *         flood mapping: A reproducible wall-to-wall evaluation of the 2024
 *         Rio Grande do Sul State floods"
 *
 * Builds the QA60 median composite (28 Apr - 11 May 2024), computes the water
 * indices, FLOOD-HI (Eq. 1) and the reflectance masks, and exports per
 * municipality:
 *   A  Sentinel-2 acquisitions and their QA60 cloud fraction   (Table S1, Fig. 3a, b)
 *   B  class-conditional histograms of every index             (Tables 4, 6, S6, S7)
 *   C  confusion counts at the zero threshold, 11 detectors     (Table 5, Table S4)
 *      and pixels by number of cloud-free observations          (Table 1, Fig. 3c)
 *   D  map of cloud-free observations per pixel (30 m)          (Fig. S4)
 *
 * Every detector is scored on the same pixel population: valid composite
 * pixels inside the domain. Mask-rejected or undetected pixels are counted as
 * negatives (predictions are unmasked before scoring). Pixel code:
 * 2 * prediction + reference -> 0 TN, 1 FN, 2 FP, 3 TP.
 *
 * Usage: set DOMAIN, run, start the export tasks; repeat with the other domain.
 * Export field names are kept as in the original runs (see data/README.md).
 */

// ---------------------------------------------------------------- settings --
var DOMAIN = 'ROI1';                       // 'ROI1' (calibration) or 'ROI2' (test)
var ASSETS = {                             // municipality polygons (field NM_MUN) and DAA polygons
  ROI1: {domain: 'projects/YOUR_PROJECT/assets/ROI1_municipalities',
         daa:    'projects/YOUR_PROJECT/assets/ROI1_DAA'},
  ROI2: {domain: 'projects/YOUR_PROJECT/assets/ROI2_municipalities',
         daa:    'projects/YOUR_PROJECT/assets/ROI2_DAA'}
};
var START = '2024-04-28', END = '2024-05-12';   // END is exclusive
var CRS = 'EPSG:32722';                          // WGS 84 / UTM zone 22S
var SCALE = 10;                                  // metres; never use bestEffort
var FOLDER = 'FLOODHI_exports';
var TILE_SCALE = 4;                              // raise to 8 or 16 on memory errors

var domain = ee.FeatureCollection(ASSETS[DOMAIN].domain);
var daa = ee.FeatureCollection(ASSETS[DOMAIN].daa);
var geom = domain.geometry();

// ------------------------------------------------------------- composite --
var BANDS = ['B2', 'B3', 'B4', 'B6', 'B7', 'B8', 'B11', 'B12'];

/** Mask opaque clouds and cirrus (QA60 bits 10 and 11) and scale to reflectance. */
function maskQA60(img) {
  var qa = img.select('QA60');
  var clear = qa.bitwiseAnd(1 << 10).eq(0).and(qa.bitwiseAnd(1 << 11).eq(0));
  return img.select(BANDS).updateMask(clear).divide(10000);
}

var collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterBounds(geom).filterDate(START, END);
var clearCollection = collection.map(maskQA60);
var s2 = clearCollection.median();

// Valid pixel: every band has at least one cloud-free observation.
var valid = s2.mask().reduce(ee.Reducer.min()).gt(0).unmask(0).rename('valido');
var nObs = clearCollection.select('B8').count().unmask(0).rename('n_obs');

// --------------------------------------------------------------- indices --
/** Water and vegetation indices of Table 3 and FLOOD-HI (Eq. 1). */
function indices(img) {
  var b = function(name) { return img.select(name); };
  var ndwi = img.normalizedDifference(['B3', 'B8']).rename('NDWI');
  var mndwi = img.normalizedDifference(['B3', 'B11']).rename('MNDWI');
  var imp = ndwi.add(img.normalizedDifference(['B2', 'B8'])).rename('IMP');
  var awei = img.expression('B2 + 2.5*B3 - 1.5*(B8 + B11) - 0.25*B12',
    {B2: b('B2'), B3: b('B3'), B8: b('B8'), B11: b('B11'), B12: b('B12')}).rename('AWEI');
  var tcw = img.expression(
    '0.0315*B2 + 0.2021*B3 + 0.3102*B4 + 0.1594*B8 - 0.6806*B11 - 0.6109*B12',
    {B2: b('B2'), B3: b('B3'), B4: b('B4'), B8: b('B8'), B11: b('B11'), B12: b('B12')}).rename('TCW');
  var ndvi = img.normalizedDifference(['B8', 'B4']).rename('NDVI');
  var savi = img.expression('1.5*(B8 - B4)/(B8 + B4 + 0.5)', {B8: b('B8'), B4: b('B4')}).rename('SAVI');
  var floodhi = ndwi.multiply(3.72).add(imp.multiply(-2.67)).add(awei.multiply(2.69))
    .add(tcw.multiply(-1.77)).add(ndvi.multiply(-2.67)).add(savi.multiply(3.30)).rename('FLOODHI');
  return ee.Image.cat([ndwi, mndwi, imp, awei, tcw, ndvi, savi, floodhi]);
}
var idx = indices(s2);

// Reflectance masks: 1 = pixel passes B11 < 0.12 and B6, B7, B8 < 0.20.
var masks = s2.select('B11').lt(0.12).and(s2.select('B6').lt(0.20))
  .and(s2.select('B7').lt(0.20)).and(s2.select('B8').lt(0.20)).unmask(0).rename('MASCARA');
// Reference: 1 where the pixel centre falls inside a DAA polygon.
var ref = ee.Image(0).byte().paint(daa, 1).rename('REF');

// ------------------------------------------- C: confusion counts at zero --
var DETECTORS = [
  ['FHI', idx.select('FLOODHI').gt(0)],   ['FHI_M', idx.select('FLOODHI').gt(0).and(masks)],
  ['MASC', masks],
  ['NDWI', idx.select('NDWI').gt(0)],     ['NDWI_M', idx.select('NDWI').gt(0).and(masks)],
  ['MNDWI', idx.select('MNDWI').gt(0)],   ['MNDWI_M', idx.select('MNDWI').gt(0).and(masks)],
  ['AWEI', idx.select('AWEI').gt(0)],     ['AWEI_M', idx.select('AWEI').gt(0).and(masks)],
  ['TCW', idx.select('TCW').gt(0)],       ['TCW_M', idx.select('TCW').gt(0).and(masks)]
];
var confusionBands = [];
DETECTORS.forEach(function(d) {
  var code = d[1].unmask(0).multiply(2).add(ref);           // 0 TN, 1 FN, 2 FP, 3 TP
  ['TN', 'FN', 'FP', 'TP'].forEach(function(k, i) {
    confusionBands.push(code.eq(i).rename(d[0] + '_' + k));
  });
});
var domainCounts = ee.Image.cat([
  ee.Image(1).rename('n_total'), valid.rename('n_valido'), ref.rename('n_ref'),
  ref.and(valid).rename('n_ref_valido'), masks.and(valid).rename('n_masc'),
  ref.and(masks).and(valid).rename('n_ref_masc'),
  nObs.eq(0).rename('obs0'), nObs.eq(1).rename('obs1'), nObs.eq(2).rename('obs2'),
  nObs.gte(3).rename('obs3mais'), nObs.eq(0).and(ref).rename('ref_obs0'),
  nObs.eq(1).and(ref).rename('ref_obs1'), nObs.eq(2).and(ref).rename('ref_obs2'),
  nObs.gte(3).and(ref).rename('ref_obs3mais')
]);
var confusionTable = ee.Image.cat(confusionBands).updateMask(valid)   // same population for all
  .addBands(domainCounts)
  .reduceRegions({collection: domain, reducer: ee.Reducer.sum(), scale: SCALE, crs: CRS,
                  tileScale: TILE_SCALE})
  .map(function(f) { return ee.Feature(null, f.toDictionary()).set('feat_id', f.id()); });

// ---------------------------------------- B: class-conditional histograms --
// grupo = 2 * reference + mask: 0 dry/rejected, 1 dry/passed, 2 flooded/rejected, 3 flooded/passed.
var group = ref.multiply(2).add(masks).rename('grupo');
var HISTOGRAMS = [                        // range [min, max) and number of bins
  {name: 'FLOODHI', min: -6, max: 6, bins: 1200},
  {name: 'NDWI', min: -1, max: 1, bins: 400},
  {name: 'MNDWI', min: -1, max: 1, bins: 400},
  {name: 'AWEI', min: -3, max: 2, bins: 1000},
  {name: 'TCW', min: -1, max: 0.5, bins: 600}
];
var histogramTable = ee.FeatureCollection(HISTOGRAMS.map(function(h) {
  var width = (h.max - h.min) / h.bins;
  // Clamp so that no valid pixel falls outside the fixed histogram range.
  var img = idx.select(h.name).clamp(h.min, h.max - width / 2).addBands(group).updateMask(valid);
  var reducer = ee.Reducer.fixedHistogram(h.min, h.max, h.bins).group({groupField: 1, groupName: 'grupo'});
  return img.reduceRegions({collection: domain, reducer: reducer, scale: SCALE, crs: CRS,
                            tileScale: TILE_SCALE})
    .map(function(f) { return ee.Feature(null, f.toDictionary()).set({indice: h.name, feat_id: f.id()}); });
})).flatten();

// ------------------------------------------------------- A: acquisitions --
var scenes = ee.FeatureCollection(collection.map(function(img) {
  var qa = img.select('QA60');
  var cloudy = qa.bitwiseAnd(1 << 10).neq(0).or(qa.bitwiseAnd(1 << 11).neq(0));
  var fraction = cloudy.reduceRegion({reducer: ee.Reducer.mean(), geometry: geom, scale: 60,
                                      crs: CRS, maxPixels: 1e10, tileScale: TILE_SCALE}).values().get(0);
  return ee.Feature(null, {
    id: img.get('system:index'), data: img.date().format('YYYY-MM-dd'),
    hora_utc: img.date().format('HH:mm'), tile: img.get('MGRS_TILE'),
    satelite: img.get('SPACECRAFT_NAME'), baseline: img.get('PROCESSING_BASELINE'),
    nuvem_pct_cena: img.get('CLOUDY_PIXEL_PERCENTAGE'), frac_nuvem_qa60_na_roi: fraction
  });
}));

// --------------------------------------------------------------- exports --
Export.table.toDrive({collection: scenes, description: DOMAIN + '_A_cenas_sentinel2',
                      folder: FOLDER, fileFormat: 'CSV'});
Export.table.toDrive({collection: histogramTable, description: DOMAIN + '_B_histogramas',
                      folder: FOLDER, fileFormat: 'GeoJSON'});
Export.table.toDrive({collection: confusionTable, description: DOMAIN + '_C_matrizes_confusao',
                      folder: FOLDER, fileFormat: 'CSV'});
Export.image.toDrive({image: nObs.toByte().clip(geom), description: DOMAIN + '_D_mapa_observacoes_validas',
                      folder: FOLDER, region: geom.bounds(), crs: CRS, scale: 30, maxPixels: 1e10});

// ------------------------------------------------------------ inspection --
Map.centerObject(domain, 10);
Map.addLayer(s2.clip(geom), {bands: ['B4', 'B3', 'B2'], min: 0, max: 0.3, gamma: 1.4}, 'QA60 median composite');
Map.addLayer(ref.selfMask().clip(geom), {palette: ['0000ff']}, 'DAA', false);
Map.addLayer(idx.select('FLOODHI').clip(geom), {min: -1, max: 1, palette: ['white', 'blue']}, 'FLOOD-HI', false);
Map.addLayer(masks.selfMask().clip(geom), {palette: ['ff0000']}, 'Passes the masks', false);
