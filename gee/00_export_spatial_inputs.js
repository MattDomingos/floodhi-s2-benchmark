/**
 * 00 - Export the spatial inputs (study domains and DAA) for the repository
 * -----------------------------------------------------------------------------
 * Paper: "Assessing the added value of spectral-index fusion for Sentinel-2
 *         flood mapping: A reproducible wall-to-wall evaluation of the 2024
 *         Rio Grande do Sul State floods"
 *
 * Scripts 01-06 read four table assets: the municipality polygons of each
 * domain (field NM_MUN) and the DAA clipped to each municipality. This script
 * exports those assets unchanged to Google Drive as GeoJSON, the files kept in
 * data/spatial/. The shapefiles in data/spatial/ are written from these GeoJSON
 * files by tools/spatial_shapefiles.py.
 *
 * Why not export shapefiles here: clipping the DAA to the municipal boundaries
 * left most DAA features as geometry collections (polygons plus line and point
 * fragments along the boundaries). A shapefile holds a single geometry type, so
 * Earth Engine either refuses the export or drops those features entirely.
 *
 * The Console reports, for each layer, the number of features of each geometry
 * type and how many 10 m pixels the line and point features would add to the
 * reference painted by scripts 01-06 (ee.Image.paint without a line width).
 *
 * Usage: replace the four asset paths with the ones used in the paper runs,
 * click Run, check the Console, then start the four tasks in the Tasks tab.
 * Download the files from the Drive folder FLOODHI_spatial into data/spatial/.
 */

var ASSETS = {
  ROI1_municipalities: 'projects/YOUR_PROJECT/assets/ROI1_municipalities',
  ROI1_DAA:            'projects/YOUR_PROJECT/assets/ROI1_DAA',
  ROI2_municipalities: 'projects/YOUR_PROJECT/assets/ROI2_municipalities',
  ROI2_DAA:            'projects/YOUR_PROJECT/assets/ROI2_DAA'
};
var FOLDER = 'FLOODHI_spatial';
var CRS = 'EPSG:32722';
var LINES_POINTS = ['LineString', 'MultiLineString', 'Point', 'MultiPoint'];

Object.keys(ASSETS).forEach(function(name) {
  var asset = ee.FeatureCollection(ASSETS[name]);
  var typed = asset.map(function(f) { return f.set('geom_type', f.geometry().type()); });
  var lines = typed.filter(ee.Filter.inList('geom_type', LINES_POINTS));
  var extraPixels = ee.Algorithms.If(lines.size().gt(0),
    ee.Image(0).byte().paint(lines, 1).reduceRegion({
      reducer: ee.Reducer.sum(), geometry: lines.geometry(1).bounds(1),
      scale: 10, crs: CRS, maxPixels: 1e10}).values().get(0),
    0);
  print(name, 'features by geometry type:', typed.aggregate_histogram('geom_type'),
        '10 m pixels painted by line or point features (should be 0):', extraPixels);
  Map.addLayer(asset, {color: name.indexOf('DAA') >= 0 ? '1f78b4' : '999999'}, name);
  Export.table.toDrive({collection: asset, description: name + '_geojson',
                        folder: FOLDER, fileNamePrefix: name, fileFormat: 'GeoJSON'});
});
Map.centerObject(ee.FeatureCollection(ASSETS.ROI2_municipalities), 8);
