import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { rand } from "../lib/anim";

/**
 * Signal-loss overlay used on cuts where a signal dies: tearing bars,
 * RGB-split slivers and a dropped frame of noise. Place it in a Sequence.
 */
export const SignalLoss: React.FC<{ readonly intensity?: number; readonly tint?: string }> = ({
  intensity = 1,
  tint = "255,77,61",
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const p = frame / Math.max(1, durationInFrames - 1);
  const env = Math.sin(Math.PI * p) * intensity;
  const bars = Array.from({ length: 14 }, (_, i) => {
    const r = rand(frame * 31 + i * 7);
    return {
      y: rand(frame * 13 + i) * 1920,
      h: 4 + r * 70 * env,
      x: (rand(frame * 5 + i * 3) - 0.5) * 220 * env,
      o: 0.15 + r * 0.6,
      c: i % 3 === 0 ? `rgba(${tint},0.55)` : i % 3 === 1 ? "rgba(90,200,255,0.45)" : "rgba(235,240,245,0.5)",
    };
  });
  const noiseFrame = rand(frame * 3.3) > 0.55;
  return (
    <AbsoluteFill style={{ pointerEvents: "none", mixBlendMode: "screen" }}>
      {bars.map((b, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: 0,
            width: 1080,
            top: b.y,
            height: b.h,
            translate: `${b.x}px 0px`,
            background: b.c,
            opacity: b.o * env,
          }}
        />
      ))}
      {noiseFrame && env > 0.35 ? (
        <svg width="1080" height="1920" style={{ position: "absolute", inset: 0, opacity: 0.55 * env }}>
          <filter id={`sn${frame}`}>
            <feTurbulence type="fractalNoise" baseFrequency="0.6 0.02" numOctaves="1" seed={frame} />
            <feColorMatrix type="saturate" values="0" />
          </filter>
          <rect width="1080" height="1920" filter={`url(#sn${frame})`} />
        </svg>
      ) : null}
    </AbsoluteFill>
  );
};

/** Jitter applied to a wrapped scene while its signal is failing. */
export const useJitter = (from: number, to: number, amount = 18) => {
  const frame = useCurrentFrame();
  if (frame < from || frame > to) return { translate: "0px 0px" } as React.CSSProperties;
  return {
    translate: `${(rand(frame * 9.1) - 0.5) * amount}px ${(rand(frame * 4.7) - 0.5) * amount * 0.3}px`,
    filter: `contrast(${1.1 + rand(frame) * 0.4}) saturate(${0.6 + rand(frame * 2) * 0.8})`,
  } as React.CSSProperties;
};
