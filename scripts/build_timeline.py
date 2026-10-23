"""Place the voice-over chunks on a 60 s timeline and write src/data/timeline.json.

Usage: python3 scripts/build_timeline.py <vo_dir_with_durations.json>
"""
import json, sys, shutil, os
import numpy as np, soundfile as sf

FPS, TOTAL = 30, 60.0
vo_dir = sys.argv[1]
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
chunks = json.load(open(os.path.join(vo_dir, "durations.json")))

START = 0.25
INTRA = 0.12
SCENE_GAP = 0.32
SPECIAL_AFTER = {  # extra silence after a given (scene index, chunk index)
    (0, 0): 0.12,   # "Ce point..." -> "Regardez bien."
    (0, 1): 0.95,   # the blip vanishes in silence
    (1, 2): 0.10,
    (3, 1): 0.40,   # static after "Bonne nuit..."
    (4, 2): 0.10,
    (7, 2): 0.05,
}
LEAD = 0.22  # visual cut happens slightly before the voice (J-cut)

t = START
placed = []
for i, c in enumerate(chunks):
    placed.append({**c, "start": round(t, 3)})
    t += c["dur"]
    nxt = chunks[i + 1] if i + 1 < len(chunks) else None
    if nxt is None:
        break
    gap = SCENE_GAP if nxt["si"] != c["si"] else INTRA
    gap += SPECIAL_AFTER.get((c["si"], c["ci"]), 0)
    t += gap
speech_end = t
tail = TOTAL - speech_end
print(f"speech ends at {speech_end:.2f}s, tail {tail:.2f}s")
assert tail >= 1.6, "voice-over too long for 60 s"

scenes = []
n_scenes = max(c["si"] for c in chunks) + 1
for si in range(n_scenes):
    first = next(c for c in placed if c["si"] == si)
    start = 0.0 if si == 0 else first["start"] - LEAD
    scenes.append({"id": first["scene"], "from": round(start * FPS)})
for i, s in enumerate(scenes):
    end = scenes[i + 1]["from"] if i + 1 < len(scenes) else int(TOTAL * FPS)
    s["durationInFrames"] = end - s["from"]

# assemble the full voice-over track
sr = chunks[0]["sr"]
track = np.zeros(int(TOTAL * sr), dtype=np.float32)
for c in placed:
    a, _ = sf.read(os.path.join(vo_dir, f"{c['si']:02d}_{c['ci']}.wav"), dtype="float32")
    s0 = int(c["start"] * sr)
    track[s0:s0 + len(a)] += a[: len(track) - s0]
sf.write(os.path.join(root, "public/audio/vo.wav"), track, sr)

captions = [
    {"scene": c["scene"], "text": c["show"],
     "from": round(c["start"] * FPS), "durationInFrames": round(c["dur"] * FPS)}
    for c in placed
]
json.dump({"fps": FPS, "durationInFrames": int(TOTAL * FPS), "scenes": scenes, "captions": captions},
          open(os.path.join(root, "src/data/timeline.json"), "w"), ensure_ascii=False, indent=1)
for s in scenes:
    print(f"{s['id']:12s} {s['from']/FPS:6.2f}s -> {(s['from']+s['durationInFrames'])/FPS:6.2f}s")
for c in captions:
    print(f"  {c['from']/FPS:6.2f}-{(c['from']+c['durationInFrames'])/FPS:6.2f} {c['text']}")
