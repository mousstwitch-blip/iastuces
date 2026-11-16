"""Audio : lecture/écriture, musique originale synthétisée, bruitages, mixage et normalisation.

Toute la musique et tous les effets sont générés ici à partir de formes d'onde :
aucun échantillon tiers, donc aucun droit à acquitter.
"""
from __future__ import annotations

import json
import logging
import re
import subprocess
import wave
from pathlib import Path

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

log = logging.getLogger("studio.sound")
SR = 48000


# ───────────────────────────── E/S ─────────────────────────────
def read_audio(path: Path) -> np.ndarray:
    """Décode n'importe quel fichier audio en float32 stéréo 48 kHz."""
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"], capture_output=True, check=True
    )
    return np.frombuffer(r.stdout, np.float32).reshape(-1, 2).copy()


def write_wav(path: Path, audio: np.ndarray) -> None:
    if audio.ndim == 1:
        audio = np.stack([audio, audio], 1)
    pcm = (np.clip(audio, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


# ───────────────────────────── Briques de synthèse ─────────────────────────────
def _filt(x, kind, f, order=2):
    return sosfilt(butter(order, f, kind, fs=SR, output="sos"), x, axis=0)


def lp(x, f, order=2):
    return _filt(x, "low", min(f, SR / 2 - 100), order)


def hp(x, f, order=2):
    return _filt(x, "high", f, order)


def bp(x, lo, hi, order=2):
    return _filt(x, "band", [lo, min(hi, SR / 2 - 100)], order)


def hz(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def tt(dur: float) -> np.ndarray:
    return np.arange(int(dur * SR)) / SR


def saw(f: float, t: np.ndarray, phase: float = 0.0) -> np.ndarray:
    return 2 * ((t * f + phase) % 1.0) - 1


def place(buf: np.ndarray, start: float, sig: np.ndarray, gain: float = 1.0, pan: float = 0.0) -> None:
    """Ajoute un signal mono dans un tampon stéréo (pan -1 gauche … +1 droite)."""
    i = int(start * SR)
    if i >= len(buf) or i + len(sig) <= 0:
        return
    if i < 0:
        sig, i = sig[-i:], 0
    sig = sig[: len(buf) - i]
    l, r = np.sqrt((1 - pan) / 2) * 1.414, np.sqrt((1 + pan) / 2) * 1.414
    buf[i : i + len(sig), 0] += sig * gain * l
    buf[i : i + len(sig), 1] += sig * gain * r


def reverb(x: np.ndarray, seconds: float, wet: float, rng) -> np.ndarray:
    n = int(seconds * SR)
    env = np.exp(-np.linspace(0, 6.5, n))
    out = x.copy()
    for ch in range(2):
        ir = lp(rng.standard_normal(n) * env, 6000)
        ir /= np.sqrt((ir**2).sum())
        out[:, ch] += wet * fftconvolve(x[:, ch], ir)[: len(x)]
    return out


def curve(points: list[tuple[float, float]], n: int) -> np.ndarray:
    """Courbe linéaire par morceaux échantillonnée à SR."""
    xs, ys = zip(*sorted(points))
    return np.interp(np.arange(n) / SR, xs, ys).astype(np.float32)


# ───────────────────────────── Bruitages ─────────────────────────────
def sfx_impact(rng, power: float = 1.0) -> np.ndarray:
    t = tt(2.6)
    sub = np.sin(2 * np.pi * np.cumsum(28 + 50 * np.exp(-t * 9)) / SR) * np.exp(-t * 2.2)
    crash = lp(rng.standard_normal(len(t)), 2400) * np.exp(-t * 3.5) * 0.5
    thump = lp(rng.standard_normal(len(t)), 180) * np.exp(-t * 14) * 1.4
    return np.tanh((sub + crash + thump) * 1.4 * power) * 0.9


def sfx_whoosh(rng, dur: float = 0.55, rising: bool = False) -> np.ndarray:
    n = int(dur * SR)
    noise = rng.standard_normal(n)
    out = np.zeros(n)
    k = np.linspace(0, 1, n)
    centre = 500 + 3500 * (k if rising else np.sin(np.pi * k) ** 2)
    # filtre balayé approché par 6 bandes fixes pondérées
    for fc in (400, 800, 1400, 2200, 3200, 4500):
        w = np.exp(-(((centre - fc) / (fc * 0.55)) ** 2))
        out += bp(noise, fc * 0.7, fc * 1.4) * w
    env = np.sin(np.pi * k) ** 1.5 if not rising else k**2 * np.minimum(1, (1 - k) * 40)
    return out * env * 0.55


def sfx_riser(rng, dur: float = 2.6) -> np.ndarray:
    n = int(dur * SR)
    k = np.linspace(0, 1, n)
    noise = hp(rng.standard_normal(n), 900) * k**2.5 * 0.35
    tone = np.sin(2 * np.pi * np.cumsum(180 * 2 ** (k * 1.6)) / SR) * k**2 * 0.25
    return (noise + tone) * np.minimum(1, (1 - k) * 60)


def sfx_glitch(rng) -> np.ndarray:
    n = int(0.32 * SR)
    out = np.zeros(n)
    for _ in range(7):
        a = rng.integers(0, n - 2400)
        ln = rng.integers(500, 2400)
        f = rng.choice([110, 220, 440, 1760, 3520])
        seg = np.sign(np.sin(2 * np.pi * f * np.arange(ln) / SR)) * 0.25 + rng.standard_normal(ln) * 0.15
        out[a : a + ln] += seg
    return hp(out, 300) * 0.6


def sfx_ticks(dur: float, rng) -> np.ndarray:
    """Compteur qui s'emballe puis « ding » final (scènes statistiques)."""
    n = int((dur + 1.4) * SR)
    out = np.zeros(n)
    t, step = 0.0, 0.085
    click = hp(rng.standard_normal(700), 2500) * np.exp(-np.arange(700) / 90)
    while t < dur:
        i = int(t * SR)
        out[i : i + 700] += click * (0.25 + 0.35 * t / dur)
        t += step
        step = max(0.03, step * 0.94)
    d = tt(1.3)
    ding = (np.sin(2 * np.pi * 1318 * d) + 0.5 * np.sin(2 * np.pi * 1976 * d) + 0.3 * np.sin(2 * np.pi * 2637 * d)) * np.exp(-d * 4.5) * 0.3
    i = int(dur * SR)
    out[i : i + len(ding)] += ding[: n - i]
    return out


def sfx_blip() -> np.ndarray:
    d = tt(0.9)
    return (np.sin(2 * np.pi * 740 * d) + 0.4 * np.sin(2 * np.pi * 1480 * d)) * np.exp(-d * 6) * 0.35


def sfx_flash(rng) -> np.ndarray:
    d = tt(0.5)
    return (hp(rng.standard_normal(len(d)), 3000) * np.exp(-d * 16) * 0.5) + np.sin(2 * np.pi * 60 * d) * np.exp(-d * 10) * 0.6


# ───────────────────────────── Musique ─────────────────────────────
MOODS = {
    #            tonique  bpm  progression (demi-tons depuis la tonique, accords mineurs/majeurs)
    "epic": {"root": 38, "bpm": 96, "prog": [(0, "m"), (8, "M"), (3, "M"), (10, "M")], "perc": 1.0, "piano": 0.35, "ost": 1.0},
    "dark": {"root": 36, "bpm": 80, "prog": [(0, "m"), (5, "m"), (8, "M"), (7, "M")], "perc": 0.7, "piano": 0.6, "ost": 0.6},
    "nostalgic": {"root": 33, "bpm": 72, "prog": [(8, "M"), (3, "M"), (10, "M"), (0, "m")], "perc": 0.35, "piano": 1.0, "ost": 0.45},
    "tension": {"root": 40, "bpm": 108, "prog": [(0, "m"), (0, "m"), (8, "M"), (7, "m")], "perc": 0.9, "piano": 0.3, "ost": 1.0},
}


def make_music(duration: float, mood: str, marks: dict, seed: int = 7) -> np.ndarray:
    """Compose la bande originale. `marks` : temps de début des sections (contexte, developpement, rebondissement, conclusion)."""
    rng = np.random.default_rng(seed)
    m = MOODS.get(mood, MOODS["epic"])
    n = int((duration + 3.0) * SR)
    beat = 60.0 / m["bpm"]
    bar = 4 * beat
    t_ctx, t_dev, t_twist, t_end = marks["contexte"], marks["developpement"], marks["rebondissement"], marks["conclusion"]

    # Intensité dramatique au fil des sections
    intensity = curve(
        [(0, 0.75), (max(0.5, t_ctx), 0.45), (t_dev, 0.55), (max(t_dev + 1, t_twist - 0.5), 0.85), (t_twist, 1.0), (max(t_twist + 1, t_end - 0.3), 0.95), (t_end + 0.6, 0.5), (duration, 0.35), (duration + 3, 0.0)],
        n,
    )

    pad, bass, ost, piano, perc = (np.zeros((n, 2), np.float32) for _ in range(5))
    n_bars = int(np.ceil((duration + 2) / bar))
    for b in range(n_bars):
        deg, quality = m["prog"][(b // 2) % len(m["prog"])]
        root = m["root"] + deg
        third = 3 if quality == "m" else 4
        chord = [root + 24, root + 24 + third, root + 31, root + 36]
        t0 = b * bar
        # nappe : scies désaccordées filtrées, attaques lentes qui se chevauchent
        if b % 2 == 0:
            d = 2 * bar + 1.5
            t = tt(d)
            env = np.minimum(1, t / 1.2) * np.minimum(1, (d - t) / 1.5)
            for k, note in enumerate(chord):
                f = hz(note)
                v = sum(saw(f * det, t, rng.random()) for det in (0.994, 1.0, 1.007)) / 3
                place(pad, t0, lp(v, 1100) * env, 0.10, pan=(-0.6, 0.6, -0.25, 0.25)[k])
        # basse : pulsation en croches
        for e in range(8):
            ts = t0 + e * beat / 2
            d = tt(beat / 2 * 0.95)
            f = hz(root)
            sig = (np.sin(2 * np.pi * f * d) + 0.35 * np.sin(2 * np.pi * 2 * f * d)) * np.exp(-d * 5) * np.minimum(1, d / 0.006)
            place(bass, ts, sig, 0.30 if e % 2 == 0 else 0.18)
        # ostinato de cordes en doubles croches
        pattern = [0, 2, 1, 2, 3, 2, 1, 2] * 2
        for e in range(16):
            ts = t0 + e * beat / 4
            d = tt(0.16)
            f = hz(chord[pattern[e]] + 12)
            sig = lp(saw(f, d, rng.random()) + saw(f * 1.005, d, rng.random()), 3200) * np.exp(-d * 22) * np.minimum(1, d / 0.004)
            place(ost, ts, sig, 0.07 * (1.25 if e % 4 == 0 else 0.8), pan=0.35 if e % 2 else -0.35)
        # piano : arpège lent
        for e, idx in enumerate([0, 2, 1, 3]):
            ts = t0 + e * beat
            d = tt(2.2)
            f = hz(chord[idx] + (12 if e == 3 else 0))
            sig = (np.sin(2 * np.pi * f * d) + 0.45 * np.sin(2 * np.pi * 2 * f * d) * np.exp(-d * 3) + 0.2 * np.sin(2 * np.pi * 3 * f * d) * np.exp(-d * 6)) * np.exp(-d * 2.6) * np.minimum(1, d / 0.004)
            place(piano, ts, sig, 0.11, pan=(-0.3, 0.1, 0.3, -0.1)[e])
        # percussions : tambours graves
        for pos, g in ((0, 1.0), (1.5, 0.55), (2.5, 0.7), (3.5, 0.5)):
            ts = t0 + pos * beat
            d = tt(0.6)
            drum = np.sin(2 * np.pi * np.cumsum(48 + 70 * np.exp(-d * 30)) / SR) * np.exp(-d * 9) + lp(rng.standard_normal(len(d)), 900) * np.exp(-d * 26) * 0.5
            place(perc, ts, drum, 0.42 * g, pan=rng.uniform(-0.2, 0.2))
        if mood == "tension":
            for e in range(16):
                d = tt(0.05)
                place(perc, t0 + e * beat / 4, hp(rng.standard_normal(len(d)), 6000) * np.exp(-d * 90), 0.05)

    # Entrées et sorties des couches selon la dramaturgie
    g_pad = curve([(0, 0.9), (duration, 1.0), (duration + 3, 0)], n)
    g_bass = curve([(0, 0.0), (max(0.3, t_ctx), 0.25), (t_dev, 0.7), (t_twist, 1.0), (t_end, 0.9), (t_end + 0.8, 0.3), (duration + 2, 0)], n)
    g_ost = curve([(0, 0), (max(0.1, t_dev - 1.5), 0.0), (t_dev + 2, 0.6), (t_twist, 1.0), (t_end, 1.0), (t_end + 0.6, 0.0), (duration + 3, 0)], n) * m["ost"]
    g_piano = curve([(0, 0.2), (max(0.3, t_ctx), 1.0), (t_dev + 3, 0.6), (t_twist, 0.35), (t_end, 0.5), (t_end + 0.6, 1.0), (duration + 3, 0.4)], n) * m["piano"]
    g_perc = curve([(0, 0), (max(0.1, t_dev - 0.2), 0.0), (t_dev + 0.3, 0.5), (max(t_dev + 1, t_twist - 0.2), 0.75), (t_twist, 1.0), (t_end, 1.0), (t_end + 0.3, 0.0), (duration + 3, 0)], n) * m["perc"]
    mix = pad * g_pad[:, None] + bass * g_bass[:, None] + ost * g_ost[:, None] + piano * g_piano[:, None] + perc * g_perc[:, None]
    mix = lp(mix, 9000) * (0.55 + 0.45 * intensity[:, None])
    mix = reverb(mix, 2.4, 0.9, rng)
    # accord final tenu
    d = tt(3.0)
    final = sum(np.sin(2 * np.pi * hz(m["root"] + m["prog"][0][0] + k) * d) for k in (12, 24, 31)) * np.exp(-d * 1.2) * np.minimum(1, d / 0.05) * 0.06
    place(mix, max(0, duration - 1.2), final)
    peak = np.abs(mix).max() or 1.0
    return (mix / peak * 0.8)[: int(duration * SR)]


# ───────────────────────────── Bande d'effets ─────────────────────────────
def make_sfx(duration: float, timeline: list[dict], marks: dict, seed: int = 11) -> np.ndarray:
    rng = np.random.default_rng(seed)
    buf = np.zeros((int((duration + 3) * SR), 2), np.float32)
    place(buf, 0.0, sfx_impact(rng, 1.0), 0.9)
    tw = marks["rebondissement"]
    place(buf, tw - 2.6, sfx_riser(rng), 0.7)
    place(buf, tw, sfx_impact(rng, 1.2), 1.0)
    for i, sc in enumerate(timeline[:-1]):
        t, kind = sc["end"], sc["transition"]
        pan = 0.5 if i % 2 else -0.5
        if kind == "whip":
            place(buf, t - 0.28, sfx_whoosh(rng, 0.55), 0.9, pan)
        elif kind == "zoom":
            place(buf, t - 0.45, sfx_whoosh(rng, 0.6, rising=True), 0.8)
            place(buf, t, sfx_impact(rng, 0.5), 0.35)
        elif kind == "flash":
            place(buf, t - 0.03, sfx_flash(rng), 0.8)
        elif kind == "glitch":
            place(buf, t - 0.16, sfx_glitch(rng), 0.7)
        elif kind == "fade":
            place(buf, t - 0.3, sfx_whoosh(rng, 0.7), 0.35, pan)
    for sc in timeline:
        if sc["type"] == "stat":
            place(buf, sc["start"] + 0.35, sfx_ticks(min(1.3, sc["end"] - sc["start"] - 1.0), rng), 0.5)
        elif sc["type"] == "map":
            place(buf, sc["start"] + 0.9, sfx_blip(), 0.8)
            if sc.get("route"):
                place(buf, sc["start"] + 1.2, sfx_whoosh(rng, 1.2, rising=True), 0.3)
                place(buf, sc["start"] + 2.3, sfx_blip(), 0.8)
    buf = reverb(buf, 1.6, 0.35, rng)
    return buf[: int(duration * SR)]


# ───────────────────────────── Mixage ─────────────────────────────
def build_voice_track(voice: dict, timeline: list[dict], duration: float) -> np.ndarray:
    buf = np.zeros((int(duration * SR) + SR, 2), np.float32)
    by_id = {s["id"]: s for s in voice["scenes"]}
    for sc in timeline:
        a = read_audio(Path(by_id[sc["id"]]["file"]))
        i = int(sc["vo_start"] * SR)
        buf[i : i + len(a)] += a[: len(buf) - i]
    buf = hp(buf, 70)
    peak = np.abs(buf).max() or 1.0
    return (buf / peak * 0.89)[: int(duration * SR)]


def duck_gain(voice: np.ndarray, floor: float) -> np.ndarray:
    """Gain appliqué à la musique : descend à `floor` quand la voix parle."""
    env = lp(np.abs(voice).max(axis=1), 6.0)
    env = np.clip(env / 0.04, 0, 1)
    hold = int(0.25 * SR)  # tient le ducking entre les mots
    k = np.ones(hold) / hold
    env = np.clip(np.maximum(env, np.convolve(env, k, "same") * 1.6), 0, 1)
    return (1 - (1 - floor) * env).astype(np.float32)


def mix_all(cfg: dict, voice: dict, timeline: list[dict], marks: dict, duration: float, mood: str, out: Path, music_gain: float = 1.0) -> dict:
    ac = cfg["audio"]
    vo = build_voice_track(voice, timeline, duration)
    music = make_music(duration, mood, marks)
    sfx = make_sfx(duration, timeline, marks)
    gain = duck_gain(vo, ac["ducking"])
    mix = vo + music * gain[:, None] * ac["music_volume"] * music_gain + sfx * (0.6 + 0.4 * gain[:, None]) * ac["sfx_volume"]
    fade = int(0.25 * SR)  # fin courte : la vidéo reboucle
    mix[-fade:] *= np.linspace(1, 0, fade)[:, None] ** 1.5
    mix = np.tanh(mix * 1.1) / 1.1  # limiteur doux
    raw = out.with_suffix(".premix.wav")
    write_wav(raw, mix)
    stats = loudnorm(raw, out, ac["target_lufs"])
    raw.unlink(missing_ok=True)
    # mesures utiles au contrôle qualité : rapport voix / fond
    speaking = np.abs(vo).max(axis=1) > 0.05
    bed = (music * gain[:, None] * ac["music_volume"] * music_gain)[speaking]
    stats["voice_to_music_db"] = round(float(20 * np.log10((np.sqrt((vo[speaking] ** 2).mean()) + 1e-9) / (np.sqrt((bed**2).mean()) + 1e-9))), 1)
    return stats


def loudnorm(src: Path, dst: Path, target: float) -> dict:
    """Normalisation EBU R128 en deux passes (mesure puis gain linéaire)."""
    base = f"loudnorm=I={target}:TP=-1.5:LRA=11"
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", str(src), "-af", base + ":print_format=json", "-f", "null", "-"], capture_output=True, text=True)
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr, re.S)
    if not m:
        raise RuntimeError("mesure de loudness impossible")
    meas = json.loads(m.group(0))
    af = f"{base}:measured_I={meas['input_i']}:measured_TP={meas['input_tp']}:measured_LRA={meas['input_lra']}:measured_thresh={meas['input_thresh']}:offset={meas['target_offset']}:linear=true"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af", af, "-ar", str(SR), "-ac", "2", str(dst)], check=True)
    return {"input_lufs": float(meas["input_i"]), "target_lufs": target}
