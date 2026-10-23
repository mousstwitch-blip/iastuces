import React, { useMemo } from "react";
import { AbsoluteFill, Img, Sequence, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { GlobeLabel } from "../components/GlobeLabel";
import { Headline, Kicker, Reveal } from "../components/Type";
import { easeInOut, ramp } from "../lib/anim";
import { GlobeStage, GlowPath, SurfaceMarker, screenOf, type CameraShot } from "../three/Globe";
import { ll, smallCircle } from "../three/geo";
import { cues } from "../timeline";
import { C, display, mono } from "../theme";
import { ARC7_RADIUS, SAT_SUBPOINT } from "./S07Satellite";

const LANES = 6;
const PLANE = { w: 1600, h: 2400 };

/** Multibeam swaths reveal a (procedural, illustrative) seabed lane by lane. */
const SeabedShot: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const km = Math.round(ramp(frame, [4, durationInFrames - 8], [0, 120000], easeInOut) / 1000) * 1000;
  const laneW = PLANE.w / LANES;
  const drift = ramp(frame, [0, durationInFrames], [0, -260], (t) => t);
  return (
    <AbsoluteFill style={{ backgroundColor: "#01040a", perspective: 1300, overflow: "hidden" }}>
      <div
        style={{
          position: "absolute",
          left: (1080 - PLANE.w) / 2,
          top: 420,
          width: PLANE.w,
          height: PLANE.h,
          transformOrigin: "50% 0%",
          rotate: "x 52deg",
          translate: `0px ${drift}px`,
        }}
      >
        <Img
          src={staticFile("tex/bathymetry.jpg")}
          style={{ position: "absolute", inset: 0, width: PLANE.w, height: PLANE.h, filter: "grayscale(1) brightness(0.22) contrast(1.2)" }}
        />
        {Array.from({ length: LANES }, (_, k) => {
          const start = 2 + k * 7;
          const p = ramp(frame, [start, start + 16], [0, 1], (t) => t);
          if (p <= 0) return null;
          const down = k % 2 === 0;
          const clip = down ? `inset(0 0 ${(1 - p) * 100}% 0)` : `inset(${(1 - p) * 100}% 0 0 0)`;
          const edge = down ? p * PLANE.h : (1 - p) * PLANE.h;
          return (
            <div key={k} style={{ position: "absolute", left: k * laneW, top: 0, width: laneW, height: PLANE.h }}>
              <div
                style={{
                  position: "absolute",
                  inset: 0,
                  backgroundImage: `url(${staticFile("tex/bathymetry.jpg")})`,
                  backgroundSize: `${PLANE.w}px ${PLANE.h}px`,
                  backgroundPosition: `${-k * laneW}px 0px`,
                  clipPath: clip,
                  borderLeft: "2px solid rgba(0,0,0,0.5)",
                }}
              />
              {p < 1 ? (
                <div
                  style={{
                    position: "absolute",
                    left: 0,
                    width: laneW,
                    top: edge - 6,
                    height: 12,
                    background: C.phosphor,
                    boxShadow: `0 0 40px 12px ${C.phosphor}`,
                    opacity: 0.9,
                  }}
                />
              ) : null}
            </div>
          );
        })}
      </div>
      <AbsoluteFill style={{ background: "linear-gradient(180deg, #01040a 0%, rgba(1,4,10,0.9) 26%, rgba(1,4,10,0) 48%)" }} />
      <AbsoluteFill style={{ padding: "236px 80px 0 80px" }}>
        <Kicker color={C.phosphor}>Sonar · fond de l’océan Indien</Kicker>
        <div style={{ marginTop: 18, display: "flex", alignItems: "baseline", gap: 18 }}>
          <span style={{ fontFamily: display, fontWeight: 900, fontSize: 168, letterSpacing: "-0.05em", color: C.paper, fontVariantNumeric: "tabular-nums" }}>
            {km.toLocaleString("fr-FR").replace(/\u202f|\u00a0/g, " ")}
          </span>
          <span style={{ fontFamily: display, fontWeight: 800, fontSize: 72, color: C.phosphor }}>km²</span>
        </div>
        <Kicker size={26} style={{ marginTop: 6 }}>
          fouillés · 2014 – 2017
        </Kicker>
      </AbsoluteFill>
      <div style={{ position: "absolute", right: 150, top: 1218, fontFamily: mono, fontSize: 19, color: C.steelDim, letterSpacing: "0.12em" }}>
        ILLUSTRATION · RELIEF SIMULÉ
      </div>
    </AbsoluteFill>
  );
};

