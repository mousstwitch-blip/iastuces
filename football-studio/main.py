#!/usr/bin/env python3
"""FOOTBALL STUDIO — une commande, une vidéo verticale de 60 s prête à publier.

    python main.py                                   sujet trouvé automatiquement
    python main.py --topic "La chute incroyable de Manchester United"
    python main.py --category "transferts historiques"
    python main.py --resume 20261114-mon-projet      reprend un projet interrompu
    python main.py --check                           vérifie l'installation
"""
from __future__ import annotations

import argparse
import datetime as dt
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def normalise_argv(argv: list[str]) -> list[str]:
    """Tolère les tirets et guillemets typographiques (–topic “…”) collés depuis un téléphone."""
    out = []
    for a in argv:
        if a[:1] in "–—" and len(a) > 1:
            a = "--" + a.lstrip("–—-")
        out.append(a.strip("“”«»").strip())
    return out


def check(cfg: dict) -> int:
    from studio import images, llm, tts
    from studio.config import have, proxy, secret

    ok = True

    def line(label: str, good: bool, detail: str = "", required: bool = True) -> None:
        nonlocal ok
        ok = ok and (good or not required)
        print(f"  {'✔' if good else ('✗' if required else '–')} {label:<34} {detail}")

    print("Outils")
    line("Python ≥ 3.11", sys.version_info >= (3, 11), sys.version.split()[0])
    line("ffmpeg", have("ffmpeg"))
    line("ffprobe", have("ffprobe"))
    for mod in ("numpy", "scipy", "cv2", "PIL", "requests", "edge_tts", "onnxruntime"):
        try:
            __import__(mod)
            line(f"module {mod}", True)
        except ImportError:
            line(f"module {mod}", False, "pip install -r requirements.txt", required=mod != "onnxruntime")
    print("Modèle de langage")
    for name, cls in llm.PROVIDERS.items():
        line(name, cls.available(), "" if cls.available() else "non configuré", required=False)
    try:
        print("   → utilisé :", llm.get_llm(cfg).name)
    except llm.LLMError as e:
        line("fournisseur LLM", False, str(e))
    print("Images")
    line("OpenAI images (payant)", secret("OPENAI_API_KEY") is not None, "" if secret("OPENAI_API_KEY") else "pas de clé (facultatif)", required=False)
    print("   → utilisé :", images.get_provider(cfg).name)
    line("modèle de profondeur (parallaxe)", images.DEPTH_MODEL.exists(), "" if images.DEPTH_MODEL.exists() else "téléchargé au premier lancement", required=False)
    print("Voix")
    print("   → moteurs :", ", ".join(e.name for e in tts.get_engines(cfg)))
    print("Réseau")
    print("   proxy HTTPS :", "oui" if proxy() else "non")
    print("\nInstallation", "prête." if ok else "incomplète.")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--topic", "-t", help="sujet imposé (« Et si… ? » active le mode uchronie)")
    ap.add_argument("--notes", "-n", help="indications du réalisateur : hook, scènes, fin souhaitées")
    ap.add_argument("--category", "-c", help="catégorie pour la recherche automatique de sujet")
    ap.add_argument("--resume", "-r", help="nom d'un dossier de projects/ à reprendre")
    ap.add_argument("--provider", help="force le fournisseur LLM (claude_cli, anthropic, openai, pollinations)")
    ap.add_argument("--no-vision", action="store_true", help="désactive les contrôles visuels par IA")
    ap.add_argument("--check", action="store_true", help="vérifie l'installation et quitte")
    ap.add_argument("--verbose", "-v", action="store_true")
    args = ap.parse_args(normalise_argv(sys.argv[1:]))

    if not shutil.which("ffmpeg"):
        print("ffmpeg est introuvable : installe-le (https://ffmpeg.org/download.html) puis relance.", file=sys.stderr)
        return 2
    from studio import pipeline
    from studio.config import DIRS, load_config, setup_logging

    cfg = load_config()
    if args.provider:
        cfg["llm"]["provider"] = args.provider
    if args.no_vision:
        cfg["images"]["vision_check"] = cfg["qc"]["vision_check"] = False
    if args.check:
        return check(cfg)
    setup_logging(DIRS["logs"] / f"{dt.datetime.now():%Y%m%d-%H%M%S}.log", args.verbose)
    try:
        pipeline.run(cfg, topic=args.topic, category=args.category, resume=args.resume, notes=args.notes)
    except KeyboardInterrupt:
        print("\nInterrompu. Reprends avec : python main.py --resume <dossier du projet>")
        return 130
    except Exception as e:  # message clair pour l'utilisateur, détail complet dans logs/
        import logging

        logging.getLogger("studio").debug("erreur fatale", exc_info=True)
        logging.getLogger("studio").error("✗ Échec : %s (détails dans logs/)", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
