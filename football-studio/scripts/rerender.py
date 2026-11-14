#!/usr/bin/env python3
"""Refait uniquement le montage + l'inspection d'un projet existant (sans appel à l'IA).

Usage : python scripts/rerender.py <dossier de projects/>
"""
import json, shutil, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from studio import config, qc, render

cfg = config.load_config()
config.setup_logging()
slug = sys.argv[1]
proj = config.DIRS["projects"] / slug
tl = json.loads((proj / "timeline.json").read_text())
video = render.render_video(tl, cfg, config.DIRS["audio"] / slug / "mix.wav", proj / "montage_manual.mp4", proj)
rep = qc.inspect(video, tl, cfg, proj, None, None, "manual")
final = config.DIRS["videos"] / f"{slug}.mp4"
shutil.move(video, final)
print(json.dumps({k: rep["metrics"].get(k) for k in ("width", "height", "fps", "duration", "lufs", "size_mb", "captions_missing")}))
print("problèmes :", rep["issues"] or "aucun")
print("vidéo :", final)
