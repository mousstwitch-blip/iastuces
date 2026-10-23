import React from "react";
import { AbsoluteFill } from "remotion";

/**
 * Vignette + a bottom gradient that keeps the captions legible.
 * Film grain is added after rendering (ffmpeg, see scripts/finish.sh): it is
 * much cheaper there than compositing a full-frame noise layer per frame.
 */
export const FilmLook: React.FC = () => {
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(5,8,13,0.55) 0%, rgba(5,8,13,0) 14%, rgba(5,8,13,0) 58%, rgba(5,8,13,0.72) 76%, rgba(5,8,13,0.35) 100%)",
        }}
      />
      <AbsoluteFill
        style={{
          background: "radial-gradient(ellipse 85% 70% at 50% 45%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.6) 100%)",
        }}
      />
    </AbsoluteFill>
  );
};
