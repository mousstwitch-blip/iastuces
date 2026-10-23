import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { IGARI, RadarScope, project } from "../components/RadarScope";
import { Headline, Kicker, Reveal } from "../components/Type";
import { easeInOut, ramp, rand } from "../lib/anim";
import { C } from "../theme";

/** 0:00 — a single transponder return on an ATC scope, then its label dies. */
export const S01Hook: React.FC<{ readonly vanishAt: number }> = ({ vanishAt }) => {
  const frame = useCurrentFrame();
  const [tx, ty] = project(IGARI);
  const push = ramp(frame, [0, 110], [1, 1.32], easeInOut);
  const lost = frame >= vanishAt;
  const reticle = lost ? (rand(frame * 3) > 0.4 ? 1 : 0.2) : 0.6 + 0.4 * Math.sin(frame / 4);
  const seconds = 10 + Math.floor(frame / 30);

  return (
    <AbsoluteFill style={{ backgroundColor: C.night }}>
      <AbsoluteFill style={{ scale: String(push), transformOrigin: `${tx}px ${ty}px` }}>
        <RadarScope showTarget vanishAt={vanishAt} sweepOffset={-12} />
        <svg width="1080" height="1920" style={{ position: "absolute", inset: 0 }}>
          <g opacity={reticle} stroke={lost ? C.red : C.amber} strokeWidth={3} fill="none">
            {[0, 1, 2, 3].map((k) => {
              const s = 46 + 6 * Math.sin(frame / 5);
              const sx = k % 2 === 0 ? -1 : 1;
              const sy = k < 2 ? -1 : 1;
              return (
                <path
                  key={k}
                  d={`M ${tx + sx * s} ${ty + sy * (s - 16)} L ${tx + sx * s} ${ty + sy * s} L ${tx + sx * (s - 16)} ${ty + sy * s}`}
                />
              );
            })}
          </g>
        </svg>
      </AbsoluteFill>

      <AbsoluteFill style={{ padding: "230px 80px 0 80px" }}>
        <Kicker color={C.phosphor} size={28}>
          Radar secondaire · {`17:21:${String(seconds).padStart(2, "0")}`} UTC
        </Kicker>
        <Reveal at={0} dur={8} rise={18}>
          <Headline size={124} style={{ marginTop: 18 }}>
            {lost ? <span style={{ color: C.red }}>Disparu.</span> : <>Regardez ce point.</>}
          </Headline>
        </Reveal>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
