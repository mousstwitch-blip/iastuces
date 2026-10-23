import { geoGraticule10, geoMercator, geoPath } from "d3-geo";
import type { FeatureCollection } from "geojson";
import React, { useMemo } from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import region from "../data/sea-region.json";
import { Headline, Kicker, Reveal } from "../components/Type";
import { easeInOut, ramp } from "../lib/anim";
import { cues } from "../timeline";
import { C, mono } from "../theme";

const proj = geoMercator().center([100.6, 4.6]).scale(6190).translate([540, 960]);
const P = (lon: number, lat: number) => proj([lon, lat]) as [number, number];

const KUL = P(101.71, 2.745);
const IGARI = P(103.585, 6.936);
// Simplified military primary-radar track (turn-back, across the peninsula,
// past Penang, then north-west up the Strait of Malacca). Approximate.
const PLOTS: [number, number][] = [
  [103.25, 6.75],
  [102.75, 6.45],
  [102.25, 6.1],
  [101.75, 5.8],
  [101.2, 5.55],
  [100.62, 5.38],
  [100.05, 5.5],
  [99.5, 5.78],
  [98.95, 6.06],
  [98.4, 6.33],
  [97.85, 6.6],
  [97.35, 6.85],
].map(([lon, lat]) => P(lon, lat));

const CITIES: { name: string; ll: [number, number]; side: "l" | "r" }[] = [
  { name: "Kuala Lumpur", ll: [101.69, 3.14], side: "r" },
  { name: "Penang", ll: [100.33, 5.41], side: "l" },
  { name: "Kota Bharu", ll: [102.24, 6.13], side: "l" },
];

