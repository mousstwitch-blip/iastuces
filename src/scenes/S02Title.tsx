import React, { useMemo } from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { GlobeLabel } from "../components/GlobeLabel";
import { Headline, Kicker, Reveal } from "../components/Type";
import { easeInOut, easeOut, ramp } from "../lib/anim";
import { GlobeStage, GlowPath, SurfaceMarker, screenOf, type CameraShot } from "../three/Globe";
import { greatCircle, ll } from "../three/geo";
import { cues } from "../timeline";
import { C, display, mono } from "../theme";

const KUL: [number, number] = [2.745, 101.71];
const PEK: [number, number] = [40.08, 116.58];
const IGARI: [number, number] = [6.936, 103.585];
// Subsolar point on 8 March 2014 at 17:21 UTC: Asia is in the middle of the night.
const SUN = { lat: -4.7, lon: -83 };

export const S02Title: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const [c0, c1, c2] = cues("title");
  const t = ramp(frame, [0, durationInFrames], [0, 1], easeInOut);
  const shot: CameraShot = {
    lat: 4 + 6 * t,
    lon: 100 + 7 * t,
    dist: 2.75 - 0.5 * t,
    look: ll(14 + 3 * t, 107, 0.55).toArray() as [number, number, number],
    fov: 34,
  };
  const planned = useMemo(() => greatCircle(KUL, PEK, 120, 0.012), []);
  const flown = useMemo(() => greatCircle(KUL, IGARI, 40, 0.004), []);
  const flownP = ramp(frame, [c0.at + 4, c0.at + 50], [0, 1], easeInOut);
  const lostP = ramp(frame, [c2.at - 4, c2.at + 8], [0, 1]);
  const kulS = screenOf(shot, ll(KUL[0], KUL[1]));
  const pekS = screenOf(shot, ll(PEK[0], PEK[1]));
  const igS = screenOf(shot, ll(IGARI[0], IGARI[1]));
  const stamp = ramp(frame, [c2.at, c2.at + 9], [0, 1], easeOut);
  const pulse = ((frame - c0.at) % 30) / 30;

  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <GlobeStage shot={shot} sun={SUN} nightGain={1.25} exposure={1.1}>
        <GlowPath points={planned} progress={ramp(frame, [0, 40], [0, 1])} color={C.steel} radius={0.0022} opacity={0.55 * (1 - lostP * 0.7)} />
        <GlowPath points={flown} progress={flownP} color={C.amber} radius={0.003} />
        <SurfaceMarker lat={KUL[0]} lon={KUL[1]} color={C.paper} size={0.008} />
        <SurfaceMarker lat={PEK[0]} lon={PEK[1]} color={C.paper} size={0.008} opacity={1 - lostP * 0.6} />
        {flownP > 0.98 ? (
          <SurfaceMarker lat={IGARI[0]} lon={IGARI[1]} color={lostP > 0.5 ? C.red : C.amber} size={0.011} pulse={pulse} />
        ) : null}
      </GlobeStage>

      <GlobeLabel x={kulS.x} y={kulS.y} text="KUALA LUMPUR" sub="00:41 · DÉPART" side="left" opacity={ramp(frame, [8, 20], [0, 1])} />
      <GlobeLabel x={pekS.x} y={pekS.y} text="PÉKIN" sub="DESTINATION" opacity={ramp(frame, [20, 32], [0, 1]) * (1 - lostP * 0.6)} />
      <GlobeLabel
        x={igS.x}
        y={igS.y}
        text="01:21"
        sub="DERNIER CONTACT"
        color={lostP > 0.5 ? C.red : C.amber}
        opacity={ramp(frame, [c0.at + 50, c0.at + 62], [0, 1])}
      />

      <AbsoluteFill style={{ padding: "236px 80px 0 80px" }}>
        <Reveal at={c0.at}>
          <Kicker color={C.amber}>8 mars 2014 · Malaysia Airlines</Kicker>
        </Reveal>
        <Reveal at={c0.at + 5} rise={40}>
          <Headline size={232} style={{ marginTop: 10, letterSpacing: "-0.05em" }}>
            MH370
          </Headline>
        </Reveal>
        <Reveal at={c0.at + 12}>
          <Kicker size={30} style={{ marginTop: 6 }}>
            Boeing 777 · Kuala Lumpur → Pékin
          </Kicker>
        </Reveal>
        <Reveal at={c1.at} style={{ marginTop: 44, display: "flex", alignItems: "baseline", gap: 22 }}>
          <span style={{ fontFamily: display, fontWeight: 900, fontSize: 150, color: C.amber, letterSpacing: "-0.04em" }}>
            {Math.round(ramp(frame, [c1.at, c1.at + 24], [180, 239]))}
          </span>
          <span style={{ fontFamily: mono, fontSize: 34, color: C.paper, letterSpacing: "0.12em", lineHeight: 1.25 }}>
            PERSONNES
            <br />À BORD
          </span>
        </Reveal>
      </AbsoluteFill>

      {stamp > 0 ? (
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            top: 860,
            display: "flex",
            justifyContent: "center",
            opacity: stamp,
            scale: String(1.5 - 0.5 * stamp),
          }}
        >
          <div
            style={{
              rotate: "-4deg",
              border: `6px solid ${C.red}`,
              padding: "10px 30px",
              fontFamily: display,
              fontWeight: 900,
              fontSize: 92,
              letterSpacing: "0.02em",
              color: C.red,
              background: "rgba(10,0,0,0.35)",
              textShadow: "0 0 30px rgba(255,77,61,0.5)",
            }}
          >
            JAMAIS RETROUVÉ
          </div>
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
