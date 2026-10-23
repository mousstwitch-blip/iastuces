import { geoAzimuthalEquidistant, geoPath } from "d3-geo";
import type { FeatureCollection } from "geojson";
import React, { useMemo } from "react";
import { useCurrentFrame } from "remotion";
import region from "../data/sea-region.json";
import { rand } from "../lib/anim";
import { C, mono } from "../theme";

export const SCOPE = { cx: 540, cy: 900, r: 470 };
const CENTER: [number, number] = [102.29, 6.17]; // radar site, NE Malaysia
const RANGE_DEG = 3.1;
const SWEEP_PERIOD = 60; // frames per revolution

const projection = geoAzimuthalEquidistant()
  .rotate([-CENTER[0], -CENTER[1]])
  .clipAngle(RANGE_DEG)
  .scale(SCOPE.r / ((RANGE_DEG * Math.PI) / 180))
  .translate([SCOPE.cx, SCOPE.cy]);

export const IGARI: [number, number] = [103.585, 6.936];
export const project = (lonlat: [number, number]) => projection(lonlat) as [number, number];

const bearingOf = ([x, y]: [number, number]) => {
  const b = (Math.atan2(x - SCOPE.cx, -(y - SCOPE.cy)) * 180) / Math.PI;
  return (b + 360) % 360;
};

type Props = {
  /** Global frame offset so the sweep stays continuous between scenes. */
  readonly sweepOffset?: number;
  readonly showTarget: boolean;
  /** Scene-local frame when the transponder reply disappears. */
  readonly vanishAt?: number;
  readonly dim?: number;
};

