"""Voix off française : Edge TTS (gratuit, horodatage mot à mot) ou Piper (hors-ligne)."""
from __future__ import annotations

import asyncio
import json
import logging
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

import numpy as np
import requests

from .config import ROOT, proxy
from .sound import SR, read_audio, write_wav

log = logging.getLogger("studio.tts")


class TTSError(RuntimeError):
    pass


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if c.isalnum())


def display_words(text: str) -> list[str]:
    """Mots affichés dans les sous-titres (ponctuation double rattachée au mot précédent)."""
    out: list[str] = []
    for tok in text.split():
        if out and not _norm(tok):  # « ? », « ! », « : », « — »
            if tok in "?!":
                out[-1] += " " + tok
            continue
        if out and re.fullmatch(r"\d{3}[.,;:!?…]?", tok) and re.fullmatch(r"\d{1,3}(\u202f\d{3})*", out[-1]):
            out[-1] += "\u202f" + tok  # « 1 279 » reste un seul mot à l'écran
            continue
        out.append(tok)
    return out


def align(words: list[str], bounds: list[dict], duration: float) -> list[dict]:
    """Associe chaque mot affiché aux horodatages renvoyés par le moteur vocal."""
    res, bi = [], 0
    for w in words:
        need = len(_norm(w)) or 1
        if bi >= len(bounds):
            res.append(None)
            continue
        start, acc, end = bounds[bi]["start"], 0, bounds[bi]["end"]
        while bi < len(bounds) and acc < need:
            acc += len(_norm(bounds[bi]["text"])) or 1
            end = bounds[bi]["end"]
            bi += 1
        res.append((start, end))
    if any(r is None for r in res) or not bounds:
        return proportional(words, duration)
    out = []
    for i, (w, (s, e)) in enumerate(zip(words, res)):
        nxt = res[i + 1][0] if i + 1 < len(res) else duration
        out.append({"text": w, "start": round(max(0.0, s), 3), "end": round(min(max(e, s + 0.08), max(nxt, s + 0.08)), 3)})
    return out


def proportional(words: list[str], duration: float) -> list[dict]:
    """Horodatage estimé au prorata de la longueur des mots (moteurs sans horodatage)."""
    weights = [len(_norm(w)) + 2 + (3 if re.search(r"[.,;:!?…]$", w) else 0) for w in words]
    total, t, out = float(sum(weights)) or 1.0, 0.0, []
    for w, wt in zip(words, weights):
        d = duration * wt / total
        out.append({"text": w, "start": round(t, 3), "end": round(t + d, 3)})
        t += d
    return out


def _trim(audio: np.ndarray, pad: float = 0.04) -> tuple[np.ndarray, float]:
    """Retire les silences de début et de fin ; renvoie aussi le décalage retiré."""
    mono = np.abs(audio).max(axis=1) if audio.ndim == 2 else np.abs(audio)
    idx = np.where(mono > 0.012)[0]
    if not len(idx):
        raise TTSError("audio vide")
    a = max(0, idx[0] - int(pad * SR))
    b = min(len(audio), idx[-1] + int(0.10 * SR))
    return audio[a:b], a / SR


def color(audio: np.ndarray, amount: float) -> np.ndarray:
    """Timbre documentaire : graves renforcés, présence, léger grain rauque (saturation douce)."""
    if amount <= 0:
        return audio
    from .sound import bp, lp

    y = audio + 1.0 * amount * lp(audio, 170) + 0.35 * amount * bp(audio, 1800, 3400)
    peak = np.abs(y).max() or 1.0
    drive = 1.0 + 2.2 * amount
    y = np.tanh(drive * y / peak) / np.tanh(drive)
    return (y * 0.9).astype(np.float32)


def prosody(cfg: dict, base_rate: str, base_pitch: str, section: str, last: bool) -> tuple[str, str]:
    """Vitesse et hauteur de la voix selon le moment de l'histoire."""
    table = cfg["tts"].get("prosody", {})
    dr, dp = table.get("final" if last else section, [0, 0])
    rate = int(re.sub(r"[^\d+-]", "", base_rate) or 0) + int(dr)
    pitch = int(re.sub(r"[^\d+-]", "", base_pitch) or 0) + int(dp)
    return f"{'+' if rate >= 0 else ''}{rate}%", f"{'+' if pitch >= 0 else ''}{pitch}Hz"


