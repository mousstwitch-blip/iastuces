import React, { useMemo } from "react";
import * as THREE from "three";

const vertex = /* glsl */ `
varying vec3 vPos;
void main() {
  vec4 wp = modelMatrix * vec4(position, 1.0);
  vPos = wp.xyz;
  gl_Position = projectionMatrix * viewMatrix * wp;
}`;

const fragment = /* glsl */ `
uniform float time;
uniform vec3 moonDir;
uniform vec3 tint;
varying vec3 vPos;
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p) {
  vec2 i = floor(p); vec2 f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}
float fbm(vec2 p) {
  float v = 0.0; float a = 0.5;
  for (int i = 0; i < 6; i++) { v += a * noise(p); p = p * 2.03 + vec2(1.7, 9.2); a *= 0.5; }
  return v;
}
void main() {
  vec2 p = vPos.xz * 0.16 + vec2(time, 0.0);
  float d = smoothstep(0.38, 0.78, fbm(p));
  float d2 = smoothstep(0.38, 0.78, fbm(p + moonDir.xz * 0.06));
  float light = clamp(0.55 + (d - d2) * 4.0, 0.0, 1.0);
  vec3 col = mix(vec3(0.015, 0.03, 0.06), tint, light) * (0.35 + 0.65 * d);
  float dist = length(vPos.xz - cameraPosition.xz);
  float fog = smoothstep(14.0, 70.0, dist);
  col = mix(col, vec3(0.05, 0.09, 0.15), fog);
  float alpha = mix(0.25 + 0.75 * d, 0.0, smoothstep(40.0, 80.0, dist));
  gl_FragColor = vec4(col, alpha);
  #include <colorspace_fragment>
}`;

/** A moonlit layer of stratocumulus, scrolled by `time` (frame-driven). */
export const CloudSea: React.FC<{ readonly time: number; readonly y?: number }> = ({ time, y = -2.6 }) => {
  const mat = useMemo(
    () =>
      new THREE.ShaderMaterial({
        vertexShader: vertex,
        fragmentShader: fragment,
        transparent: true,
        depthWrite: false,
        uniforms: {
          time: { value: 0 },
          moonDir: { value: new THREE.Vector3(0.6, 0.5, -0.6).normalize() },
          tint: { value: new THREE.Color("#8fa6c4") },
        },
      }),
    [],
  );
  mat.uniforms.time.value = time;
  return (
    <mesh material={mat} position={[0, y, 0]} rotation={[-Math.PI / 2, 0, 0]}>
      <planeGeometry args={[220, 220, 1, 1]} />
    </mesh>
  );
};
