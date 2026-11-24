/**
 * 05 - TCW coefficient sensitivity (Table S8) and FLOOD-HI training sample
 * -----------------------------------------------------------------------------
 * (1) On the QA60 median composite, computes TCW with the Landsat TM
 *     coefficients of Crist (1985), used in the paper, and with the
 *     Sentinel-2 MSI coefficients of Shi and Xu (2019) (13 bands; B10 is not
 *     in Level-2A and its weight, 0.0003, is dropped). The Sentinel-2
 *     coefficients were derived for top-of-atmosphere reflectance, so applying
 *     them to surface reflectance is an approximation. Exports
 *     class-conditional histograms (bin width 0.001) per municipality.
 * (2) ROI-1 only: repeats the sampling call of the original FLOOD-HI fit
 *     (5,000 points, 30 m, seed 42) and counts valid flooded and non-flooded
 *     points.
 */

var DOMAIN = 'ROI1';
var ASSETS = {
  ROI1: {domain: 'projects/YOUR_PROJECT/assets/ROI1_municipalities', daa: 'projects/YOUR_PROJECT/assets/ROI1_DAA'},
  ROI2: {domain: 'projects/YOUR_PROJECT/assets/ROI2_municipalities', daa: 'projects/YOUR_PROJECT/assets/ROI2_DAA'}
};
var CRS = 'EPSG:32722', SCALE = 10, FOLDER = 'FLOODHI_exports', TILE_SCALE = 4;

var domain = ee.FeatureCollection(ASSETS[DOMAIN].domain);
var daa = ee.FeatureCollection(ASSETS[DOMAIN].daa);
var geom = domain.geometry();

var BANDS = ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B8A', 'B9', 'B11', 'B12'];
var USED = ['B2', 'B3', 'B4', 'B6', 'B7', 'B8', 'B11', 'B12'];      // bands of the main analysis
var s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(geom)
  .filterDate('2024-04-28', '2024-05-12').map(function(img) {
    var qa = img.select('QA60');
    var clear = qa.bitwiseAnd(1 << 10).eq(0).and(qa.bitwiseAnd(1 << 11).eq(0));
    return img.select(BANDS).updateMask(clear).divide(10000);
  }).median();
var valid = s2.select(USED).mask().reduce(ee.Reducer.min()).gt(0).unmask(0);   // same population as script 01
var b = function(name) { return s2.select(name); };

var tcwCrist = s2.expression('0.0315*B2 + 0.2021*B3 + 0.3102*B4 + 0.1594*B8 - 0.6806*B11 - 0.6109*B12',
  {B2: b('B2'), B3: b('B3'), B4: b('B4'), B8: b('B8'), B11: b('B11'), B12: b('B12')}).rename('TCW_CRIST');
var tcwS2 = s2.expression(
  '0.1825*B1 + 0.1763*B2 + 0.1615*B3 + 0.0486*B4 + 0.0170*B5 + 0.0223*B6 + 0.0219*B7' +
  ' - 0.0755*B8 - 0.0910*B8A - 0.1369*B9 - 0.7701*B11 - 0.5293*B12',
  {B1: b('B1'), B2: b('B2'), B3: b('B3'), B4: b('B4'), B5: b('B5'), B6: b('B6'), B7: b('B7'),
   B8: b('B8'), B8A: b('B8A'), B9: b('B9'), B11: b('B11'), B12: b('B12')}).rename('TCW_S2');
var masks = b('B11').lt(0.12).and(b('B6').lt(0.20)).and(b('B7').lt(0.20)).and(b('B8').lt(0.20)).unmask(0);
var ref = ee.Image(0).byte().paint(daa, 1);
var group = ref.multiply(2).add(masks).rename('grupo');      // as in script 01

// (1) histograms
var MIN = -1, MAX = 0.5, BINS = 1500;                        // bin width 0.001
var width = (MAX - MIN) / BINS;
var tables = [{name: 'TCW_CRIST', img: tcwCrist}, {name: 'TCW_S2', img: tcwS2}].map(function(h) {
  var img = h.img.clamp(MIN, MAX - width / 2).addBands(group).updateMask(valid);
  return img.reduceRegions({collection: domain,
    reducer: ee.Reducer.fixedHistogram(MIN, MAX, BINS).group({groupField: 1, groupName: 'grupo'}),
    scale: SCALE, crs: CRS, tileScale: TILE_SCALE})
    .map(function(f) { return ee.Feature(null, {NM_MUN: f.get('NM_MUN'), indice: h.name, groups: f.get('groups')}); });
});
Export.table.toDrive({collection: ee.FeatureCollection(tables).flatten(),
                      description: DOMAIN + '_v7_TCW_histogramas', folder: FOLDER, fileFormat: 'GeoJSON'});

// (2) original training sample (ROI-1)
if (DOMAIN === 'ROI1') {
  var training = s2.normalizedDifference(['B3', 'B8']).rename('NDWI').addBands(tcwCrist)
    .addBands(ref.rename('class'))
    .sample({region: geom, scale: 30, numPixels: 5000, seed: 42, geometries: false});
  var summary = ee.FeatureCollection([ee.Feature(null, {
    n_validos: training.size(),
    n_inundados: training.filter(ee.Filter.eq('class', 1)).size(),
    n_secos: training.filter(ee.Filter.eq('class', 0)).size()
  })]);
  print('Training sample', summary);
  Export.table.toDrive({collection: summary, description: 'ROI1_v7_contagem_treino', folder: FOLDER, fileFormat: 'CSV'});
}
