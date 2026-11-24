/**
 * 04 - Automatic example windows and agreement maps (Figs. 9, 10 and S3)
 * -----------------------------------------------------------------------------
 * Divides the domain into a regular grid (3 km cells in ROI-1, 5 km in ROI-2)
 * and, among cells at least 95% valid and 10% covered by the DAA, selects
 *   A the cell with most correct detections over open land cover,
 *   B the cell with most omissions under natural vegetation,
 *   C the cell with most omissions in urban areas.
 * For each window it prints a link to a PNG with three panels (true colour,
 * land cover, agreement of FLOOD-HI + masks with the DAA). It also exports
 * the cell statistics and 30 m maps of agreement and land cover.
 */

var DOMAIN = 'ROI1';
var ASSETS = {
  ROI1: {domain: 'projects/YOUR_PROJECT/assets/ROI1_municipalities', daa: 'projects/YOUR_PROJECT/assets/ROI1_DAA'},
  ROI2: {domain: 'projects/YOUR_PROJECT/assets/ROI2_municipalities', daa: 'projects/YOUR_PROJECT/assets/ROI2_DAA'}
};
var CELL = {ROI1: 3000, ROI2: 5000};     // window side (m)
var THRESHOLD = 0;                       // FLOOD-HI threshold (0 = sign rule)
var CRS = 'EPSG:32722', FOLDER = 'FLOODHI_exports', TILE_SCALE = 4;
var SELECTION_SCALE = 60;                // resolution used only to rank the cells
var MIN_VALID = 0.95, MIN_DAA = 0.10, PNG_WIDTH = 600;

var domain = ee.FeatureCollection(ASSETS[DOMAIN].domain);
var daa = ee.FeatureCollection(ASSETS[DOMAIN].daa);
var geom = domain.geometry();

var BANDS = ['B2', 'B3', 'B4', 'B6', 'B7', 'B8', 'B11', 'B12'];
var s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(geom)
  .filterDate('2024-04-28', '2024-05-12').map(function(img) {
    var qa = img.select('QA60');
    var clear = qa.bitwiseAnd(1 << 10).eq(0).and(qa.bitwiseAnd(1 << 11).eq(0));
    return img.select(BANDS).updateMask(clear).divide(10000);
  }).median();
var inside = ee.Image(0).byte().paint(domain, 1);
var valid = s2.mask().reduce(ee.Reducer.min()).gt(0).unmask(0).and(inside);
var b = function(name) { return s2.select(name); };
var ndwi = s2.normalizedDifference(['B3', 'B8']);
var imp = ndwi.add(s2.normalizedDifference(['B2', 'B8']));
var awei = s2.expression('B2 + 2.5*B3 - 1.5*(B8 + B11) - 0.25*B12', {B2: b('B2'), B3: b('B3'), B8: b('B8'), B11: b('B11'), B12: b('B12')});
var tcw = s2.expression('0.0315*B2 + 0.2021*B3 + 0.3102*B4 + 0.1594*B8 - 0.6806*B11 - 0.6109*B12',
  {B2: b('B2'), B3: b('B3'), B4: b('B4'), B8: b('B8'), B11: b('B11'), B12: b('B12')});
var ndvi = s2.normalizedDifference(['B8', 'B4']);
var savi = s2.expression('1.5*(B8 - B4)/(B8 + B4 + 0.5)', {B8: b('B8'), B4: b('B4')});
var floodhi = ndwi.multiply(3.72).add(imp.multiply(-2.67)).add(awei.multiply(2.69))
  .add(tcw.multiply(-1.77)).add(ndvi.multiply(-2.67)).add(savi.multiply(3.30));
var masks = b('B11').lt(0.12).and(b('B6').lt(0.20)).and(b('B7').lt(0.20)).and(b('B8').lt(0.20)).unmask(0);
var ref = ee.Image(0).byte().paint(daa, 1);
var pred = floodhi.gt(THRESHOLD).and(masks).unmask(0);
var agreementAll = pred.multiply(2).add(ref).rename('erro');      // 0 TN, 1 FN, 2 FP, 3 TP
var agreement = agreementAll.updateMask(valid);

var STRATA = {1: [24], 2: [33, 31, 26], 3: [14, 15, 18, 19, 39, 20, 62, 41, 36, 46, 47, 35, 48, 9, 21],
              4: [1, 3, 4, 5, 6, 49, 10, 11, 12, 32, 29, 50, 13], 6: [40]};
var from = [], to = [];
Object.keys(STRATA).forEach(function(k) { STRATA[k].forEach(function(c) { from.push(c); to.push(Number(k)); }); });
var landCover = ee.Image('projects/mapbiomas-public/assets/brazil/lulc/collection9/mapbiomas_collection90_integration_v1')
  .select('classification_2023').remap(from, to, 5).unmask(5).rename('uso');