class Edge:
    name = "edge"

    def __init__(self, cfg: dict):
        self.cfg = cfg["tts"]

    def synth(self, text: str, out: Path, rate: str, pitch: str | None = None) -> tuple[float, list[dict]]:
        import edge_tts

        async def run() -> list[dict]:
            com = edge_tts.Communicate(text, self.cfg["edge_voice"], rate=rate, pitch=pitch or self.cfg.get("edge_pitch", "+0Hz"), proxy=proxy(), boundary="WordBoundary")
            bounds = []
            with open(out.with_suffix(".mp3"), "wb") as f:
                async for chunk in com.stream():
                    if chunk["type"] == "audio":
                        f.write(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        s = chunk["offset"] / 1e7
                        bounds.append({"text": chunk["text"], "start": s, "end": s + chunk["duration"] / 1e7})
            return bounds

        last: Exception | None = None
        for attempt in range(4):
            try:
                bounds = asyncio.run(run())
                audio = read_audio(out.with_suffix(".mp3"))
                audio, off = _trim(audio)
                write_wav(out, color(audio, float(self.cfg.get("voice_color", 0))))
                out.with_suffix(".mp3").unlink(missing_ok=True)
                dur = len(audio) / SR
                for b in bounds:
                    b["start"], b["end"] = b["start"] - off, b["end"] - off
                return dur, align(display_words(text), bounds, dur)
            except Exception as e:  # réseau, service saturé…
                last = e
                log.debug("edge-tts tentative %d : %s", attempt + 1, e)
                import time

                time.sleep(2 + 2 * attempt)
        raise TTSError(f"Edge TTS indisponible : {last}")


class Piper:
    """Voix neuronale hors-ligne (pip install piper-tts). Modèle téléchargé une fois depuis Hugging Face."""

    name = "piper"

    def __init__(self, cfg: dict):
        self.cfg = cfg["tts"]

    def _model(self) -> Path:
        voice = self.cfg["piper_voice"]  # ex. fr_FR-tom-medium
        dest = ROOT / "assets" / "models" / f"{voice}.onnx"
        if not dest.exists():
            lang, name, quality = voice.split("-")
            base = f"https://huggingface.co/rhasspy/piper-voices/resolve/main/{lang[:2]}/{lang}/{name}/{quality}/{voice}.onnx"
            dest.parent.mkdir(parents=True, exist_ok=True)
            for url, target in ((base, dest), (base + ".json", Path(str(dest) + ".json"))):
                r = requests.get(url, timeout=300)
                r.raise_for_status()
                target.write_bytes(r.content)
        return dest

    def synth(self, text: str, out: Path, rate: str, pitch: str | None = None) -> tuple[float, list[dict]]:
        try:
            model = self._model()
            pct = int(re.sub(r"[^\d+-]", "", rate) or 0)
            raw = out.with_suffix(".raw.wav")
            r = subprocess.run(
                [sys.executable, "-m", "piper", "-m", str(model), "-f", str(raw), "--length-scale", f"{1 / (1 + pct / 100):.3f}"],
                input=text, capture_output=True, text=True, timeout=300,
            )
            if r.returncode != 0 or not raw.exists():
                raise TTSError(r.stderr[-300:])
            audio, _ = _trim(read_audio(raw))
            raw.unlink(missing_ok=True)
            write_wav(out, color(audio, float(self.cfg.get("voice_color", 0))))
            dur = len(audio) / SR
            return dur, proportional(display_words(text), dur)
        except (requests.RequestException, subprocess.SubprocessError, OSError) as e:
            raise TTSError(f"Piper indisponible : {e}")


def get_engines(cfg: dict) -> list:
    wanted = cfg["tts"].get("provider", "auto")
    if wanted == "edge":
        return [Edge(cfg)]
    if wanted == "piper":
        return [Piper(cfg)]
    return [Edge(cfg), Piper(cfg)]


def shift_rate(rate: str, factor: float) -> str:
    """Multiplie la vitesse : "+10%" × 1.05 -> "+16%"."""
    pct = int(re.sub(r"[^\d+-]", "", rate) or 0)
    new = round(((1 + pct / 100) * factor - 1) * 100)
    return f"{'+' if new >= 0 else ''}{new}%"


def synthesize(cfg: dict, script: dict, out_dir: Path, rate: str | None = None) -> dict:
    """Une piste par scène -> voix.json : durées exactes et horodatage de chaque mot."""
    out_dir.mkdir(parents=True, exist_ok=True)
    rate = rate or cfg["tts"]["edge_rate"]
    engines = get_engines(cfg)
    scenes = []
    engine_used = None
    for k, s in enumerate(script["scenes"]):
        wav = out_dir / f"vo_{s['id']:02d}.wav"
        s_rate, s_pitch = prosody(cfg, rate, cfg["tts"].get("edge_pitch", "+0Hz"), s.get("section", ""), k == len(script["scenes"]) - 1)
        last: Exception | None = None
        for eng in engines if engine_used is None else [engine_used]:
            try:
                dur, words = eng.synth(s["narration"], wav, s_rate, s_pitch)
                engine_used = eng
                break
            except TTSError as e:
                last = e
                log.warning("  %s", e)
        else:
            raise TTSError(f"aucune voix disponible pour la scène {s['id']} : {last}")
        scenes.append({"id": s["id"], "file": str(wav), "duration": round(dur, 3), "words": words})
    info = {"engine": engine_used.name, "rate": rate, "scenes": scenes, "speech_total": round(sum(x["duration"] for x in scenes), 2)}
    (out_dir / "voix.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
    log.info("  voix %s (%s) : %.1f s de parole sur %d scènes", engine_used.name, rate, info["speech_total"], len(scenes))
    return info
