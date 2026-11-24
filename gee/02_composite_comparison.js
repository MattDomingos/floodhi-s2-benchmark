/**
 * 02 - Composites, land-cover strata and random-point samples
 * -----------------------------------------------------------------------------
 * Builds four composites and exports, per municipality:
 *   B  class-conditional histograms per composite, split by reference class,
 *      mask status and membership of the area valid in all four composites
 *      (Fig. 6c, Data S1)
 *   S  confusion counts per land-cover stratum and number of cloud-free
 *      observations (Fig. 7, Fig. 8, Table S2)
 *   E  6,000 random points per domain with bands of every composite
 *      (Table 7, Table S3, Fig. S1)
 *
 * Composites: median with QA60 (reference), median with Cloud Score+,
 * single date 6 May 2024 with Cloud Score+, and maximum water (per-pixel
 * observation with the highest MNDWI) with Cloud Score+ (cs_cdf >= 0.60).
 * Land cover: MapBiomas Collection 9, 2023, grouped into six strata.
 */

// ---------------------------------------------------------------- settings --
var DOMAIN = 'ROI1';
var ASSETS = {
  ROI1: {domain: 'projects/YOUR_PROJECT/assets/ROI1_municipalities', daa: 'projects/YOUR_PROJECT/assets/ROI1_DAA'},
  ROI2: {domain: 'projects/YOUR_PROJECT/assets/ROI2_municipalities', daa: 'projects/YOUR_PROJECT/assets/ROI2_DAA'}
};
var CRS = 'EPSG:32722', SCALE = 10, FOLDER = 'FLOODHI_exports', TILE_SCALE = 4;
var CS_THRESHOLD = 0.60;                   // Cloud Score+ clear-sky score
var N_POINTS = 6000, SEED = 42;

var domain = ee.FeatureCollection(ASSETS[DOMAIN].domain);
var daa = ee.FeatureCollection(ASSETS[DOMAIN].daa);
var geom = domain.geometry();

// ------------------------------------------------------------ composites --
var BANDS = ['B2', 'B3', 'B4', 'B6', 'B7', 'B8', 'B11', 'B12'];
var s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(geom);
var csPlus = ee.ImageCollection('GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED');

function qa60Collection(start, end) {
  return s2.filterDate(start, end).map(function(img) {
    var qa = img.select('QA60');
    var clear = qa.bitwiseAnd(1 << 10).eq(0).and(qa.bitwiseAnd(1 << 11).eq(0));
    return img.select(BANDS).updateMask(clear).divide(10000);
  });
}
function cloudScoreCollection(start, end) {
  return s2.filterDate(start, end).linkCollection(csPlus, ['cs_cdf']).map(function(img) {
    return img.select(BANDS).updateMask(img.select('cs_cdf').gte(CS_THRESHOLD)).divide(10000);
  });
}
/** Keep, for each pixel, the observation with the highest MNDWI. */
function maximumWater(col) {
  return col.map(function(img) {
    return img.addBands(img.normalizedDifference(['B3', 'B11']).rename('q'));
  }).qualityMosaic('q').select(BANDS);
}

var NAMES = ['mediana_qa60', 'mediana_cs', 'dia06_cs', 'maxagua_cs'];   // codes used in the exports
var COMPOSITES = {
  mediana_qa60: qa60Collection('2024-04-28', '2024-05-12').median(),
  mediana_cs: cloudScoreCollection('2024-04-28', '2024-05-12').median(),
  dia06_cs: cloudScoreCollection('2024-05-06', '2024-05-07').median(),
  maxagua_cs: maximumWater(cloudScoreCollection('2024-04-28', '2024-05-12'))
};
var VALID = {};
NAMES.forEach(function(n) { VALID[n] = COMPOSITES[n].mask().reduce(ee.Reducer.min()).gt(0).unmask(0); });
var common = NAMES.map(function(n) { return VALID[n]; })
  .reduce(function(a, b) { return a.and(b); }).rename('comum');