const REUNION: [number, number] = [-20.9, 55.5];
// Other coastlines where debris attributed to MH370 washed up (ATSB debris reports).
const DEBRIS: [number, number][] = [
  [-21.7, 35.4], // Mozambique
  [-34.2, 22.1], // South Africa
  [-19.7, 63.4], // Rodrigues, Mauritius
  [-5.1, 39.8], // Pemba, Tanzania
  [-16.9, 49.9], // Madagascar
];
const SUN = { lat: 14, lon: 104 };

const DebrisShot: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const t = ramp(frame, [0, durationInFrames], [0, 1], easeInOut);
  const shot: CameraShot = {
    lat: -20 - 4 * t,
    lon: 70 - 4 * t,
    dist: 4.8 - 0.4 * t,
    look: ll(-26, 68, 0.3).toArray() as [number, number, number],
    fov: 34,
  };
  const arc = useMemo(() => smallCircle(SAT_SUBPOINT, ARC7_RADIUS, 108, 162, 120, 1.004), []);
  const zone = useMemo(() => smallCircle(SAT_SUBPOINT, ARC7_RADIUS, 141, 152, 40, 1.004), []);
  const reS = screenOf(shot, ll(REUNION[0], REUNION[1]));
  const zS = screenOf(shot, ll(-36, 90));
  const pulse = (frame % 28) / 28;
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <GlobeStage shot={shot} sun={SUN} nightGain={0.6}>
        <GlowPath points={arc} progress={1} color={C.amber} radius={0.003} opacity={0.6} />
        <GlowPath points={zone} progress={1} color={C.phosphor} radius={0.02} opacity={0.35} />
        {DEBRIS.map(([la, lo], i) => (
          <SurfaceMarker key={i} lat={la} lon={lo} color={C.paper} size={0.007} opacity={ramp(frame, [6 + i * 4, 14 + i * 4], [0, 1])} />
        ))}
        <SurfaceMarker lat={REUNION[0]} lon={REUNION[1]} color={C.red} size={0.011} pulse={frame > 20 ? pulse : 0} opacity={ramp(frame, [14, 22], [0, 1])} />
      </GlobeStage>
      <GlobeLabel x={zS.x} y={zS.y} text="ZONE FOUILLÉE" color={C.phosphor} opacity={ramp(frame, [0, 10], [0, 1])} />
      <GlobeLabel
        x={reS.x}
        y={reS.y}
        text="LA RÉUNION"
        sub="29 JUILLET 2015 · FLAPERON"
        color={C.red}
        opacity={ramp(frame, [22, 34], [0, 1])}
      />
      <AbsoluteFill style={{ padding: "236px 80px 0 80px" }}>
        <Reveal at={0}>
          <Kicker color={C.paper}>Seuls indices retrouvés</Kicker>
        </Reveal>
        <Reveal at={4}>
          <Headline size={104} style={{ marginTop: 14 }}>
            Des débris,
          </Headline>
        </Reveal>
        <Reveal at={22}>
          <Headline size={104} color={C.steel}>
            à des milliers
            <br />
            de km.
          </Headline>
        </Reveal>
      </AbsoluteFill>
      <div style={{ position: "absolute", left: 80, top: 1218, fontFamily: mono, fontSize: 19, color: C.steelDim, letterSpacing: "0.12em" }}>
        • DÉBRIS ATTRIBUÉS AU MH370
      </div>
    </AbsoluteFill>
  );
};

/** 0:39 — the seabed search, then the only physical evidence: debris on African shores. */
export const S08Search: React.FC = () => {
  const { durationInFrames } = useVideoConfig();
  const [, c1] = cues("search");
  const split = c1.at - 4;
  return (
    <AbsoluteFill>
      <Sequence name="Sonar" durationInFrames={split} premountFor={30}>
        <SeabedShot />
      </Sequence>
      <Sequence name="Débris" from={split} durationInFrames={durationInFrames - split} premountFor={30}>
        <DebrisShot />
      </Sequence>
    </AbsoluteFill>
  );
};
