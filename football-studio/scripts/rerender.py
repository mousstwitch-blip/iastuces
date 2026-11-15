#!/usr/bin/env python3
"""Refait uniquement le montage + l'inspection d'un projet existant (sans appel à l'IA).

Usage : python scripts/rerender.py <dossier de projects/> [--regen 3,4,6]
  Photos perso : dépose photos/<projet>/scene_XX.jpg (XX = numéro de scène) puis relance ce script.
  --regen : régénère d'abord les images de ces scènes (prompts de script.json, contrôle visuel IA si disponible).
"""
import json, shutil, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from studio import config, qc, render

cfg = config.load_config()
config.setup_logging()
slug = sys.argv[1]
proj = config.DIRS["projects"] / slug
if "--regen" in sys.argv:
    from studio import pipeline
    from studio.llm import get_llm

    ids = [int(x) for x in sys.argv[sys.argv.index("--regen") + 1].split(",")]
    script = json.loads((proj / "script.json").read_text())
    pipeline.step_images(cfg, get_llm(cfg), script, pipeline.Project(slug), only={i: "" for i in ids})
    (proj / "script.json").write_text(json.dumps(script, ensure_ascii=False, indent=1))
# Emplacements photo : photos/<projet>/scene_XX.jpg|png|webp remplacent l'image IA de la scène
user_dir = config.ROOT / "photos" / slug
photos = set()
if user_dir.exists():
    from PIL import Image
    from studio import images

    for f in sorted(user_dir.glob("scene_*.*")):
        if f.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
            continue
        sid = int(f.stem.split("_")[1])
        dest = config.DIRS["images"] / slug / f"scene_{sid:02d}.jpg"
        images._fit(Image.open(f)).save(dest, quality=95)
        if images.depth_available():
            images.depth_map(dest, dest.with_name(f"scene_{sid:02d}_depth.png"))
        print(f"photo perso : scène {sid} <- {f.name}")
        photos.add(sid)
tl = json.loads((proj / "timeline.json").read_text())
for sc in tl["scenes"]:
    sc["photo"] = sc["id"] in photos
video = render.render_video(tl, cfg, config.DIRS["audio"] / slug / "mix.wav", proj / "montage_manual.mp4", proj)
rep = qc.inspect(video, tl, cfg, proj, None, None, "manual")
final = config.DIRS["videos"] / f"{slug}.mp4"
shutil.move(video, final)
print(json.dumps({k: rep["metrics"].get(k) for k in ("width", "height", "fps", "duration", "lufs", "size_mb", "captions_missing")}))
print("problèmes :", rep["issues"] or "aucun")
print("vidéo :", final)