// --------------------------------------------------- indices and masks --
function indices(img) {
  var b = function(name) { return img.select(name); };
  var ndwi = img.normalizedDifference(['B3', 'B8']).rename('NDWI');
  var mndwi = img.normalizedDifference(['B3', 'B11']).rename('MNDWI');
  var imp = ndwi.add(img.normalizedDifference(['B2', 'B8'])).rename('IMP');
  var awei = img.expression('B2 + 2.5*B3 - 1.5*(B8 + B11) - 0.25*B12',
    {B2: b('B2'), B3: b('B3'), B8: b('B8'), B11: b('B11'), B12: b('B12')}).rename('AWEI');
  var tcw = img.expression('0.0315*B2 + 0.2021*B3 + 0.3102*B4 + 0.1594*B8 - 0.6806*B11 - 0.6109*B12',
    {B2: b('B2'), B3: b('B3'), B4: b('B4'), B8: b('B8'), B11: b('B11'), B12: b('B12')}).rename('TCW');
  var ndvi = img.normalizedDifference(['B8', 'B4']).rename('NDVI');
  var savi = img.expression('1.5*(B8 - B4)/(B8 + B4 + 0.5)', {B8: b('B8'), B4: b('B4')}).rename('SAVI');
  var floodhi = ndwi.multiply(3.72).add(imp.multiply(-2.67)).add(awei.multiply(2.69))
    .add(tcw.multiply(-1.77)).add(ndvi.multiply(-2.67)).add(savi.multiply(3.30)).rename('FLOODHI');
  return ee.Image.cat([ndwi, mndwi, imp, awei, tcw, ndvi, savi, floodhi]);
}
function reflectanceMasks(img) {
  return img.select('B11').lt(0.12).and(img.select('B6').lt(0.20))
    .and(img.select('B7').lt(0.20)).and(img.select('B8').lt(0.20)).unmask(0).rename('MASCARA');
}
var ref = ee.Image(0).byte().paint(daa, 1).rename('REF');

// ---------------------------------------------------- land-cover strata --
// 1 urban, 2 water bodies (MapBiomas 26, 31, 33), 3 farming and pasture, 4 natural vegetation, 5 other, 6 irrigated rice
var STRATA = {
  1: [24], 2: [33, 31, 26],
  3: [14, 15, 18, 19, 39, 20, 62, 41, 36, 46, 47, 35, 48, 9, 21],
  4: [1, 3, 4, 5, 6, 49, 10, 11, 12, 32, 29, 50, 13], 6: [40]
};
var from = [], to = [];
Object.keys(STRATA).forEach(function(k) { STRATA[k].forEach(function(c) { from.push(c); to.push(Number(k)); }); });
var landCover = ee.Image('projects/mapbiomas-public/assets/brazil/lulc/collection9/mapbiomas_collection90_integration_v1')
  .select('classification_2023').remap(from, to, 5).unmask(5).rename('uso');
var nObs = qa60Collection('2024-04-28', '2024-05-12').select('B8').count().unmask(0);
var obsClass = nObs.min(3).rename('obs');                       // 0, 1, 2, 3 = three or more
var stratum = landCover.multiply(10).add(obsClass).rename('estrato');

// ------------------------------------------------------- B: histograms --
var HISTOGRAMS = [
  {name: 'FLOODHI', min: -6, max: 6, bins: 1200}, {name: 'NDWI', min: -1, max: 1, bins: 400},
  {name: 'MNDWI', min: -1, max: 1, bins: 400},     {name: 'AWEI', min: -3, max: 2, bins: 1000},
  {name: 'TCW', min: -1, max: 0.5, bins: 600}
];
var histogramList = [];
NAMES.forEach(function(n) {
  var idx = indices(COMPOSITES[n]);
  // grupo = 4 * reference + 2 * mask + common area
  var group = ref.multiply(4).add(reflectanceMasks(COMPOSITES[n]).multiply(2)).add(common).rename('grupo');
  HISTOGRAMS.forEach(function(h) {
    var width = (h.max - h.min) / h.bins;
    var img = idx.select(h.name).clamp(h.min, h.max - width / 2).addBands(group).updateMask(VALID[n]);
    var reducer = ee.Reducer.fixedHistogram(h.min, h.max, h.bins).group({groupField: 1, groupName: 'grupo'});
    histogramList.push(img.reduceRegions({collection: domain, reducer: reducer, scale: SCALE, crs: CRS,
                                          tileScale: TILE_SCALE})
      .map(function(f) {
        return ee.Feature(null, {NM_MUN: f.get('NM_MUN'), feat_id: f.id(), variante: n,
                                 indice: h.name, groups: f.get('groups')});
      }));
  });
});

