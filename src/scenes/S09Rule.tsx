import React, { useMemo } from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import * as THREE from "three";
import { Headline, Kicker, Reveal } from "../components/Type";
import { easeInOut, ramp } from "../lib/anim";
import { GlobeStage, SurfaceMarker, type CameraShot } from "../three/Globe";
import { greatCircle, ll } from "../three/geo";
import { cues } from "../timeline";
import { C, display, mono } from "../theme";

// Illustrative long-haul routes over the Indian Ocean (not real traffic).
const ROUTES: [[number, number], [number, number]][] = [
  [[-31.95, 115.86], [-26.2, 28.04]],
  [[-31.95, 115.86], [25.25, 55.36]],
  [[1.35, 103.99], [-20.43, 57.68]],
  [[19.09, 72.87], [-20.43, 57.68]],
  [[-33.9, 151.2], [-26.2, 28.04]],
  [[1.35, 103.99], [-26.2, 28.04]],
  [[2.74, 101.71], [21.68, 39.15]],
  [[7.18, 79.88], [-31.95, 115.86]],
  [[25.27, 51.6], [-31.95, 115.86]],
  [[13.0, 80.2], [2.74, 101.71]],
  [[-37.0, 174.8], [-26.2, 28.04]],
  [[1.35, 103.99], [25.25, 55.36]],
];

const SUN = { lat: 16, lon: 106 };

/** 0:45 — since 2018, airliners over oceans report their position at least every 15 min. */
export const S09Rule: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const [c0, c1] = cues("rule");
  const t = ramp(frame, [0, durationInFrames], [0, 1], easeInOut);
  const shot: CameraShot = {
    lat: -6 - 6 * t,
    lon: 70 + 14 * t,
    dist: 4.9 - 0.6 * t,
    look: ll(-14, 78, 0.3).toArray() as [number, number, number],
    fov: 34,
  };
  const planes = useMemo(() => {
    const out: { path: THREE.Vector3[]; phase: number; speed: number; pulseOffset: number }[] = [];
    ROUTES.forEach((r, i) => {
      const path = greatCircle(r[0], r[1], 200, 0, 1);
      for (let k = 0; k < 3; k++) out.push({ path, phase: (k * 0.31 + i * 0.137) % 1, speed: 0.0009 + (i % 3) * 0.0002, pulseOffset: (i * 7 + k * 13) % 45 });
    });
    return out;
  }, []);
  const show = ramp(frame, [4, 30], [0, 1]);
  const cycle = 45;
  const ringP = (frame % cycle) / cycle;

  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <GlobeStage shot={shot} sun={SUN} nightGain={0.5} exposure={1.05}>
        {planes.map((p, i) => {
          const u = (p.phase + frame * p.speed) % 1;
          const v = p.path[Math.floor(u * (p.path.length - 1))];
          const lat = (Math.asin(v.y / v.length()) * 180) / Math.PI;
          const lon = (Math.atan2(-v.z, v.x) * 180) / Math.PI;
          const pulse = ((frame + p.pulseOffset) % cycle) / cycle;
          return <SurfaceMarker key={i} lat={lat} lon={lon} color={C.amber} size={0.007} pulse={pulse} opacity={show} />;
        })}
      </GlobeStage>

      <AbsoluteFill style={{ padding: "236px 80px 0 80px" }}>
        <Reveal at={0}>
          <Kicker color={C.amber}>Depuis novembre 2018 · norme OACI</Kicker>
        </Reveal>
        <Reveal at={c0.at + 6}>
          <Headline size={100} style={{ marginTop: 14 }}>
            Au-dessus des océans,
          </Headline>
        </Reveal>
        <Reveal at={c1.at + 4}>
          <Headline size={100} color={C.amber}>
            une position
            <br />
            au moins toutes les
          </Headline>
        </Reveal>
      </AbsoluteFill>

      <Reveal at={c1.at + 30} style={{ position: "absolute", left: 80, top: 860, display: "flex", alignItems: "center", gap: 28 }}>
        <svg width="150" height="150">
          <circle cx="75" cy="75" r="62" fill="none" stroke="rgba(255,181,71,0.25)" strokeWidth="10" />
          <circle
            cx="75"
            cy="75"
            r="62"
            fill="none"
            stroke={C.amber}
            strokeWidth="10"
            strokeDasharray={`${ringP * 389.6} 389.6`}
            transform="rotate(-90 75 75)"
            strokeLinecap="round"
          />
        </svg>
        <div>
          <div style={{ fontFamily: display, fontWeight: 900, fontSize: 132, lineHeight: 0.9, color: C.paper, letterSpacing: "-0.04em" }}>15 min</div>
          <div style={{ fontFamily: mono, fontSize: 24, color: C.steel, letterSpacing: "0.12em", marginTop: 8 }}>AVIONS DE LIGNE · ZONES OCÉANIQUES</div>
        </div>
      </Reveal>
      <div style={{ position: "absolute", right: 150, top: 1218, fontFamily: mono, fontSize: 19, color: C.steelDim, letterSpacing: "0.12em" }}>
        ROUTES ILLUSTRATIVES
      </div>
    </AbsoluteFill>
  );
};
