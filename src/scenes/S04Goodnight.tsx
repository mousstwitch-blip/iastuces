import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import envelope from "../data/vo-envelope.json";
import { Kicker, Reveal } from "../components/Type";
import { easeInOut, ramp, rand } from "../lib/anim";
import { cues, scene } from "../timeline";
import { C, display, mono } from "../theme";

const QUOTE = ["Good", "night", "Malaysian", "three", "seven", "zero."];

const pad = (n: number) => String(n).padStart(2, "0");
const clock = (s: number) => `${pad(Math.floor(s / 3600))}:${pad(Math.floor((s % 3600) / 60))}:${pad(Math.floor(s % 60))}`;

/** 0:16 — the last radio words, then the transponder goes silent at 01:21. */
export const S04Goodnight: React.FC = () => {
  const frame = useCurrentFrame();
  const [, c1, c2] = cues("goodnight");
  const from = scene("goodnight").from;

  // 01:19:29 → fast-forward to 01:21:13 while "deux minutes plus tard" is spoken
  const t0 = 1 * 3600 + 19 * 60 + 29;
  const t1 = 1 * 3600 + 21 * 60 + 13;
  const ff = ramp(frame, [c2.at + 2, c2.at + 34], [0, 1], easeInOut);
  const secs = t0 + frame / 30 + ff * (t1 - t0 - 4);
  const silentAt = c2.end - 16;
  const silent = frame >= silentAt;
  const flicker = frame >= silentAt && frame < silentAt + 10 && rand(frame) > 0.5;

  const bars = 64;
  const center = (from + frame) * 8;
  const radio = frame >= c1.at - 4 && frame <= c1.end + 4 ? 1 : 0.18;

  return (
    <AbsoluteFill style={{ backgroundColor: "#04070c", overflow: "hidden" }}>
      {/* out-of-focus cockpit instruments */}
      {Array.from({ length: 16 }, (_, i) => {
        const hue = [C.amber, "#5ad1ff", C.phosphor, "#ff6a3d"][i % 4];
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: rand(i * 3) * 1180 - 100,
              top: 1200 + rand(i * 5) * 700 - frame * 0.25,
              width: 80 + rand(i * 7) * 220,
              height: 80 + rand(i * 7) * 220,
              borderRadius: "50%",
              background: hue,
              opacity: (silent && i % 4 === 2 ? 0.02 : 0.1) + rand(i * 11) * 0.12,
              filter: "blur(40px)",
            }}
          />
        );
      })}

      <AbsoluteFill style={{ padding: "236px 80px 0 80px" }}>
        <Reveal at={0}>
          <Kicker>8 mars 2014 · heure de Malaisie</Kicker>
        </Reveal>
        <Reveal at={2}>
          <div
            style={{
              fontFamily: mono,
              fontWeight: 700,
              fontSize: 148,
              letterSpacing: "-0.02em",
              color: silent ? C.red : C.paper,
              marginTop: 8,
              filter: ff > 0 && ff < 1 ? "blur(2px)" : undefined,
            }}
          >
            {clock(secs)}
          </div>
        </Reveal>

        <Reveal at={c1.at - 10} style={{ marginTop: 120 }}>
          <Kicker color={C.amber} size={26}>
            Dernier message radio du vol
          </Kicker>
          <div
            style={{
              marginTop: 18,
              display: "flex",
              flexWrap: "wrap",
              columnGap: "0.25em",
              fontFamily: display,
              fontWeight: 800,
              fontSize: 92,
              lineHeight: 1.02,
              letterSpacing: "-0.03em",
            }}
          >
            {QUOTE.map((w, i) => {
              const at = c1.at + (i / QUOTE.length) * c1.dur;
              const p = ramp(frame, [at - 2, at + 5], [0, 1]);
              return (
                <span key={i} style={{ color: p > 0.5 ? C.paper : "rgba(238,242,246,0.18)" }}>
                  {i === 0 ? "“" : ""}
                  {w}
                  {i === QUOTE.length - 1 ? "”" : ""}
                </span>
              );
            })}
          </div>
        </Reveal>

        <svg width="920" height="140" style={{ marginTop: 34, opacity: radio }}>
          {Array.from({ length: bars }, (_, i) => {
            const idx = Math.max(0, Math.min(envelope.length - 1, center - (bars - i) * 2));
            const v = silent ? 0.02 : (envelope[idx] ?? 0) * radio + 0.03;
            const h = 6 + v * 120;
            return <rect key={i} x={i * 14.4} y={70 - h / 2} width={7} height={h} rx={3.5} fill={C.steel} />;
          })}
        </svg>

        <Reveal at={c2.at} style={{ marginTop: 40 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 26,
              padding: "22px 28px",
              border: `2px solid ${silent ? C.red : "rgba(159,180,199,0.35)"}`,
              background: "rgba(5,10,18,0.6)",
              width: 860,
              opacity: flicker ? 0.3 : 1,
            }}
          >
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: 14,
                background: silent ? C.red : C.phosphor,
                boxShadow: `0 0 24px ${silent ? C.red : C.phosphor}`,
              }}
            />
            <div style={{ fontFamily: mono, fontSize: 32, color: C.paper, letterSpacing: "0.1em" }}>TRANSPONDEUR</div>
            <div style={{ marginLeft: "auto", fontFamily: mono, fontWeight: 700, fontSize: 32, color: silent ? C.red : C.phosphor }}>
              {silent ? "— — — —" : "MAS370 · 350"}
            </div>
          </div>
        </Reveal>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
