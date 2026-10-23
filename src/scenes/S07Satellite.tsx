import React, { useMemo } from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { GlobeLabel } from "../components/GlobeLabel";
import { Headline, Kicker, Reveal } from "../components/Type";
import { easeInOut, easeOut, ramp } from "../lib/anim";
import { GlobeStage, GlowPath, screenOf, type CameraShot } from "../three/Globe";
import { RangeShell, Satellite } from "../three/Satellite";
import { destination, ll, smallCircle } from "../three/geo";
import { cues } from "../timeline";
import { C } from "../theme";

export const SAT_SUBPOINT: [number, number] = [0, 64.5]; // Inmarsat-3 F1
export const ARC7_RADIUS = 43.9; // degrees of arc from the sub-satellite point
// Subsolar point at 00:19 UTC on 8 March 2014: dawn line over the eastern Indian Ocean.
export const SUN_0019 = { lat: -4.6, lon: 177.7 };
const SAT_R = 2.2; // schematic altitude (not to scale)
// Range sphere radius whose intersection with the globe is exactly the 7th arc.
const SHELL_R = Math.sqrt(SAT_R * SAT_R + 1 - 2 * SAT_R * Math.cos((ARC7_RADIUS * Math.PI) / 180));

/** 0:33 — satellite handshakes give a distance, i.e. a ring, not a point. */
export const S07Satellite: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const [, c1, c2] = cues("satellite");
  const t = ramp(frame, [0, durationInFrames], [0, 1], easeInOut);
  const shot: CameraShot = {
    lat: -6 - 8 * t,
    lon: 70 + 8 * t,
    dist: 5.6 - 0.7 * t,
    look: ll(-12, 78, 0.25 + 0.15 * t).toArray() as [number, number, number],
    fov: 34,
  };
  const sat = useMemo(() => ll(SAT_SUBPOINT[0], SAT_SUBPOINT[1], SAT_R), []);
  const ring = useMemo(() => smallCircle(SAT_SUBPOINT, ARC7_RADIUS, 0, 360, 240, 1.002), []);
  const south = useMemo(() => smallCircle(SAT_SUBPOINT, ARC7_RADIUS, 108, 162, 120, 1.004), []);

  const pings = [0, 14, 28].map((d) => (frame - (c1.at + d)) / 24);
  const ringP = ramp(frame, [c1.at + 40, c1.at + 70], [0, 1]);
  const arcP = ramp(frame, [c2.at, c2.at + 40], [0, 1], easeOut);
  const satS = screenOf(shot, sat);
  const [alat, alon] = destination(SAT_SUBPOINT[0], SAT_SUBPOINT[1], 128, ARC7_RADIUS);
  const arcS = screenOf(shot, ll(alat, alon));

  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <GlobeStage shot={shot} sun={SUN_0019} nightGain={0.9} exposure={1.05}>
        <Satellite position={sat} frame={frame} />
        {pings.map((p, i) => {
          const last = i === pings.length - 1;
          const opacity = p <= 0 ? 0 : p < 1 ? 1 - p * (last ? 0.5 : 0.75) : last ? 0.4 * (1 - arcP * 0.6) : 0;
          return <RangeShell key={i} center={sat} radius={Math.min(1, Math.max(0, p)) * SHELL_R} opacity={opacity} color={C.amber} />;
        })}
        <GlowPath points={ring} progress={ringP} color={C.steel} radius={0.0022} opacity={0.5 * (1 - arcP * 0.4)} />
        <GlowPath points={south} progress={arcP} color={C.amber} radius={0.0045} />
      </GlobeStage>

      <GlobeLabel x={satS.x} y={satS.y} text="INMARSAT-3 F1" sub="36 000 KM · GÉOSTATIONNAIRE" color={C.amber} opacity={ramp(frame, [6, 18], [0, 1]) * ramp(frame, [c1.at - 6, c1.at + 4], [1, 0])} />
      <GlobeLabel x={arcS.x} y={arcS.y} text="7ᵉ ARC" sub="00:19 UTC · DERNIER SIGNAL" color={C.amber} opacity={ramp(frame, [c2.at + 20, c2.at + 32], [0, 1])} />

      <AbsoluteFill style={{ padding: "236px 80px 0 80px" }}>
        <Reveal at={0}>
          <Kicker color={C.amber}>Dernier témoin · un satellite</Kicker>
        </Reveal>
        <Reveal at={c1.at}>
          <Headline size={100} style={{ marginTop: 14 }}>
            Une distance,
          </Headline>
        </Reveal>
        <Reveal at={c1.at + 18}>
          <Headline size={100} color={C.steel}>
            pas une position.
          </Headline>
        </Reveal>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
