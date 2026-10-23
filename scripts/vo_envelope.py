"""Per-frame (30 fps) RMS envelope of the voice-over, 8 sub-bins per frame, for waveform visuals."""
import json, os, numpy as np, soundfile as sf
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
a, sr = sf.read(os.path.join(root, "public/audio/vo.wav"), dtype="float32")
hop = sr // 240
n = len(a) // hop
rms = np.sqrt(np.mean(a[: n * hop].reshape(n, hop) ** 2, axis=1))
rms = rms / (rms.max() + 1e-9)
json.dump([round(float(x), 3) for x in rms], open(os.path.join(root, "src/data/vo-envelope.json"), "w"))
print(n, "bins")