export const RadarScope: React.FC<Props> = ({ sweepOffset = 0, showTarget, vanishAt = Infinity, dim = 1 }) => {
  const frame = useCurrentFrame();
  const land = useMemo(() => geoPath(projection)(region as unknown as FeatureCollection) ?? "", []);
  const sweep = (((frame + sweepOffset) / SWEEP_PERIOD) * 360) % 360;

  const target = project(IGARI);
  const tb = bearingOf(target);
  const since = (sweep - tb + 360) % 360; // degrees since the sweep crossed the target
  const glow = Math.exp(-since / 110);
  // the plot only refreshes when the sweep passes it, so it lingers after the reply stops
  const lastHitFrame = frame - (since / 360) * SWEEP_PERIOD;
  const alive = showTarget && lastHitFrame < vanishAt;
  const blockFlicker = frame >= vanishAt && frame < vanishAt + 10 ? rand(frame * 7) > 0.5 : frame < vanishAt;
  const trail = [1, 2, 3, 4, 5].map((k) => project([IGARI[0] - 0.05 * k, IGARI[1] - 0.105 * k]));

  const rings = [50, 100, 150, 200, 250, 300];
  const kmToPx = SCOPE.r / ((RANGE_DEG * Math.PI) / 180) / 6371;

  return (
    <svg width="1080" height="1920" style={{ position: "absolute", inset: 0, opacity: dim }}>
      <defs>
        <radialGradient id="glass" cx="50%" cy="45%" r="60%">
          <stop offset="0%" stopColor="#0d2a20" />
          <stop offset="70%" stopColor="#06140f" />
          <stop offset="100%" stopColor="#020806" />
        </radialGradient>
        <clipPath id="scope">
          <circle cx={SCOPE.cx} cy={SCOPE.cy} r={SCOPE.r} />
        </clipPath>
        <filter id="phos" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="5" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse">
          <rect width="4" height="1" fill="rgba(0,0,0,0.35)" />
        </pattern>
      </defs>

      <circle cx={SCOPE.cx} cy={SCOPE.cy} r={SCOPE.r + 26} fill="#0b0f12" stroke="#1d2a30" strokeWidth={3} />
      <circle cx={SCOPE.cx} cy={SCOPE.cy} r={SCOPE.r} fill="url(#glass)" />

      <g clipPath="url(#scope)">
        <path d={land} fill="rgba(99,255,180,0.05)" stroke={C.phosphorDim} strokeWidth={2} />
        {rings.map((km) => (
          <g key={km}>
            <circle cx={SCOPE.cx} cy={SCOPE.cy} r={km * kmToPx} fill="none" stroke="rgba(99,255,180,0.16)" strokeWidth={1.5} />
            <text x={SCOPE.cx + 6} y={SCOPE.cy - km * kmToPx - 6} fill="rgba(99,255,180,0.4)" fontFamily={mono} fontSize={18}>
              {km}
            </text>
          </g>
        ))}
        <line x1={SCOPE.cx - SCOPE.r} y1={SCOPE.cy} x2={SCOPE.cx + SCOPE.r} y2={SCOPE.cy} stroke="rgba(99,255,180,0.1)" />
        <line x1={SCOPE.cx} y1={SCOPE.cy - SCOPE.r} x2={SCOPE.cx} y2={SCOPE.cy + SCOPE.r} stroke="rgba(99,255,180,0.1)" />

        <foreignObject x={SCOPE.cx - SCOPE.r} y={SCOPE.cy - SCOPE.r} width={SCOPE.r * 2} height={SCOPE.r * 2}>
          <div
            style={{
              width: "100%",
              height: "100%",
              borderRadius: "50%",
              background: `conic-gradient(from ${sweep - 75}deg, rgba(99,255,180,0) 0deg, rgba(99,255,180,0.05) 40deg, rgba(99,255,180,0.32) 75deg, rgba(0,0,0,0) 75.4deg)`,
            }}
          />
        </foreignObject>
        <line
          x1={SCOPE.cx}
          y1={SCOPE.cy}
          x2={SCOPE.cx + Math.sin((sweep * Math.PI) / 180) * SCOPE.r}
          y2={SCOPE.cy - Math.cos((sweep * Math.PI) / 180) * SCOPE.r}
          stroke={C.phosphor}
          strokeWidth={3}
          filter="url(#phos)"
        />

        {showTarget
          ? trail.map(([x, y], i) => (
              <circle key={i} cx={x} cy={y} r={5} fill={C.phosphor} opacity={0.42 - i * 0.07} />
            ))
          : null}
        {alive ? (
          <g filter="url(#phos)" opacity={0.35 + 0.65 * glow}>
            <rect x={target[0] - 9} y={target[1] - 9} width={18} height={18} fill="none" stroke={C.phosphor} strokeWidth={3} />
            <circle cx={target[0]} cy={target[1]} r={4} fill={C.phosphor} />
          </g>
        ) : null}
        {showTarget && blockFlicker ? (
          <g fontFamily={mono} fill={C.phosphor} filter="url(#phos)">
            <line x1={target[0] - 10} y1={target[1] - 10} x2={target[0] - 56} y2={target[1] - 56} stroke={C.phosphor} strokeWidth={2} />
            <text x={target[0] - 62} y={target[1] - 84} fontSize={30} fontWeight={700} textAnchor="end">
              MAS370
            </text>
            <text x={target[0] - 62} y={target[1] - 50} fontSize={26} textAnchor="end">
              350 B772
            </text>
          </g>
        ) : null}
        <rect x={0} y={0} width={1080} height={1920} fill="url(#scan)" />
      </g>

      {Array.from({ length: 72 }, (_, i) => {
        const a = (i * 5 * Math.PI) / 180;
        const long = i % 6 === 0;
        const r0 = SCOPE.r + 4;
        const r1 = SCOPE.r + (long ? 22 : 12);
        return (
          <line
            key={i}
            x1={SCOPE.cx + Math.sin(a) * r0}
            y1={SCOPE.cy - Math.cos(a) * r0}
            x2={SCOPE.cx + Math.sin(a) * r1}
            y2={SCOPE.cy - Math.cos(a) * r1}
            stroke={long ? "rgba(99,255,180,0.6)" : "rgba(99,255,180,0.25)"}
            strokeWidth={long ? 3 : 1.5}
          />
        );
      })}
      {[0, 90, 180, 270].map((deg) => {
        const a = (deg * Math.PI) / 180;
        return (
          <text
            key={deg}
            x={SCOPE.cx + Math.sin(a) * (SCOPE.r + 50)}
            y={SCOPE.cy - Math.cos(a) * (SCOPE.r + 50) + 8}
            textAnchor="middle"
            fill="rgba(99,255,180,0.55)"
            fontFamily={mono}
            fontSize={22}
          >
            {String(deg).padStart(3, "0")}
          </text>
        );
      })}
    </svg>
  );
};
