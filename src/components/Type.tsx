import React from "react";
import { useCurrentFrame } from "remotion";
import { ramp } from "../lib/anim";
import { C, display, mono } from "../theme";

type RevealProps = {
  readonly at: number;
  readonly out?: number;
  readonly dur?: number;
  readonly rise?: number;
  readonly style?: React.CSSProperties;
  readonly children: React.ReactNode;
};

/** Fades/rises/de-blurs its content in at `at` and optionally out at `out` (scene-local frames). */
export const Reveal: React.FC<RevealProps> = ({ at, out, dur = 14, rise = 28, style, children }) => {
  const frame = useCurrentFrame();
  const inP = ramp(frame, [at, at + dur], [0, 1]);
  const outP = out === undefined ? 0 : ramp(frame, [out, out + 10], [0, 1]);
  return (
    <div
      style={{
        opacity: inP * (1 - outP),
        translate: `0px ${(1 - inP) * rise - outP * 12}px`,
        filter: `blur(${(1 - inP) * 10 + outP * 6}px)`,
        ...style,
      }}
    >
      {children}
    </div>
  );
};

export const Kicker: React.FC<{
  readonly children: React.ReactNode;
  readonly color?: string;
  readonly size?: number;
  readonly style?: React.CSSProperties;
}> = ({ children, color = C.steel, size = 32, style }) => (
  <div
    style={{
      fontFamily: mono,
      fontWeight: 500,
      fontSize: size,
      letterSpacing: "0.16em",
      textTransform: "uppercase",
      color,
      ...style,
    }}
  >
    {children}
  </div>
);

export const Headline: React.FC<{
  readonly children: React.ReactNode;
  readonly size?: number;
  readonly color?: string;
  readonly style?: React.CSSProperties;
}> = ({ children, size = 110, color = C.paper, style }) => (
  <div
    style={{
      fontFamily: display,
      fontWeight: 900,
      fontSize: size,
      lineHeight: 0.92,
      letterSpacing: "-0.035em",
      color,
      textShadow: "0 6px 40px rgba(0,0,0,0.65)",
      ...style,
    }}
  >
    {children}
  </div>
);

/** A word-by-word staggered headline. */
export const StaggerWords: React.FC<{
  readonly text: string;
  readonly at: number;
  readonly step?: number;
  readonly style?: React.CSSProperties;
  readonly wordStyle?: (i: number, word: string) => React.CSSProperties;
}> = ({ text, at, step = 3, style, wordStyle }) => {
  const frame = useCurrentFrame();
  const words = text.split(" ");
  return (
    <div style={{ display: "flex", flexWrap: "wrap", columnGap: "0.24em", ...style }}>
      {words.map((w, i) => {
        const p = ramp(frame, [at + i * step, at + i * step + 12], [0, 1]);
        return (
          <span
            key={i}
            style={{
              display: "inline-block",
              opacity: p,
              translate: `0px ${(1 - p) * 0.5}em`,
              filter: `blur(${(1 - p) * 8}px)`,
              ...wordStyle?.(i, w),
            }}
          >
            {w}
          </span>
        );
      })}
    </div>
  );
};
