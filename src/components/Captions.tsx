import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { ramp } from "../lib/anim";
import { TIMELINE } from "../timeline";
import { C, display } from "../theme";

const HIGHLIGHT = /\d|transpondeur|satellite|écho|arc|Réunion|radars?$|jamais|disparaît|position/i;

/**
 * Voice-over captions. Each chunk is its own TTS file, so chunk timing is exact;
 * words inside a chunk are revealed proportionally to their character offset.
 */
export const Captions: React.FC = () => {
  const frame = useCurrentFrame();
  const caps = TIMELINE.captions;
  const idx = caps.findIndex((c, i) => {
    const next = caps[i + 1];
    const until = next ? Math.min(next.from, c.from + c.durationInFrames + 14) : c.from + c.durationInFrames + 14;
    return frame >= c.from - 2 && frame < until;
  });
  if (idx === -1) return null;
  const cap = caps[idx];
  const words = cap.text.split(" ");
  const total = cap.text.length;
  let offset = 0;
  const local = frame - cap.from;
  const next = caps[idx + 1];
  const end = next ? Math.min(next.from, cap.from + cap.durationInFrames + 14) : cap.from + cap.durationInFrames + 14;
  const fadeOut = ramp(frame, [end - 5, end], [0, 1]);

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          left: 90,
          right: 150,
          top: 1262,
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          columnGap: "0.26em",
          rowGap: 4,
          fontFamily: display,
          fontWeight: 800,
          fontSize: 54,
          lineHeight: 1.12,
          letterSpacing: "-0.01em",
          textAlign: "center",
          opacity: 1 - fadeOut,
        }}
      >
        {words.map((w, i) => {
          const appear = (offset / total) * cap.durationInFrames * 0.92;
          offset += w.length + 1;
          const p = ramp(local, [appear - 1, appear + 5], [0, 1]);
          const hot = HIGHLIGHT.test(w);
          return (
            <span
              key={i}
              style={{
                display: "inline-block",
                color: hot ? C.amber : C.paper,
                opacity: 0.25 + 0.75 * p,
                scale: String(0.92 + 0.08 * p),
                textShadow: "0 3px 3px rgba(0,0,0,0.9), 0 0 28px rgba(0,0,0,0.85)",
              }}
            >
              {w}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
