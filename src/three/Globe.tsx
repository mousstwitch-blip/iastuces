import { useThree } from "@react-three/fiber";
import { ThreeCanvas } from "@remotion/three";
import React, { useLayoutEffect, useMemo } from "react";
import { useVideoConfig } from "remotion";
import * as THREE from "three";
import { ll, seeded } from "./geo";
import { useTexture } from "./useTexture";

const earthVertex = /* glsl */ `
varying vec2 vUv;
varying vec3 vNormalW;
varying vec3 vPosW;
void main() {
  vUv = uv;
  vNormalW = normalize(mat3(modelMatrix) * normal);
  vec4 wp = modelMatrix * vec4(position, 1.0);
  vPosW = wp.xyz;
  gl_Position = projectionMatrix * viewMatrix * wp;
}`;

const earthFragment = /* glsl */ `
uniform sampler2D dayTex;
uniform sampler2D nightTex;
uniform vec3 sunDir;
uniform float nightGain;
uniform float exposure;
varying vec2 vUv;
varying vec3 vNormalW;
varying vec3 vPosW;
void main() {
  vec3 n = normalize(vNormalW);
  vec3 v = normalize(cameraPosition - vPosW);
  float ndl = dot(n, sunDir);
  float dayMix = smoothstep(-0.06, 0.16, ndl);
  vec3 day = texture2D(dayTex, vUv).rgb;
  vec3 night = texture2D(nightTex, vUv).rgb;
  vec3 lit = day * (max(ndl, 0.0) * 1.25 + 0.015);
  vec3 lights = pow(night, vec3(1.9)) * vec3(1.6, 1.15, 0.7) * 5.0 * nightGain;
  vec3 col = mix(lights + day * 0.012, lit, dayMix);
  float fres = pow(1.0 - max(dot(n, v), 0.0), 3.0);
  col += vec3(0.30, 0.55, 1.0) * fres * (0.10 + 0.9 * dayMix);
  gl_FragColor = vec4(col * exposure, 1.0);
  #include <colorspace_fragment>
}`;

const atmoVertex = /* glsl */ `
varying vec3 vNormal;
varying vec3 vNormalW;
void main() {
  vNormal = normalize(normalMatrix * normal);
  vNormalW = normalize(mat3(modelMatrix) * normal);
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}`;

const atmoFragment = /* glsl */ `
uniform vec3 sunDir;
varying vec3 vNormal;
varying vec3 vNormalW;
void main() {
  float i = pow(max(0.0, 0.72 - dot(vNormal, vec3(0.0, 0.0, 1.0))), 3.5);
  float sun = smoothstep(-0.45, 0.4, dot(vNormalW, sunDir));
  vec3 c = mix(vec3(0.05, 0.12, 0.35), vec3(0.32, 0.62, 1.0), sun);
  gl_FragColor = vec4(c * i * 1.6, 1.0);
}`;

export type SunPos = { lat: number; lon: number };

const Earth: React.FC<{
  readonly day: THREE.Texture;
  readonly night: THREE.Texture;
  readonly sun: SunPos;
  readonly nightGain: number;
  readonly exposure: number;
}> = ({ day, night, sun, nightGain, exposure }) => {
  const sunDir = useMemo(() => ll(sun.lat, sun.lon).normalize(), [sun.lat, sun.lon]);
  const earthMat = useMemo(
    () =>
      new THREE.ShaderMaterial({
        vertexShader: earthVertex,
        fragmentShader: earthFragment,
        uniforms: {
          dayTex: { value: day },
          nightTex: { value: night },
          sunDir: { value: sunDir },
          nightGain: { value: nightGain },
          exposure: { value: exposure },
        },
      }),
    [day, night, sunDir, nightGain, exposure],
  );
  const atmoMat = useMemo(
    () =>
      new THREE.ShaderMaterial({
        vertexShader: atmoVertex,
        fragmentShader: atmoFragment,
        uniforms: { sunDir: { value: sunDir } },
        side: THREE.BackSide,
        blending: THREE.AdditiveBlending,
        transparent: true,
        depthWrite: false,
      }),
    [sunDir],
  );
  return (
    <>
      <mesh material={earthMat}>
        <sphereGeometry args={[1, 160, 160]} />
      </mesh>
      <mesh material={atmoMat} scale={1.11}>
        <sphereGeometry args={[1, 96, 96]} />
      </mesh>
    </>
  );
};

const Stars: React.FC = () => {
  const geom = useMemo(() => {
    const rnd = seeded(7);
    const n = 2600;
    const pos = new Float32Array(n * 3);
    const col = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      const u = rnd() * 2 - 1;
      const t = rnd() * Math.PI * 2;
      const s = Math.sqrt(1 - u * u);
      pos.set([s * Math.cos(t) * 90, u * 90, s * Math.sin(t) * 90], i * 3);
      const b = 0.25 + Math.pow(rnd(), 3) * 0.95;
      const warm = rnd();
      col.set([b * (0.85 + warm * 0.15), b * 0.92, b * (1.05 - warm * 0.2)], i * 3);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    g.setAttribute("color", new THREE.BufferAttribute(col, 3));
    return g;
  }, []);
  return (
    <points geometry={geom}>
      <pointsMaterial size={2.2} sizeAttenuation={false} vertexColors transparent depthWrite={false} />
    </points>
  );
};

export type CameraShot = {
  /** Camera position as lat/lon/distance from the Earth's centre. */
  readonly lat: number;
  readonly lon: number;
  readonly dist: number;
  /** Point the camera looks at (defaults to the Earth's centre). */
  readonly look?: [number, number, number];
  readonly fov?: number;
  readonly roll?: number;
};

