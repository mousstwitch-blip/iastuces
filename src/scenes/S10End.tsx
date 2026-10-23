import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { IGARI, RadarScope, project } from "../components/RadarScope";
import { Headline, Kicker, Reveal } from "../components/Type";
import { easeInOut, ramp } from "../lib/anim";
import { cues } from "../timeline";
import { C, display, mono } from "../theme";

/** 0:51 — back to the scope from the opening, now empty. Loops into the hook. */
export const S10End: React.FC<{ readonly wipeIn: number }> = ({ wipeIn }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const [c0, c1, c2] = cues("end").map((c) => ({ ...c, at: c.at + wipeIn, end: c.end + wipeIn }));
  const wipe = ramp(frame, [0, wipeIn], [0, 360], easeInOut);
  const card = c2.end + 8;
  const scopeDim = ramp(frame, [card - 6, card + 14], [1, 0.25]);
  const [tx, ty] = project(IGARI);
  const fadeOut = ramp(frame, [durationInFrames - 12, durationInFrames], [1, 0]);
  const mask = wipe < 360 ? `conic-gradient(from 0deg at 50% 47%, #000 ${wipe}deg, transparent ${wipe}deg)` : undefined;

  return (
    <AbsoluteFill style={{ backgroundColor: C.night, maskImage: mask, WebkitMaskImage: mask, opacity: fadeOut }}>
      <AbsoluteFill style={{ opacity: scopeDim, scale: String(ramp(frame, [0, durationInFrames], [1.12, 1.0], easeInOut)) }}>
        <RadarScope showTarget={false} sweepOffset={20} />
        <svg width="1080" height="1920" style={{ position: "absolute", inset: 0 }}>
          <g stroke={C.red} strokeWidth={3} fill="none" strokeDasharray="8 8" opacity={0.7}>
            <rect x={tx - 40} y={ty - 40} width={80} height={80} />
          </g>
          <text x={tx} y={ty + 12} fill={C.red} fontFamily={mono} fontSize={34} fontWeight={700} textAnchor="middle">
            ?
          </text>
        </svg>
      </AbsoluteFill>

      {frame < card ? (
        <AbsoluteFill style={{ padding: "236px 80px 0 80px" }}>
          <Reveal at={c0.at} out={c1.at - 4}>
            <Kicker color={C.red}>Mars 2026 · nouvelle recherche</Kicker>
            <Headline size={118} color={C.red} style={{ marginTop: 14 }}>
              Sans résultat.
            </Headline>
          </Reveal>
        </AbsoluteFill>
      ) : null}
      {frame < card ? (
        <AbsoluteFill style={{ padding: "236px 80px 0 80px" }}>
          <Reveal at={c1.at}>
            <Headline size={104}>Un avion ne disparaît pas.</Headline>
          </Reveal>
          <Reveal at={c2.at} style={{ marginTop: 18 }}>
            <Headline size={104} color={C.amber}>
              Il sort de ce que nos radars savent voir.
            </Headline>
          </Reveal>
        </AbsoluteFill>
      ) : null}

      {frame >= card ? (
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", textAlign: "center", paddingBottom: 220 }}>
          <Reveal at={card}>
            <div style={{ fontFamily: display, fontWeight: 900, fontSize: 210, letterSpacing: "-0.05em", color: C.paper }}>MH370</div>
          </Reveal>
          <Reveal at={card + 8}>
            <Kicker color={C.amber} size={32}>
              239 personnes · toujours introuvable
            </Kicker>
          </Reveal>
          <Reveal at={card + 18} style={{ marginTop: 40 }}>
            <Kicker color={C.steelDim} size={20}>
              Sources : ATSB · rapport malaisien 2018 · OACI · Ocean Infinity
            </Kicker>
          </Reveal>
        </AbsoluteFill>
      ) : null}
    </AbsoluteFill>
  );
};
