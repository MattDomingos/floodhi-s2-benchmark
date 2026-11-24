/**
 * 06 - Terrain screen of the DAA (Table S9)
 * -----------------------------------------------------------------------------
 * The DAA layer has no attribute that separates floods from mass movements,
 * so this script screens it by terrain. Each valid pixel is classified by
 *   slope (Copernicus GLO-30): 0 <5, 1 5-10, 2 10-15, 3 15-20, 4 >=20 degrees
 *   height above the nearest drainage (MERIT Hydro HAND):
 *                              0 <5, 1 5-10, 2 10-20, 3 20-30, 4 >=30 m
 * (classe = 5 * slope class + HAND class), and the script sums, per
 * municipality and class, valid pixels, DAA pixels and the correct detections
 * (tp) and omissions (fn) of FLOOD-HI + masks at the zero threshold.
 */

var DOMAIN = 'ROI1';
var ASSETS = {
  ROI1: {domain: 'projects/YOUR_PROJECT/assets/ROI1_municipalities', daa: 'projects/YOUR_PROJECT/assets/ROI1_DAA'},
  ROI2: {domain: 'projects/YOUR_PROJECT/assets/ROI2_municipalities', daa: 'projects/YOUR_PROJECT/assets/ROI2_DAA'}
};
var CRS = 'EPSG:32722', SCALE = 10, FOLDER = 'FLOODHI_exports', TILE_SCALE = 8;

var domain = ee.FeatureCollection(ASSETS[DOMAIN].domain);
var daa = ee.FeatureCollection(ASSETS[DOMAIN].daa);
var geom = domain.geometry();
var proj10 = ee.Projection(CRS).atScale(SCALE);

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
var masks = b('B11').lt(0.12).and(b('B6').lt(0.20)).and(b('B7').lt(0.20)).and(b('B8').lt(0.20));
var pred = floodhi.gt(0).and(masks).unmask(0);
var ref = ee.Image(0).byte().paint(daa, 1);

// Terrain
var dem = ee.ImageCollection('COPERNICUS/DEM/GLO30').select('DEM').filterBounds(geom).mosaic()
  .setDefaultProjection('EPSG:4326', null, 30);
var slope = ee.Terrain.slope(dem);
var hand = ee.Image('MERIT/Hydro/v1_0_1').select('hnd');
var slopeClass = ee.Image(0).where(slope.gte(5), 1).where(slope.gte(10), 2).where(slope.gte(15), 3).where(slope.gte(20), 4);
var handClass = ee.Image(0).where(hand.gte(5), 1).where(hand.gte(10), 2).where(hand.gte(20), 3).where(hand.gte(30), 4);
var terrainClass = slopeClass.multiply(5).add(handClass).rename('classe');

var img = ee.Image.cat([valid.rename('n_valido'), ref.and(valid).rename('n_daa'),
                        ref.and(pred).and(valid).rename('tp'), ref.and(pred.not()).and(valid).rename('fn'),
                        terrainClass]).reproject(proj10);
var table = img.reduceRegions({collection: domain,
  reducer: ee.Reducer.sum().repeat(4).group({groupField: 4, groupName: 'classe'}),
  scale: SCALE, crs: CRS, tileScale: TILE_SCALE
}).map(function(f) {
  return ee.Feature(null, {NM_MUN: f.get('NM_MUN'), bandas: 'n_valido,n_daa,tp,fn', groups: f.get('groups')});
});
Export.table.toDrive({collection: table, description: DOMAIN + '_v8_relevo_daa', folder: FOLDER, fileFormat: 'GeoJSON'});

Map.centerObject(domain, 10);
Map.addLayer(ref.selfMask().clip(geom), {palette: ['3182bd']}, 'DAA');
Map.addLayer(ref.and(slope.gte(15)).and(hand.gte(20)).selfMask().clip(geom), {palette: ['e31a1c']},
             'DAA on slopes >= 15 deg and HAND >= 20 m');
