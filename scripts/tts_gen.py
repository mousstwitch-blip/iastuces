"""Generates one WAV per narration chunk with Kokoro TTS (French voice ff_siwis).

Usage: python3 scripts/tts_gen.py <kokoro_model_dir> scripts/narration.json <out_dir> 1.2
(model files: kokoro-v1.0.onnx + voices-v1.0.bin from github.com/thewh1teagle/kokoro-onnx releases)
"""
import sys, json, soundfile as sf, numpy as np
from kokoro_onnx import Kokoro
model_dir, script, out, speed = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])
k = Kokoro(model_dir+"/kokoro-v1.0.onnx", model_dir+"/voices-v1.0.bin")
data = json.load(open(script)); res=[]
for si,s in enumerate(data):
  for ci,(say,show) in enumerate(s["chunks"]):
    a, sr = k.create(say, voice="ff_siwis", speed=speed, lang="fr-fr")
    # trim leading/trailing silence
    thr = 0.01; idx = np.where(np.abs(a)>thr)[0]
    a = a[max(0,idx[0]-int(0.02*sr)):min(len(a),idx[-1]+int(0.06*sr))]
    fn=f"{out}/{si:02d}_{ci}.wav"; sf.write(fn,a,sr)
    res.append({"scene":s["scene"],"si":si,"ci":ci,"say":say,"show":show,"dur":len(a)/sr,"sr":sr})
json.dump(res,open(out+"/durations.json","w"),ensure_ascii=False,indent=1)
tot=sum(r["dur"] for r in res); print("speech total",round(tot,2))
for si in range(len(data)): print(data[si]["scene"], round(sum(r["dur"] for r in res if r["si"]==si),2))
