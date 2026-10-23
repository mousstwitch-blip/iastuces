import * as THREE from "three";

const D2R = Math.PI / 180;

/**
 * Matches THREE.SphereGeometry's UV layout with an equirectangular texture whose
 * left edge is longitude -180°.
 */
export const ll = (lat: number, lon: number, r = 1) =>
  new THREE.Vector3(
    r * Math.cos(lat * D2R) * Math.cos(lon * D2R),
    r * Math.sin(lat * D2R),
    -r * Math.cos(lat * D2R) * Math.sin(lon * D2R),
  );

/** Great-circle points between two lat/lon pairs, optionally lifted into an arc. */
export const greatCircle = (a: [number, number], b: [number, number], n = 96, lift = 0, r = 1.002) => {
  const va = ll(a[0], a[1]).normalize();
  const vb = ll(b[0], b[1]).normalize();
  const omega = va.angleTo(vb);
  const pts: THREE.Vector3[] = [];
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    const s = Math.sin(omega);
    const v = va
      .clone()
      .multiplyScalar(Math.sin((1 - t) * omega) / s)
      .add(vb.clone().multiplyScalar(Math.sin(t * omega) / s));
    pts.push(v.normalize().multiplyScalar(r + lift * Math.sin(Math.PI * t)));
  }
  return pts;
};

/** Destination point given start, bearing (deg) and angular distance (deg). */
export const destination = (lat: number, lon: number, bearing: number, dist: number): [number, number] => {
  const p1 = lat * D2R;
  const l1 = lon * D2R;
  const b = bearing * D2R;
  const d = dist * D2R;
  const p2 = Math.asin(Math.sin(p1) * Math.cos(d) + Math.cos(p1) * Math.sin(d) * Math.cos(b));
  const l2 = l1 + Math.atan2(Math.sin(b) * Math.sin(d) * Math.cos(p1), Math.cos(d) - Math.sin(p1) * Math.sin(p2));
  return [p2 / D2R, l2 / D2R];
};

/** A small circle (e.g. a satellite range ring) between two bearings. */
export const smallCircle = (center: [number, number], radiusDeg: number, b0: number, b1: number, n = 160, r = 1.003) => {
  const pts: THREE.Vector3[] = [];
  for (let i = 0; i <= n; i++) {
    const [la, lo] = destination(center[0], center[1], b0 + ((b1 - b0) * i) / n, radiusDeg);
    pts.push(ll(la, lo, r));
  }
  return pts;
};

/** Seeded random generator (mulberry32). */
export const seeded = (seed: number) => {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
};
