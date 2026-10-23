import React, { useMemo } from "react";
import * as THREE from "three";

/** Small stylised geostationary satellite (body + two solar wings). */
export const Satellite: React.FC<{ readonly position: THREE.Vector3; readonly frame: number }> = ({ position, frame }) => {
  const quat = useMemo(
    () => new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 0, 1), position.clone().normalize().negate()),
    [position],
  );
  return (
    <group position={position} quaternion={quat}>
      <mesh>
        <boxGeometry args={[0.05, 0.05, 0.07]} />
        <meshStandardMaterial color="#e0b43a" metalness={0.6} roughness={0.35} emissive="#7a5500" />
      </mesh>
      {[-1, 1].map((s) => (
        <mesh key={s} position={[s * 0.13, 0, 0]}>
          <boxGeometry args={[0.18, 0.06, 0.004]} />
          <meshStandardMaterial color="#3d6fb8" metalness={0.4} roughness={0.35} emissive="#1b3d75" />
        </mesh>
      ))}
      <mesh position={[0, 0, 0.05]}>
        <coneGeometry args={[0.03, 0.03, 16]} />
        <meshStandardMaterial color="#e8e8e8" />
      </mesh>
      <mesh position={[0, 0.035, 0]}>
        <sphereGeometry args={[0.01, 8, 8]} />
        <meshBasicMaterial color={frame % 20 < 4 ? "#ffffff" : "#553300"} toneMapped={false} />
      </mesh>
    </group>
  );
};

const shellVertex = /* glsl */ `
varying vec3 vN;
varying vec3 vV;
void main() {
  vec4 wp = modelMatrix * vec4(position, 1.0);
  vN = normalize(mat3(modelMatrix) * normal);
  vV = normalize(cameraPosition - wp.xyz);
  gl_Position = projectionMatrix * viewMatrix * wp;
}`;
const shellFragment = /* glsl */ `
uniform vec3 color;
uniform float opacity;
varying vec3 vN;
varying vec3 vV;
void main() {
  float f = pow(1.0 - abs(dot(normalize(vN), normalize(vV))), 2.2);
  gl_FragColor = vec4(color, (0.04 + f * 0.9) * opacity);
}`;

/** Translucent range sphere centred on the satellite. */
export const RangeShell: React.FC<{
  readonly center: THREE.Vector3;
  readonly radius: number;
  readonly opacity: number;
  readonly color: string;
}> = ({ center, radius, opacity, color }) => {
  const mat = useMemo(
    () =>
      new THREE.ShaderMaterial({
        vertexShader: shellVertex,
        fragmentShader: shellFragment,
        uniforms: { color: { value: new THREE.Color(color) }, opacity: { value: 1 } },
        transparent: true,
        depthWrite: false,
        side: THREE.DoubleSide,
        blending: THREE.AdditiveBlending,
      }),
    [color],
  );
  mat.uniforms.opacity.value = opacity;
  if (radius <= 0.001 || opacity <= 0) return null;
  return (
    <mesh position={center} scale={radius} material={mat}>
      <sphereGeometry args={[1, 96, 96]} />
    </mesh>
  );
};
