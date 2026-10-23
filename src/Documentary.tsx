import { Audio } from "@remotion/media";
import React from "react";
import { AbsoluteFill, Sequence, staticFile, useCurrentFrame } from "remotion";
import { Captions } from "./components/Captions";
import { FilmLook } from "./components/FilmLook";
import { SignalLoss } from "./components/SignalLoss";
import { ramp } from "./lib/anim";
import { S01Hook } from "./scenes/S01Hook";
import { S02Title } from "./scenes/S02Title";
import { S03Transponder } from "./scenes/S03Transponder";
import { S04Goodnight } from "./scenes/S04Goodnight";
import { S05Military } from "./scenes/S05Military";
import { S06Curvature } from "./scenes/S06Curvature";
import { S07Satellite } from "./scenes/S07Satellite";
import { S08Search } from "./scenes/S08Search";
import { S09Rule } from "./scenes/S09Rule";
import { S10End } from "./scenes/S10End";
import { C } from "./theme";
import { cues, scene } from "./timeline";

const FadeIn: React.FC<{ readonly frames: number; readonly children: React.ReactNode }> = ({ frames, children }) => {
  const frame = useCurrentFrame();
  return <AbsoluteFill style={{ opacity: ramp(frame, [0, frames], [0, 1]) }}>{children}</AbsoluteFill>;
};

const Flash: React.FC = () => {
  const frame = useCurrentFrame();
  return <AbsoluteFill style={{ backgroundColor: "#dfe9f5", opacity: ramp(frame, [0, 7], [0.85, 0]), mixBlendMode: "screen" }} />;
};

const hook = scene("hook");
const title = scene("title");
const transponder = scene("transponder");
const goodnight = scene("goodnight");
const military = scene("military");
const curvature = scene("curvature");
const satellite = scene("satellite");
const search = scene("search");
const rule = scene("rule");
const end = scene("end");

const HOOK_VANISH = cues("hook")[1].end + 6;
const XPDR_SILENT = goodnight.from + cues("goodnight")[2].end - 16;
const LAST_ECHO = military.from + cues("military")[2].end - 2;
const FADE = 10;
const WIPE = 16;

export const Documentary: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: C.night }}>
      <Sequence name="01 Accroche · radar" from={hook.from} durationInFrames={hook.durationInFrames}>
        <S01Hook vanishAt={HOOK_VANISH} />
      </Sequence>
      <Sequence name="02 Titre · globe" from={title.from} durationInFrames={title.durationInFrames} premountFor={60}>
        <S02Title />
      </Sequence>
      <Sequence name="03 Transpondeur" from={transponder.from} durationInFrames={transponder.durationInFrames} premountFor={60}>
        <S03Transponder />
      </Sequence>
      <Sequence name="04 Bonne nuit" from={goodnight.from} durationInFrames={goodnight.durationInFrames} premountFor={60}>
        <S04Goodnight />
      </Sequence>
      <Sequence name="05 Radar militaire" from={military.from} durationInFrames={military.durationInFrames} premountFor={60}>
        <S05Military />
      </Sequence>
      <Sequence name="06 Courbure" from={curvature.from} durationInFrames={curvature.durationInFrames} premountFor={60}>
        <S06Curvature />
      </Sequence>
      <Sequence name="07 Satellite" from={satellite.from} durationInFrames={satellite.durationInFrames} premountFor={60}>
        <S07Satellite />
      </Sequence>
      <Sequence name="08 Recherches" from={search.from - FADE} durationInFrames={search.durationInFrames + FADE} premountFor={60}>
        <FadeIn frames={FADE}>
          <S08Search />
        </FadeIn>
      </Sequence>
      <Sequence name="09 Règle OACI" from={rule.from - FADE} durationInFrames={rule.durationInFrames + FADE} premountFor={60}>
        <FadeIn frames={FADE}>
          <S09Rule />
        </FadeIn>
      </Sequence>
      <Sequence name="10 Fin · radar vide" from={end.from - WIPE} durationInFrames={end.durationInFrames + WIPE} premountFor={60}>
        <S10End wipeIn={WIPE} />
      </Sequence>

      <Sequence name="Perte de signal · accroche" from={hook.from + hook.durationInFrames - 16} durationInFrames={24}>
        <SignalLoss />
      </Sequence>
      <Sequence name="Flash · transpondeur" from={transponder.from} durationInFrames={8}>
        <Flash />
      </Sequence>
      <Sequence name="Perte de signal · XPDR" from={XPDR_SILENT} durationInFrames={14}>
        <SignalLoss intensity={0.8} />
      </Sequence>
      <Sequence name="Perte de signal · dernier écho" from={LAST_ECHO} durationInFrames={10}>
        <SignalLoss intensity={0.6} tint="99,255,180" />
      </Sequence>
      <Sequence name="Flash · satellite" from={satellite.from} durationInFrames={8}>
        <Flash />
      </Sequence>

      <Captions />
      <FilmLook />
      <Audio name="Mix (voix + musique + effets)" src={staticFile("audio/mix.wav")} />
    </AbsoluteFill>
  );
};
