"""Contrôles qualité n°3 et n°4 : inspection réelle du MP4 exporté.

Tout ce qui est rapporté ici est mesuré sur le fichier final (ffprobe, filtres d'analyse
FFmpeg, images extraites) — rien n'est supposé à partir de la configuration.
"""
from __future__ import annotations

import json
import logging
import re
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

from .llm import LLM, LLMError
from .render import caption_groups, font, hex_rgb, prepare_words
from .research import prompt as tpl

log = logging.getLogger("studio.qc")


def probe(video: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(video)], capture_output=True, text=True)
    if r.returncode != 0:
        return {"readable": False, "error": r.stderr[-300:]}
    data = json.loads(r.stdout)
    v = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in data["streams"] if s["codec_type"] == "audio"), None)
    out = {"readable": v is not None, "duration": float(data["format"].get("duration", 0)), "size_mb": round(int(data["format"].get("size", 0)) / 1e6, 2), "bitrate_kbps": int(data["format"].get("bit_rate", 0)) // 1000}
    if v:
        num, den = v["r_frame_rate"].split("/")
        out.update(width=v["width"], height=v["height"], fps=round(int(num) / int(den), 3), vcodec=v["codec_name"], pix_fmt=v.get("pix_fmt"), video_duration=float(v.get("duration", out["duration"])), frames=int(v.get("nb_frames", 0)))
    if a:
        out.update(acodec=a["codec_name"], sample_rate=int(a["sample_rate"]), channels=a["channels"], audio_duration=float(a.get("duration", out["duration"])))
    return out


def _analyse(video: Path) -> dict:
    """Une seule passe FFmpeg : écrans noirs, images figées, silences, loudness, décodage complet."""
    r = subprocess.run(
        ["ffmpeg", "-v", "info", "-nostats", "-i", str(video),
         "-vf", "blackdetect=d=0.15:pic_th=0.97:pix_th=0.09,freezedetect=n=-55dB:d=1.5",
         "-af", "silencedetect=noise=-45dB:d=1.2,ebur128=peak=true", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    err = r.stderr
    black = [(float(a), float(b)) for a, b in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", err)]
    freeze = [(float(a), float(b)) for a, b in zip(re.findall(r"freeze_start: ([\d.]+)", err), re.findall(r"freeze_end: ([\d.]+)", err))]
    silence = [(float(a), float(b)) for a, b in zip(re.findall(r"silence_start: ([\d.]+)", err), re.findall(r"silence_end: ([\d.]+)", err))]
    summary = err[err.rfind("Summary:") :] if "Summary:" in err else ""
    lufs = re.search(r"I:\s+(-?[\d.]+) LUFS", summary)
    peak = re.search(r"Peak:\s+(-?[\d.]+) dBFS", summary)
    decode_errors = [ln for ln in err.splitlines() if re.search(r"(?i)error|corrupt|invalid", ln) and "silencedetect" not in ln]
    return {"decodes": r.returncode == 0, "decode_errors": decode_errors[:5], "black": black, "freeze": freeze, "silence": silence,
            "lufs": float(lufs.group(1)) if lufs else None, "true_peak": float(peak.group(1)) if peak else None}


def grab(video: Path, t: float) -> np.ndarray | None:
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0, t):.3f}", "-i", str(video), "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True)
    if r.returncode != 0 or not r.stdout:
        return None
    img = cv2.imdecode(np.frombuffer(r.stdout, np.uint8), cv2.IMREAD_COLOR)
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB) if img is not None else None