/** 0:23 — military primary radar keeps an anonymous echo until 02:22. */
export const S05Military: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const [c0, c1, c2] = cues("military");
  const path = useMemo(() => geoPath(proj), []);
  const land = useMemo(() => path(region as unknown as FeatureCollection) ?? "", [path]);
  const grat = useMemo(() => path(geoGraticule10()) ?? "", [path]);

  const zoom = ramp(frame, [0, durationInFrames], [1.18, 1.0], easeInOut);
  const panX = ramp(frame, [0, durationInFrames], [-120, 40], easeInOut);
  const plotStart = c0.at + 6;
  const plotEnd = c2.at + 4;
  const shown = ramp(frame, [plotStart, plotEnd], [0, PLOTS.length], (t) => t);
  const lastVanish = c2.end - 2;
  const last = PLOTS[PLOTS.length - 1];

  return (
    <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 55%, #061524 0%, #040c16 70%, #02060b 100%)" }}>
      <svg width="1080" height="1920" style={{ position: "absolute", inset: 0 }}>
        <defs>
          <filter id="mglow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="6" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        <g transform={`translate(${540 + panX} 960) scale(${zoom}) translate(-540 -960)`}>
          <path d={grat} fill="none" stroke="rgba(159,180,199,0.08)" strokeWidth={1.2} />
          <path d={land} fill="#16293d" stroke="#6f8ea8" strokeWidth={2} />

          <text x={P(101.9, 4.4)[0]} y={P(101.9, 4.4)[1]} fill="rgba(159,180,199,0.45)" fontFamily={mono} fontSize={30} letterSpacing="0.3em" textAnchor="middle">
            MALAISIE
          </text>
          <text x={P(99.6, 8.1)[0]} y={P(99.6, 8.1)[1]} fill="rgba(159,180,199,0.4)" fontFamily={mono} fontSize={26} letterSpacing="0.3em" textAnchor="middle">
            THAÏLANDE
          </text>
          <text x={P(98.7, 3.0)[0]} y={P(98.7, 3.0)[1]} fill="rgba(159,180,199,0.4)" fontFamily={mono} fontSize={26} letterSpacing="0.3em" textAnchor="middle">
            SUMATRA
          </text>
          <text x={P(99.3, 4.75)[0]} y={P(99.3, 4.75)[1]} fill="rgba(110,160,200,0.45)" fontFamily={mono} fontSize={19} letterSpacing="0.25em" textAnchor="middle" transform={`rotate(-38 ${P(99.3, 4.75)[0]} ${P(99.3, 4.75)[1]})`}>
            DÉTROIT DE MALACCA
          </text>

          {/* planned route continues to Vietnam / Beijing */}
          <line x1={IGARI[0]} y1={IGARI[1]} x2={IGARI[0] + 160} y2={IGARI[1] - 190} stroke={C.steel} strokeWidth={3} strokeDasharray="10 10" opacity={0.6} />
          <text x={IGARI[0] + 120} y={IGARI[1] - 210} fill={C.steel} fontFamily={mono} fontSize={22} textAnchor="middle" opacity={0.8}>
            VERS PÉKIN
          </text>
          <line x1={KUL[0]} y1={KUL[1]} x2={IGARI[0]} y2={IGARI[1]} stroke={C.amber} strokeWidth={5} />
          <g transform={`translate(${IGARI[0]} ${IGARI[1]})`}>
            <path d="M -12 -12 L 12 12 M -12 12 L 12 -12" stroke={C.red} strokeWidth={5} />
            <text x={-20} y={44} fill={C.red} fontFamily={mono} fontSize={22} fontWeight={700} textAnchor="end">
              IGARI · 01:21
            </text>
            <text x={-20} y={70} fill={C.steel} fontFamily={mono} fontSize={19} textAnchor="end">
              TRANSPONDEUR MUET
            </text>
          </g>

          {CITIES.map((c) => {
            const [x, y] = P(...c.ll);
            return (
              <g key={c.name}>
                <circle cx={x} cy={y} r={6} fill={C.paper} />
                <text x={c.side === "r" ? x + 14 : x - 14} y={y + 7} fill={C.paper} fontFamily={mono} fontSize={23} textAnchor={c.side === "r" ? "start" : "end"} opacity={0.85}>
                  {c.name}
                </text>
              </g>
            );
          })}

          {PLOTS.map(([x, y], i) => {
            const age = shown - i;
            if (age <= 0) return null;
            const isLast = i === PLOTS.length - 1;
            if (isLast && frame >= lastVanish) return null;
            const glow = Math.max(0.25, 1 - (age - 1) * 0.18);
            const col = isLast && frame >= c2.at ? C.red : C.phosphor;
            return (
              <g key={i} filter="url(#mglow)" opacity={glow}>
                <rect x={x - 9} y={y - 9} width={18} height={18} fill="none" stroke={col} strokeWidth={3.5} />
              </g>
            );
          })}
          {frame >= c2.at && frame < lastVanish ? (
            <g>
              <circle cx={last[0]} cy={last[1]} r={20 + ((frame - c2.at) % 20) * 3} fill="none" stroke={C.red} strokeWidth={3} opacity={1 - ((frame - c2.at) % 20) / 20} />
            </g>
          ) : null}
        </g>
      </svg>

      <Reveal at={c2.at} style={{ position: "absolute", left: 80, top: 760 }}>
        <div style={{ fontFamily: mono, fontWeight: 700, fontSize: 96, color: C.red, letterSpacing: "-0.02em", textShadow: "0 0 30px rgba(255,77,61,0.45)" }}>
          02:22
        </div>
        <Kicker color={C.paper} size={26}>
          Dernier écho radar
        </Kicker>
      </Reveal>

      <AbsoluteFill style={{ padding: "236px 80px 0 80px" }}>
        <Reveal at={0}>
          <Kicker color={C.phosphor}>Radar militaire · primaire</Kicker>
        </Reveal>
        <Reveal at={c0.at + 4}>
          <Headline size={100} style={{ marginTop: 14 }}>
            Un écho.
            <br />
            <span style={{ color: C.steel }}>Sans nom.</span>
          </Headline>
        </Reveal>
      </AbsoluteFill>

      <div style={{ position: "absolute", left: 80, top: 1218, fontFamily: mono, fontSize: 19, color: C.steelDim, letterSpacing: "0.12em" }}>
        TRACÉ SIMPLIFIÉ · D’APRÈS L’ATSB ET LE RAPPORT MALAISIEN
      </div>
      <Reveal at={c1.at} style={{ position: "absolute", left: 80, top: 500 }}>
        <Kicker color={C.phosphor} size={22}>
          □ = écho primaire
        </Kicker>
      </Reveal>
    </AbsoluteFill>
  );
};
