/**
 * 03 - Agreement by distance to the DAA boundary (Table S5)
 * -----------------------------------------------------------------------------
 * For every valid pixel, computes the distance to the nearest pixel of the
 * opposite DAA class inside the domain (the domain limit is not a DAA
 * boundary) and sums TP/FP/FN/TN per distance class:
 *   faixa 1 <= 15 m, 2 15-25 m, 3 25-35 m, 4 35-55 m, 5 > 55 m.
 * Excluding buffers of 10, 20, 30 and 50 m drops classes 1, 1-2, 1-3, 1-4.
 * Detectors: threshold zero (suffix _0) and thresholds transferred from ROI-1
 * (suffix _T, values from results/transferred_thresholds.csv).
 */

var DOMAIN = 'ROI1';
var ASSETS = {
  ROI1: {domain: 'projects/YOUR_PROJECT/assets/ROI1_municipalities', daa: 'projects/YOUR_PROJECT/assets/ROI1_DAA'},
  ROI2: {domain: 'projects/YOUR_PROJECT/assets/ROI2_municipalities', daa: 'projects/YOUR_PROJECT/assets/ROI2_DAA'}
};
var CRS = 'EPSG:32722', SCALE = 10, FOLDER = 'FLOODHI_exports', TILE_SCALE = 8;
var NEIGHBOURHOOD = 64;                  // pixels; farther distances fall in class 5

var domain = ee.FeatureCollection(ASSETS[DOMAIN].domain);
var daa = ee.FeatureCollection(ASSETS[DOMAIN].daa);
var geom = domain.geometry();
var proj10 = ee.Projection(CRS).atScale(SCALE);

// QA60 median composite, indices, FLOOD-HI and masks (as in script 01)
var BANDS = ['B2', 'B3', 'B4', 'B6', 'B7', 'B8', 'B11', 'B12'];
var s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(geom)
  .filterDate('2024-04-28', '2024-05-12').map(function(img) {
    var qa = img.select('QA60');
    var clear = qa.bitwiseAnd(1 << 10).eq(0).and(qa.bitwiseAnd(1 << 11).eq(0));
    return img.select(BANDS).updateMask(clear).divide(10000);
  }).median();
var inside = ee.Image(0).byte().paint(domain, 1).reproject(proj10);
var valid = s2.mask().reduce(ee.Reducer.min()).gt(0).unmask(0).and(inside).reproject(proj10);
var b = function(name) { return s2.select(name); };
var ndwi = s2.normalizedDifference(['B3', 'B8']);
var mndwi = s2.normalizedDifference(['B3', 'B11']);
var imp = ndwi.add(s2.normalizedDifference(['B2', 'B8']));
var awei = s2.expression('B2 + 2.5*B3 - 1.5*(B8 + B11) - 0.25*B12', {B2: b('B2'), B3: b('B3'), B8: b('B8'), B11: b('B11'), B12: b('B12')});
var tcw = s2.expression('0.0315*B2 + 0.2021*B3 + 0.3102*B4 + 0.1594*B8 - 0.6806*B11 - 0.6109*B12',
  {B2: b('B2'), B3: b('B3'), B4: b('B4'), B8: b('B8'), B11: b('B11'), B12: b('B12')});
var ndvi = s2.normalizedDifference(['B8', 'B4']);
var savi = s2.expression('1.5*(B8 - B4)/(B8 + B4 + 0.5)', {B8: b('B8'), B4: b('B4')});
var floodhi = ndwi.multiply(3.72).add(imp.multiply(-2.67)).add(awei.multiply(2.69))
  .add(tcw.multiply(-1.77)).add(ndvi.multiply(-2.67)).add(savi.multiply(3.30));
var masks = b('B11').lt(0.12).and(b('B6').lt(0.20)).and(b('B7').lt(0.20)).and(b('B8').lt(0.20)).unmask(0);

// Distance to the DAA boundary
var ref = ee.Image(0).byte().paint(daa, 1).reproject(proj10);
var d2Outside = ref.fastDistanceTransform(NEIGHBOURHOOD, 'pixels', 'squared_euclidean');
var d2Inside = ref.not().and(inside).fastDistanceTransform(NEIGHBOURHOOD, 'pixels', 'squared_euclidean');
var distance = ref.where(ref.eq(0), d2Outside).where(ref.eq(1), d2Inside)
  .unmask(1e6).sqrt().multiply(SCALE).reproject(proj10);           // metres
var band = ee.Image(5).where(distance.lte(55), 4).where(distance.lte(35), 3)
  .where(distance.lte(25), 2).where(distance.lte(15), 1).rename('faixa');

var DETECTORS = [
  ['FHI_M_0', floodhi.gt(0).and(masks)], ['FHI_0', floodhi.gt(0)], ['MASC', masks],
  ['MNDWI_0', mndwi.gt(0)], ['MNDWI_M_0', mndwi.gt(0).and(masks)], ['TCW_0', tcw.gt(0)],
  ['TCW_M_0', tcw.gt(0).and(masks)], ['AWEI_0', awei.gt(0)], ['AWEI_M_0', awei.gt(0).and(masks)],
  ['NDWI_0', ndwi.gt(0)], ['NDWI_M_0', ndwi.gt(0).and(masks)],
  ['FHI_M_T', floodhi.gte(-0.19).and(masks)], ['FHI_T', floodhi.gte(0.19)],
  ['MNDWI_M_T', mndwi.gte(-0.415).and(masks)], ['MNDWI_T', mndwi.gte(-0.055)],
  ['TCW_M_T', tcw.gte(-0.0575).and(masks)], ['TCW_T', tcw.gte(-0.0275)],
  ['AWEI_M_T', awei.gte(-0.275).and(masks)], ['AWEI_T', awei.gte(-0.17)],
  ['NDWI_M_T', ndwi.gte(-0.66).and(masks)], ['NDWI_T', ndwi.gte(-0.20)]
];
var names = ['n_valido', 'n_ref'];
var bands = [valid.rename('n_valido'), ref.and(valid).rename('n_ref')];
DETECTORS.forEach(function(d) {
  var code = d[1].unmask(0).multiply(2).add(ref);
  ['TN', 'FN', 'FP', 'TP'].forEach(function(k, i) {
    names.push(d[0] + '_' + k);
    bands.push(code.eq(i).and(valid).rename(d[0] + '_' + k));
  });
});
var nb = names.length;
var table = ee.Image.cat(bands).addBands(band).reduceRegions({
  collection: domain, reducer: ee.Reducer.sum().repeat(nb).group({groupField: nb, groupName: 'faixa'}),
  scale: SCALE, crs: CRS, tileScale: TILE_SCALE
}).map(function(f) {
  return ee.Feature(null, {NM_MUN: f.get('NM_MUN'), feat_id: f.id(), bandas: names.join(','), groups: f.get('groups')});
});
Export.table.toDrive({collection: table, description: DOMAIN + '_v5_buffer_borda', folder: FOLDER, fileFormat: 'GeoJSON'});

Map.centerObject(domain, 11);
Map.addLayer(band.clip(geom), {min: 1, max: 5, palette: ['d7301f', 'fc8d59', 'fdcc8a', 'c7e9b4', 'f0f0f0']},
             'Distance class to the DAA boundary');