def caption_visible(frame: np.ndarray, cfg: dict) -> bool:
    """Vérifie dans l'image exportée la présence d'un texte clair cerné de noir dans la zone des sous-titres."""
    H, W = frame.shape[:2]
    cy = int(H * cfg["captions"]["y_ratio"])
    roi = frame[max(0, cy - 150) : cy + 150, 60 : W - 60].astype(np.int16)
    colours = [hex_rgb(cfg["captions"][k]) for k in ("color", "active_color", "keyword_color")]
    text = np.zeros(roi.shape[:2], bool)
    for c in colours:
        text |= np.abs(roi - np.array(c)).max(axis=2) < 40
    dark = roi.max(axis=2) < 28
    # le contour noir doit jouxter le texte clair
    near = cv2.dilate(dark.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    return (text & near).mean() > 0.008


def control_times(timeline: dict, count: int) -> list[float]:
    times = [0.05, 1.0]
    for sc in timeline["scenes"]:
        times.append((sc["start"] + sc["end"]) / 2)
    times.append(timeline["duration"] - 0.5)
    times = sorted(set(round(t, 2) for t in times))
    while len(times) > max(count, len(timeline["scenes"]) + 2):
        times.pop(len(times) // 2)
    return times


def contact_sheet(frames: list[tuple[float, np.ndarray]], out: Path, cols: int = 5) -> Path:
    tw, th = 270, 480
    rows = -(-len(frames) // cols)
    sheet = Image.new("RGB", (cols * (tw + 8) + 8, rows * (th + 44) + 8), (18, 18, 22))
    d = ImageDraw.Draw(sheet)
    f = font("montserrat-800.ttf", 24)
    for i, (t, fr) in enumerate(frames):
        x, y = 8 + (i % cols) * (tw + 8), 8 + (i // cols) * (th + 44)
        sheet.paste(Image.fromarray(fr).resize((tw, th), Image.LANCZOS), (x, y))
        d.text((x + 4, y + th + 6), f"{t:05.2f} s", font=f, fill=(255, 214, 10))
    sheet.save(out, quality=90)
    return out


def inspect(video: Path, timeline: dict, cfg: dict, workdir: Path, mix_stats: dict | None, llm: LLM | None, tag: str) -> dict:
    """Inspecte la vidéo exportée et renvoie un rapport {metrics, issues, ok}."""
    vc = cfg["video"]
    issues: list[dict] = []

    def add(typ, severity, detail, scene=None, time=None):
        issues.append({"type": typ, "severity": severity, "detail": detail, "scene": scene, "time": time})

    def scene_at(t: float):
        return next((s["id"] for s in timeline["scenes"] if s["start"] <= t < s["end"]), timeline["scenes"][-1]["id"])

    info = probe(video)
    if not info.get("readable"):
        add("format", "bloquant", f"fichier illisible : {info.get('error', 'pas de flux vidéo')}")
        return {"metrics": info, "issues": issues, "ok": False}
    if (info["width"], info["height"]) != (vc["width"], vc["height"]):
        add("format", "bloquant", f"résolution {info['width']}×{info['height']} au lieu de {vc['width']}×{vc['height']}")
    if info["fps"] < 30 or abs(info["fps"] - vc["fps"]) > 0.01:
        add("format", "bloquant", f"{info['fps']} images/s au lieu de {vc['fps']}")
    if info.get("vcodec") != "h264" or info.get("pix_fmt") != "yuv420p":
        add("format", "bloquant", f"codec {info.get('vcodec')}/{info.get('pix_fmt')} (attendu h264/yuv420p)")
    if "acodec" not in info:
        add("audio", "bloquant", "aucune piste audio")
    elif abs(info["audio_duration"] - info["video_duration"]) > 0.25:
        add("audio", "bloquant", f"audio ({info['audio_duration']:.2f} s) et vidéo ({info['video_duration']:.2f} s) de durées différentes")
    if not vc["min_duration"] <= info["duration"] <= vc["max_duration"]:
        add("duree", "bloquant", f"durée {info['duration']:.1f} s hors de la plage {vc['min_duration']:.0f}-{vc['max_duration']:.0f} s")

    an = _analyse(video)
    if not an["decodes"] or an["decode_errors"]:
        add("format", "bloquant", "erreurs de décodage : " + "; ".join(an["decode_errors"])[:200])
    for a, b in an["black"]:
        add("noir", "bloquant", f"écran noir de {a:.2f} à {b:.2f} s", scene_at(a), a)
    for a, b in an["freeze"]:
        add("fige", "bloquant", f"image figée de {a:.2f} à {b:.2f} s", scene_at(a), a)
    for a, b in an["silence"]:
        add("audio", "bloquant", f"silence complet de {a:.2f} à {b:.2f} s", scene_at(a), a)
    target = cfg["audio"]["target_lufs"]
    if an["lufs"] is None:
        add("audio", "bloquant", "niveau sonore non mesurable (piste muette ?)")
    elif abs(an["lufs"] - target) > 2.0:
        add("loudness", "bloquant", f"niveau {an['lufs']} LUFS (cible {target})")
    if an["true_peak"] is not None and an["true_peak"] > -0.3:
        add("loudness", "mineur", f"crête à {an['true_peak']} dBFS (risque de saturation)")
    if mix_stats and mix_stats.get("voice_to_music_db") is not None and mix_stats["voice_to_music_db"] < 9:
        add("voix_couverte", "bloquant", f"la voix ne dépasse la musique que de {mix_stats['voice_to_music_db']} dB")

    # images de contrôle réellement extraites du MP4
    frames = []
    for t in control_times(timeline, int(cfg["qc"]["control_frames"])):
        fr = grab(video, t)
        if fr is None:
            add("format", "bloquant", f"image impossible à extraire à {t:.2f} s", scene_at(t), t)
            continue
        frames.append((t, fr))
        lum = cv2.cvtColor(fr, cv2.COLOR_RGB2GRAY)
        if lum.mean() < 14:
            add("noir", "bloquant", f"image très sombre à {t:.2f} s (luminance {lum.mean():.0f})", scene_at(t), t)
        elif lum.std() < 9:
            add("defaut_image", "bloquant", f"image uniforme à {t:.2f} s", scene_at(t), t)
    if frames and frames[0][1].mean() < 30:
        add("noir", "bloquant", "la vidéo ne démarre pas sur une image forte", 1, 0.05)

    # sous-titres : présence vérifiée au milieu de chaque groupe (échantillon)
    groups = caption_groups(prepare_words(timeline), int(cfg["captions"]["max_words"]))
    sample = groups[:: max(1, len(groups) // 10)]
    missing = []
    for g in sample:
        t = (g["start"] + g["end"]) / 2
        fr = grab(video, t)
        if fr is not None and not caption_visible(fr, cfg):
            missing.append(round(t, 2))
    if len(missing) > max(1, len(sample) // 4):
        add("sous_titres", "bloquant", f"sous-titres non détectés à {missing}")

    sheet = contact_sheet(frames, workdir / f"planche_contact_{tag}.jpg") if frames else None
    metrics = dict(info, lufs=an["lufs"], true_peak=an["true_peak"], captions_checked=len(sample), captions_missing=missing,
                   control_frames=[t for t, _ in frames], contact_sheet=str(sheet) if sheet else None, mix=mix_stats)

    if sheet and cfg["qc"].get("vision_check") and llm is not None and llm.vision:
        desc = "\n".join(f"- scène {s['id']} ({s['start']:.1f}-{s['end']:.1f} s, {s['type']}) : « {s['narration']} »" for s in timeline["scenes"])
        try:
            review = llm.json(tpl("final_check", scenes=desc), images=[sheet])
            metrics["vision_score"] = review.get("score")
            for i in review.get("issues", []):
                sev = "bloquant" if i.get("severity") == "bloquant" else "mineur"
                add(str(i.get("type", "autre")), sev, "[revue IA] " + str(i.get("problem", "")), i.get("scene"), i.get("time"))
        except LLMError as e:
            metrics["vision_error"] = str(e)[:200]
            log.warning("  revue visuelle IA indisponible : %s", e)

    ok = not any(i["severity"] == "bloquant" for i in issues)
    return {"metrics": metrics, "issues": issues, "ok": ok}