// ------------------------------------- S: confusion counts per stratum --
var bandNames = ['n_total', 'n_ref', 'n_comum', 'n_ref_comum'];
var bands = [ee.Image(1).rename('n_total'), ref.rename('n_ref'), common.rename('n_comum'),
             common.and(ref).rename('n_ref_comum')];
NAMES.forEach(function(n) {
  var idx = indices(COMPOSITES[n]), m = reflectanceMasks(COMPOSITES[n]), v = VALID[n];
  var DETECTORS = [['FHI_M', idx.select('FLOODHI').gt(0).and(m)], ['FHI', idx.select('FLOODHI').gt(0)],
                   ['MASC', m], ['MNDWI_M', idx.select('MNDWI').gt(0).and(m)], ['TCW', idx.select('TCW').gt(0)]];
  bandNames.push(n + '_valido');
  bands.push(v.rename(n + '_valido'));
  DETECTORS.forEach(function(d) {
    var code = d[1].unmask(0).multiply(2).add(ref);             // 0 TN, 1 FN, 2 FP, 3 TP
    ['TN', 'FN', 'FP', 'TP'].forEach(function(k, i) {
      var name = n + '__' + d[0] + '_' + k;
      bandNames.push(name);
      bands.push(code.eq(i).and(v).rename(name));
    });
  });
});
var nb = bandNames.length;
var strataTable = ee.Image.cat(bands).addBands(stratum)               // stratum is the last band
  .reduceRegions({collection: domain, reducer: ee.Reducer.sum().repeat(nb).group({groupField: nb, groupName: 'estrato'}),
                  scale: SCALE, crs: CRS, tileScale: TILE_SCALE})
  .map(function(f) {
    return ee.Feature(null, {NM_MUN: f.get('NM_MUN'), feat_id: f.id(), bandas: bandNames.join(','),
                             groups: f.get('groups')});
  });

// ------------------------------------------------------ E: random points --
var points = ee.FeatureCollection.randomPoints({region: geom, points: N_POINTS, seed: SEED, maxError: 1});
var stack = [ref, landCover, obsClass, common];
NAMES.forEach(function(n) {
  stack.push(COMPOSITES[n].unmask(-1).rename(BANDS.map(function(b) { return n + '_' + b; })));
  stack.push(VALID[n].rename('valido_' + n));
});
var sample = ee.Image.cat(stack).sampleRegions({collection: points, scale: SCALE,
  projection: ee.Projection(CRS), geometries: true, tileScale: TILE_SCALE});

// --------------------------------------------------------------- exports --
Export.table.toDrive({collection: ee.FeatureCollection(histogramList).flatten(),
                      description: DOMAIN + '_v3_B_histogramas', folder: FOLDER, fileFormat: 'GeoJSON'});
Export.table.toDrive({collection: strataTable, description: DOMAIN + '_v3_S_estratos',
                      folder: FOLDER, fileFormat: 'GeoJSON'});
Export.table.toDrive({collection: sample, description: DOMAIN + '_v3_E_amostra_pareada',
                      folder: FOLDER, fileFormat: 'CSV'});

Map.centerObject(domain, 10);
NAMES.forEach(function(n, i) {
  Map.addLayer(COMPOSITES[n].clip(geom), {bands: ['B4', 'B3', 'B2'], min: 0, max: 0.3, gamma: 1.4}, n, i === 0);
});
Map.addLayer(common.selfMask().clip(geom), {palette: ['00aa00']}, 'Valid in all four composites', false);