var open = landCover.eq(2).or(landCover.eq(3)).or(landCover.eq(6));

var tp = agreementAll.eq(3).and(valid), fn = agreementAll.eq(1).and(valid), fp = agreementAll.eq(2).and(valid);
var daaValid = ref.and(valid);
var stack = ee.Image.cat([
  ee.Image(1).rename('n'), valid.rename('v'), daaValid.rename('daa'), tp.rename('tp'), fn.rename('fn'),
  fp.rename('fp'), daaValid.and(landCover.eq(4)).rename('daa_veg'), daaValid.and(landCover.eq(1)).rename('daa_urb'),
  daaValid.and(open).rename('daa_aberta'), tp.and(open).rename('tp_aberta'),
  fn.and(landCover.eq(4)).rename('fn_veg'), fn.and(landCover.eq(1)).rename('fn_urb')
]);
var cells = geom.coveringGrid(ee.Projection(CRS).atScale(CELL[DOMAIN]));
var stats = stack.reduceRegions({collection: cells, reducer: ee.Reducer.sum(), scale: SELECTION_SCALE,
                                 crs: CRS, tileScale: TILE_SCALE}).map(function(f) {
  var den = ee.Number(f.get('daa')).max(1);
  var c = f.geometry().centroid(1);
  return f.set({
    frac_valida: ee.Number(f.get('v')).divide(f.get('n')),
    frac_daa: ee.Number(f.get('daa')).divide(ee.Number(f.get('v')).max(1)),
    recall: ee.Number(f.get('tp')).divide(den),
    precisao: ee.Number(f.get('tp')).divide(ee.Number(f.get('tp')).add(f.get('fp')).max(1)),
    frac_daa_veg: ee.Number(f.get('daa_veg')).divide(den),
    frac_daa_urb: ee.Number(f.get('daa_urb')).divide(den),
    frac_daa_aberta: ee.Number(f.get('daa_aberta')).divide(den),
    lon: c.coordinates().get(0), lat: c.coordinates().get(1),
    x_utm: c.transform(CRS, 1).coordinates().get(0), y_utm: c.transform(CRS, 1).coordinates().get(1)
  });
});
var eligible = stats.filter(ee.Filter.gte('frac_valida', MIN_VALID)).filter(ee.Filter.gte('frac_daa', MIN_DAA));
var selected = ee.Dictionary({A: eligible.sort('tp_aberta', false).first(),
                              B: eligible.sort('fn_veg', false).first(),
                              C: eligible.sort('fn_urb', false).first()});

var rgb = s2.visualize({bands: ['B4', 'B3', 'B2'], min: 0, max: 0.3, gamma: 1.4});
var landCoverVis = landCover.visualize({min: 1, max: 6, palette: ['e31a1c', '2171b5', 'fee08b', '41ab5d', 'bdbdbd', 'fdae6b']});
var agreementVis = agreement.updateMask(agreement.gt(0))
  .visualize({min: 1, max: 3, palette: ['e66101', 'c51b7d', '2166ac'], opacity: 0.8});  // FN, FP, TP
selected.evaluate(function(sel, error) {
  if (error) { print('Window selection failed:', error); return; }
  ['A', 'B', 'C'].forEach(function(k) {
    var region = ee.Geometry(sel[k].geometry);
    print('Window ' + k, sel[k].properties);
    ee.ImageCollection([rgb, landCoverVis, rgb.blend(agreementVis)]).getFilmstripThumbURL(
      {dimensions: PNG_WIDTH, region: region, crs: CRS, format: 'png'},
      function(url, e) { if (!e) print(ui.Label({value: 'Save as ' + DOMAIN + '_janela_' + k + '.png', targetUrl: url})); });
  });
});

Export.table.toDrive({collection: stats.map(function(f) { return ee.Feature(null, f.toDictionary()); }),
                      description: DOMAIN + '_v4_celulas', folder: FOLDER, fileFormat: 'CSV'});
// 30 m maps: modal agreement class (1 TN, 2 FN, 3 FP, 4 TP; 0 outside/invalid) and land cover
var agreement30 = agreement.add(1).toByte().reproject({crs: CRS, scale: 10})
  .reduceResolution({reducer: ee.Reducer.mode(), maxPixels: 64}).reproject({crs: CRS, scale: 30})
  .unmask(0).toByte().clip(geom);
Export.image.toDrive({image: agreement30, description: DOMAIN + '_v4_mapa_erros_30m', folder: FOLDER,
                      region: geom.bounds(), crs: CRS, scale: 30, maxPixels: 1e10});
Export.image.toDrive({image: landCover.updateMask(inside).unmask(0).toByte().clip(geom),
                      description: DOMAIN + '_v4_uso_solo_30m', folder: FOLDER,
                      region: geom.bounds(), crs: CRS, scale: 30, maxPixels: 1e10});
