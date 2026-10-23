import { useThree } from "@react-three/fiber";
import { ThreeCanvas } from "@remotion/three";
import React, { useLayoutEffect } from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import * as THREE from "three";
import { Headline, Kicker, Reveal } from "../components/Type";
import { easeInOut, ramp, rand } from "../lib/anim";
import { Airliner } from "../three/Airliner";
import { CloudSea } from "../three/CloudSea";
import { cues } from "../timeline";
import { C, mono } from "../theme";

type Cam = { pos: [number, number, number]; look: [number, number, number] };

const camAt = (t: number): Cam => ({
  pos: [9.5 - 4.5 * t, 2.8 - 0.6 * t, 16.5 + 1.5 * t],
  look: [0, -0.35, 0],
});

const Rig: React.FC<{ readonly cam: Cam }> = ({ cam }) => {
  const camera = useThree((s) => s.camera) as THREE.PerspectiveCamera;
  useLayoutEffect(() => {
    camera.position.set(...cam.pos);
    camera.lookAt(new THREE.Vector3(...cam.look));
    camera.fov = 38;
    camera.updateProjectionMatrix();
  });
  return null;
};

const probe = new THREE.PerspectiveCamera(38, 1080 / 1920, 0.1, 500);
const toScreen = (cam: Cam, v: THREE.Vector3) => {
  probe.position.set(...cam.pos);
  probe.lookAt(new THREE.Vector3(...cam.look));
  probe.updateMatrixWorld();
  const p = v.clone().project(probe);
  return { x: ((p.x + 1) / 2) * 1080, y: ((1 - p.y) / 2) * 1920 };
};

const Ring: React.FC<{ cx: number; cy: number; r: number; color: string; o: number; w?: number }> = ({ cx, cy, r, color, o, w = 4 }) => (
  <circle cx={cx} cy={cy} r={Math.max(0, r)} fill="none" stroke={color} strokeWidth={w} opacity={Math.max(0, o)} />
);

/** 0:10 — how a secondary radar "sees": it asks, the transponder answers. */
export const S03Transponder: React.FC = () => {
  const frame = useCurrentFrame();
  const { width, height, durationInFrames } = useVideoConfig();
  const [c0, c1, c2] = cues("transponder");
  const cam = camAt(ramp(frame, [0, durationInFrames], [0, 1], easeInOut));
  const plane = toScreen(cam, new THREE.Vector3(0, 0, 0));
  const ground = { x: 250, y: 2080 };

  // interrogation pulses travel from the ground station to the aircraft
  const qStarts = [c1.at - 6, c1.at + 8, c1.at + 22];
  // replies leave the aircraft
  const aStarts = [c2.at + 10, c2.at + 22, c2.at + 34];
  const reach = Math.hypot(plane.x - ground.x, plane.y - ground.y);

  return (
    <AbsoluteFill
      style={{
        background:
          "radial-gradient(circle at 78% 18%, rgba(190,210,235,0.35) 0, rgba(120,150,190,0.12) 120px, rgba(10,20,36,0) 420px), linear-gradient(180deg, #02050b 0%, #071225 48%, #0d1d33 70%, #0a1626 100%)",
      }}
    >
      <svg width="1080" height="1920" style={{ position: "absolute", inset: 0 }}>
        {Array.from({ length: 140 }, (_, i) => (
          <circle key={i} cx={rand(i) * 1080} cy={rand(i + 500) * 900} r={rand(i + 900) * 1.6 + 0.3} fill="#dfe8ff" opacity={0.25 + rand(i + 77) * 0.6} />
        ))}
        <circle cx={842} cy={346} r={34} fill="#e8eef7" opacity={0.92} />
      </svg>
      <ThreeCanvas width={width} height={height} gl={{ antialias: true, alpha: true }} camera={{ fov: 38, position: [0, 0, 8] }}>
        <Rig cam={cam} />
        <ambientLight intensity={0.22} color="#6b7f9e" />
        <hemisphereLight args={["#8fb0ff", "#0a0f18", 0.55]} />
        <directionalLight position={[6, 7, -6]} intensity={2.6} color="#cfdcff" />
        <directionalLight position={[-6, 2, 6]} intensity={0.55} color="#ffb98a" />
        <group position={[0, 0.03 * Math.sin(frame / 18), 0]} rotation={[0.02 * Math.sin(frame / 25), 0, 0.015 * Math.sin(frame / 31)]}>
          <Airliner frame={frame} />
        </group>
        <CloudSea time={frame * 0.012} />
      </ThreeCanvas>

      <svg width="1080" height="1920" style={{ position: "absolute", inset: 0 }}>
        {qStarts.map((s, i) => {
          const p = (frame - s) / 26;
          if (p <= 0 || p > 1.1) return null;
          return <Ring key={`q${i}`} cx={ground.x} cy={ground.y} r={p * reach} color={C.paper} o={0.85 * (1 - p * 0.6)} w={5} />;
        })}
        {aStarts.map((s, i) => {
          const p = (frame - s) / 30;
          if (p <= 0 || p > 1) return null;
          return <Ring key={`a${i}`} cx={plane.x} cy={plane.y} r={60 + p * 900} color={C.amber} o={1 - p} w={6} />;
        })}
      </svg>

      <Reveal at={c1.at} out={c2.at + 8} style={{ position: "absolute", left: 80, top: 1520 }}>
        <Kicker color={C.paper} size={28}>
          ▲ Question · 1030 MHz
        </Kicker>
      </Reveal>
      <Reveal at={c2.at + 10} style={{ position: "absolute", left: plane.x - 300, top: plane.y - 190, width: 600, textAlign: "center" }}>
        <div style={{ fontFamily: mono, fontSize: 30, fontWeight: 700, color: C.amber, letterSpacing: "0.08em", textShadow: "0 2px 12px #000" }}>
          MAS370 · FL350
        </div>
        <Kicker color={C.amber} size={24} style={{ marginTop: 6 }}>
          ▼ Réponse · 1090 MHz
        </Kicker>
      </Reveal>

      <AbsoluteFill style={{ padding: "236px 80px 0 80px" }}>
        <Reveal at={c0.at}>
          <Kicker>Radar secondaire</Kicker>
        </Reveal>
        <Reveal at={c1.at}>
          <Headline size={104} style={{ marginTop: 14 }}>
            Le radar demande.
          </Headline>
        </Reveal>
        <Reveal at={c2.at + 4}>
          <Headline size={104} color={C.amber}>
            L’avion répond.
          </Headline>
        </Reveal>
        <Reveal at={c2.at + 20} style={{ marginTop: 18 }}>
          <Kicker color={C.steel} size={26}>
            Grâce à son transpondeur
          </Kicker>
        </Reveal>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
