// Extracts the Southeast Asia countries (Natural Earth 1:10m, public domain, via world-atlas)
// into a small GeoJSON used by the radar scope and the military-radar map.
import {readFileSync, writeFileSync} from 'node:fs';
import {feature} from 'topojson-client';
import {geoBounds} from 'd3-geo';

const topo = JSON.parse(readFileSync('node_modules/world-atlas/countries-10m.json', 'utf8'));
const all = feature(topo, topo.objects.countries).features;
const [W, S, E, N] = [90, -8, 112, 16];
const keep = all.filter((f) => {
  const [[x0, y0], [x1, y1]] = geoBounds(f);
  return x1 > W && x0 < E && y1 > S && y0 < N;
});
// round coordinates to keep the file small
const round = (c) => (typeof c[0] === 'number' ? [+c[0].toFixed(3), +c[1].toFixed(3)] : c.map(round));
const out = {
  type: 'FeatureCollection',
  features: keep.map((f) => ({type: 'Feature', properties: {name: f.properties.name}, geometry: {...f.geometry, coordinates: round(f.geometry.coordinates)}})),
};
writeFileSync('src/data/sea-region.json', JSON.stringify(out));
console.log(keep.map((f) => f.properties.name).join(', '));
