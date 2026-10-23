import { Composition, Folder } from "remotion";
import { Documentary } from "./Documentary";
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
import { TIMELINE, scene } from "./timeline";

const W = 1080;
const H = 1920;
const FPS = 30;

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition id="MH370" component={Documentary} durationInFrames={TIMELINE.durationInFrames} fps={FPS} width={W} height={H} />
      <Folder name="Scenes">
        <Composition id="S01-Hook" component={S01Hook} durationInFrames={scene("hook").durationInFrames} fps={FPS} width={W} height={H} defaultProps={{ vanishAt: 87 }} />
        <Composition id="S02-Title" component={S02Title} durationInFrames={scene("title").durationInFrames} fps={FPS} width={W} height={H} />
        <Composition id="S03-Transponder" component={S03Transponder} durationInFrames={scene("transponder").durationInFrames} fps={FPS} width={W} height={H} />
        <Composition id="S04-Goodnight" component={S04Goodnight} durationInFrames={scene("goodnight").durationInFrames} fps={FPS} width={W} height={H} />
        <Composition id="S05-Military" component={S05Military} durationInFrames={scene("military").durationInFrames} fps={FPS} width={W} height={H} />
        <Composition id="S06-Curvature" component={S06Curvature} durationInFrames={scene("curvature").durationInFrames} fps={FPS} width={W} height={H} />
        <Composition id="S07-Satellite" component={S07Satellite} durationInFrames={scene("satellite").durationInFrames} fps={FPS} width={W} height={H} />
        <Composition id="S08-Search" component={S08Search} durationInFrames={scene("search").durationInFrames} fps={FPS} width={W} height={H} />
        <Composition id="S09-Rule" component={S09Rule} durationInFrames={scene("rule").durationInFrames} fps={FPS} width={W} height={H} />
        <Composition id="S10-End" component={S10End} durationInFrames={scene("end").durationInFrames} fps={FPS} width={W} height={H} defaultProps={{ wipeIn: 0 }} />
      </Folder>
    </>
  );
};
