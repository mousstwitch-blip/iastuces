import React from "react";
import { C, mono } from "../theme";

/** A DOM label pinned to a projected globe point. */
export const GlobeLabel: React.FC<{
  readonly x: number;
  readonly y: number;
  readonly text: string;
  readonly sub?: string;
  readonly color?: string;
  readonly side?: "left" | "right";
  readonly opacity?: number;
}> = ({ x, y, text, sub, color = C.paper, side = "right", opacity = 1 }) => (
  <div
    style={{
      position: "absolute",
      left: side === "right" ? x + 26 : undefined,
      right: side === "left" ? 1080 - x + 26 : undefined,
      top: y - 22,
      opacity,
      fontFamily: mono,
      textAlign: side === "right" ? "left" : "right",
      textShadow: "0 2px 10px rgba(0,0,0,0.9)",
      whiteSpace: "nowrap",
    }}
  >
    <div style={{ fontSize: 30, fontWeight: 700, color, letterSpacing: "0.06em" }}>{text}</div>
    {sub ? <div style={{ fontSize: 22, color: C.steel, letterSpacing: "0.1em", marginTop: 2 }}>{sub}</div> : null}
  </div>
);
