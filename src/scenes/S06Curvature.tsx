import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { Headline, Kicker, Reveal } from "../components/Type";
import { easeInOut, ramp, rand } from "../lib/anim";
import { cues } from "../timeline";
import { C, mono } from "../theme";

// Schematic cross-section, curvature hugely exaggerated.
const EARTH = { cx: 230, cy: 2330, r: 1400 };
const RADAR = { x: 230, y: EARTH.cy - EARTH.r - 26 }; // antenna on the coast
const ALT = 120;

const surfaceY = (x: number) => EARTH.cy - Math.sqrt(EARTH.r * EARTH.r - (x - EARTH.cx) ** 2);

/** 0:29 — line of sight vs the curve of the Earth: past the horizon, nothing. */
export const S06Curvature: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const [, c1] = cues("curvature");
  const zoomOut = ramp(frame, [0, durationInFrames], [1.08, 0.96], easeInOut);
  const px = ramp(frame, [6, c1.at + 46], [380, 1010], easeInOut);
  const angle = Math.asin((px - EARTH.cx) / (EARTH.r + ALT));
  const planeX = EARTH.cx + Math.sin(angle) * (EARTH.r + ALT);
  const planeY = EARTH.cy - Math.cos(angle) * (EARTH.r + ALT);
  const beamY = RADAR.y;
  const hidden = planeY - 14 > beamY;
  const beamP = ramp(frame, [0, 18], [0, 1]);

  // ocean surface path
  const pts: string[] = [];
  for (let x = -20; x <= 1100; x += 20) pts.push(`${x},${surfaceY(x).toFixed(1)}`);
  const surface = `M ${pts.join(" L ")} L 1100,1920 L -20,1920 Z`;
  const blind = `M ${RADAR.x} ${beamY} L 1100 ${beamY} L 1100 ${surfaceY(1100)} ${pts
    .filter((p) => Number(p.split(",")[0]) >= RADAR.x)
    .reverse()
    .map((p) => `L ${p}`)
    .join(" ")} Z`;

  return (
    <AbsoluteFill style={{ background: "linear-gradient(180deg, #02050a 0%, #06101d 55%, #0a1a2c 75%)" }}>
      <AbsoluteFill style={{ scale: String(zoomOut), transformOrigin: "50% 75%" }}>
        <svg width="1080" height="1920">
          <defs>
            <linearGradient id="sea" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stopColor="#1b4a6b" />
              <stop offset="0.08" stopColor="#0c2a42" />
              <stop offset="1" stopColor="#02070d" />
            </linearGradient>
            <linearGradient id="beam" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0" stopColor={C.phosphor} stopOpacity="0.55" />
              <stop offset="1" stopColor={C.phosphor} stopOpacity="0.05" />
            </linearGradient>
            <filter id="atm" x="-10%" y="-10%" width="120%" height="120%">
              <feGaussianBlur stdDeviation="18" />
            </filter>
          </defs>
          {Array.from({ length: 90 }, (_, i) => (
            <circle key={i} cx={rand(i + 3) * 1080} cy={rand(i + 40) * 1100} r={rand(i + 8) * 1.5 + 0.3} fill="#dfe8ff" opacity={0.2 + rand(i) * 0.5} />
          ))}
          <path d={surface} fill="none" stroke="#3d8fd0" strokeWidth={30} opacity={0.35} filter="url(#atm)" />
          <path d={blind} fill={C.red} opacity={0.12 * ramp(frame, [c1.at - 6, c1.at + 10], [0, 1])} />
          <path d={surface} fill="url(#sea)" stroke="#6fb4e6" strokeWidth={2.5} />

          {/* line of sight */}
          <polygon
            points={`${RADAR.x},${RADAR.y} ${RADAR.x + 900 * beamP},${beamY - 34 * beamP} ${RADAR.x + 900 * beamP},${beamY + 4}`}
            fill="url(#beam)"
          />
          <line x1={RADAR.x} y1={beamY} x2={RADAR.x + 880 * beamP} y2={beamY} stroke={C.phosphor} strokeWidth={3} strokeDasharray="14 10" />

          {/* coast + radar */}
          <path d={`M ${RADAR.x - 260} ${surfaceY(RADAR.x - 260) + 4} L ${RADAR.x - 40} ${surfaceY(RADAR.x - 40) - 18} L ${RADAR.x + 30} ${surfaceY(RADAR.x + 30) + 2} Z`} fill="#24384a" />
          <rect x={RADAR.x - 4} y={RADAR.y} width={8} height={30} fill={C.paper} />
          <path d={`M ${RADAR.x - 22} ${RADAR.y + 2} Q ${RADAR.x} ${RADAR.y - 26} ${RADAR.x + 22} ${RADAR.y + 2} Z`} fill={C.paper} />

          {/* aircraft, nose to the right */}
          <g transform={`translate(${planeX} ${planeY}) rotate(${(angle * 180) / Math.PI})`} opacity={hidden ? 0.75 : 1}>
            <path
              d="M -38 0 Q -30 -9 0 -8 L 26 -8 Q 40 -6 44 0 Q 40 4 26 5 L -30 5 Q -38 4 -38 0 Z M -30 -6 L -40 -24 L -30 -24 L -18 -7 Z M -4 1 L -20 14 L -8 14 L 12 2 Z"
              fill={hidden ? "none" : C.amber}
              stroke={hidden ? C.red : C.amber}
              strokeWidth={hidden ? 2.5 : 0}
              strokeDasharray={hidden ? "5 4" : undefined}
            />
          </g>
          {!hidden ? (
            <circle cx={planeX} cy={planeY} r={38 + (frame % 15) * 1.5} fill="none" stroke={C.phosphor} strokeWidth={2.5} opacity={1 - (frame % 15) / 15} />
          ) : (
            <text x={planeX} y={planeY - 34} textAnchor="middle" fill={C.red} fontFamily={mono} fontSize={30} fontWeight={700}>
              ?
            </text>
          )}

          <text x={RADAR.x - 10} y={RADAR.y + 92} fill={C.paper} fontFamily={mono} fontSize={22} letterSpacing="0.12em">
            RADAR CÔTIER
          </text>
          <text x={760} y={beamY - 22} fill={C.phosphor} fontFamily={mono} fontSize={22} letterSpacing="0.12em" textAnchor="middle" opacity={beamP}>
            LIGNE DE VUE
          </text>
          <text
            x={700}
            y={beamY + 150}
            fill={C.red}
            fontFamily={mono}
            fontSize={26}
            fontWeight={700}
            letterSpacing="0.14em"
            textAnchor="middle"
            opacity={ramp(frame, [c1.at, c1.at + 12], [0, 1])}
          >
            ZONE AVEUGLE
          </text>
        </svg>
      </AbsoluteFill>

      <AbsoluteFill style={{ padding: "236px 80px 0 80px" }}>
        <Reveal at={0}>
          <Kicker>Loin des côtes</Kicker>
        </Reveal>
        <Reveal at={6}>
          <Headline size={104} style={{ marginTop: 14 }}>
            La Terre est ronde.
          </Headline>
        </Reveal>
        <Reveal at={c1.at + 4}>
          <Headline size={104} color={C.red}>
            Le radar, lui, voit droit.
          </Headline>
        </Reveal>
      </AbsoluteFill>
      <div style={{ position: "absolute", right: 150, top: 1218, fontFamily: mono, fontSize: 19, color: C.steelDim, letterSpacing: "0.12em" }}>
        SCHÉMA · ÉCHELLE EXAGÉRÉE
      </div>
    </AbsoluteFill>
  );
};