const applyShot = (camera: THREE.PerspectiveCamera, shot: CameraShot) => {
  camera.position.copy(ll(shot.lat, shot.lon, shot.dist));
  camera.up.set(Math.sin(shot.roll ?? 0), Math.cos(shot.roll ?? 0), 0);
  camera.lookAt(new THREE.Vector3(...(shot.look ?? [0, 0, 0])));
  camera.fov = shot.fov ?? 32;
  camera.near = 0.01;
  camera.far = 200;
  camera.updateProjectionMatrix();
  camera.updateMatrixWorld();
};

const CameraRig: React.FC<{ readonly shot: CameraShot }> = ({ shot }) => {
  const camera = useThree((s) => s.camera) as THREE.PerspectiveCamera;
  useLayoutEffect(() => {
    applyShot(camera, shot);
  });
  return null;
};

const probe = new THREE.PerspectiveCamera(32, 1080 / 1920, 0.01, 200);

/** Screen position (px) of a world point for a given shot, and whether it faces the camera. */
export const screenOf = (shot: CameraShot, v: THREE.Vector3, width = 1080, height = 1920) => {
  probe.aspect = width / height;
  applyShot(probe, shot);
  const p = v.clone().project(probe);
  const toCam = probe.position.clone().sub(v);
  const visible = v.length() > 1.05 || v.clone().normalize().dot(toCam.normalize()) > 0.05;
  return { x: ((p.x + 1) / 2) * width, y: ((1 - p.y) / 2) * height, visible };
};

/** A photoreal Earth (NASA Blue/Black Marble) with atmosphere and stars. */
export const GlobeStage: React.FC<{
  readonly shot: CameraShot;
  readonly sun: SunPos;
  readonly nightGain?: number;
  readonly exposure?: number;
  readonly children?: React.ReactNode;
}> = ({ shot, sun, nightGain = 1, exposure = 1, children }) => {
  const { width, height } = useVideoConfig();
  const day = useTexture("tex/earth-blue-marble.jpg");
  const night = useTexture("tex/earth-night.jpg");
  // Mount the canvas only once every texture is ready, so the very first WebGL
  // frame already contains the Earth (R3F does not redraw on late state changes).
  if (!day || !night) return null;
  return (
    <ThreeCanvas width={width} height={height} gl={{ antialias: true }} camera={{ fov: 32, position: [0, 0, 4] }}>
      <CameraRig shot={shot} />
      <Stars />
      <Earth day={day} night={night} sun={sun} nightGain={nightGain} exposure={exposure} />
      {children}
    </ThreeCanvas>
  );
};

/** A glowing tube along a list of points, drawn progressively from 0 to `progress`. */
export const GlowPath: React.FC<{
  readonly points: THREE.Vector3[];
  readonly progress: number;
  readonly color: string;
  readonly radius?: number;
  readonly opacity?: number;
}> = ({ points, progress, color, radius = 0.004, opacity = 1 }) => {
  const segs = points.length * 2;
  const radial = 8;
  const geom = useMemo(() => {
    const curve = new THREE.CatmullRomCurve3(points);
    return new THREE.TubeGeometry(curve, segs, radius, radial, false);
  }, [points, segs, radius]);
  const halo = useMemo(() => {
    const curve = new THREE.CatmullRomCurve3(points);
    return new THREE.TubeGeometry(curve, segs, radius * 2.6, radial, false);
  }, [points, segs, radius]);
  const count = Math.round(Math.max(0, Math.min(1, progress)) * segs) * radial * 6;
  geom.setDrawRange(0, count);
  halo.setDrawRange(0, count);
  return (
    <>
      <mesh geometry={geom}>
        <meshBasicMaterial color={color} transparent opacity={opacity} toneMapped={false} />
      </mesh>
      <mesh geometry={halo}>
        <meshBasicMaterial
          color={color}
          transparent
          opacity={0.22 * opacity}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          toneMapped={false}
        />
      </mesh>
    </>
  );
};

/** A dot on the surface with an optional expanding pulse ring. */
export const SurfaceMarker: React.FC<{
  readonly lat: number;
  readonly lon: number;
  readonly color: string;
  readonly size?: number;
  readonly pulse?: number; // 0..1, ring expansion
  readonly opacity?: number;
}> = ({ lat, lon, color, size = 0.012, pulse, opacity = 1 }) => {
  const pos = useMemo(() => ll(lat, lon, 1.004), [lat, lon]);
  const quat = useMemo(
    () => new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 0, 1), pos.clone().normalize()),
    [pos],
  );
  return (
    <group position={pos} quaternion={quat}>
      <mesh>
        <circleGeometry args={[size, 32]} />
        <meshBasicMaterial color={color} transparent opacity={opacity} toneMapped={false} />
      </mesh>
      <mesh>
        <circleGeometry args={[size * 2, 32]} />
        <meshBasicMaterial
          color={color}
          transparent
          opacity={0.18 * opacity}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          toneMapped={false}
        />
      </mesh>
      {pulse !== undefined && pulse > 0 && pulse < 1 ? (
        <mesh scale={1 + pulse * 2.6}>
          <ringGeometry args={[size * 1.5, size * 1.65, 48]} />
          <meshBasicMaterial color={color} transparent opacity={(1 - pulse) * opacity} toneMapped={false} />
        </mesh>
      ) : null}
    </group>
  );
};
