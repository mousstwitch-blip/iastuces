"""Synthesises the score and sound design, mixes them under the voice-over and
writes public/audio/mix.wav (48 kHz stereo, exactly 60 s, ~-14 LUFS).

Everything here is generated from scratch (no samples), so there is no licence
to clear. Event times are read from src/data/timeline.json.

Usage: python3 scripts/build_audio.py
"""
import json, os, subprocess, tempfile
import numpy as np
import soundfile as sf
from scipy.signal import fftconvolve, butter, sosfilt, resample_poly

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SR = 48000
TL = json.load(open(os.path.join(ROOT, "src/data/timeline.json")))
FPS = TL["fps"]
DUR = TL["durationInFrames"] / FPS
N = int(round(DUR * SR))
rng = np.random.default_rng(370)

scene = {s["id"]: s for s in TL["scenes"]}
caps = TL["captions"]


def cap(sid, i):
    c = [c for c in caps if c["scene"] == sid][i]
    return c["from"] / FPS, (c["from"] + c["durationInFrames"]) / FPS


def s0(sid):
    return scene[sid]["from"] / FPS


def t_arr(n):
    return np.arange(n) / SR


def env_adsr(n, a=0.005, r=0.2):
    e = np.ones(n)
    na, nr = max(1, int(a * SR)), max(1, int(r * SR))
    e[:na] = np.linspace(0, 1, na)
    e[-nr:] *= np.exp(-np.linspace(0, 5, nr))
    return e


def lowpass(x, f, order=2):
    return sosfilt(butter(order, f, "low", fs=SR, output="sos"), x)


def highpass(x, f, order=2):
    return sosfilt(butter(order, f, "high", fs=SR, output="sos"), x)


def bandpass(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], "band", fs=SR, output="sos"), x)


# ---------------------------------------------------------------- reverb
def make_ir(seconds=2.4, decay=3.2):
    n = int(seconds * SR)
    t = t_arr(n)
    ir = rng.standard_normal((n, 2)) * np.exp(-decay * t)[:, None]
    ir[:, 0] = lowpass(ir[:, 0], 6000)
    ir[:, 1] = lowpass(ir[:, 1], 6000)
    return ir / np.abs(ir).sum(axis=0).max() * 8


IR = make_ir()


def reverb(mono, wet=0.35):
    st = np.stack([mono, mono], axis=1)
    r = np.stack([fftconvolve(mono, IR[:, 0])[: len(mono)], fftconvolve(mono, IR[:, 1])[: len(mono)]], axis=1)
    return st * (1 - wet) + r * wet


# ---------------------------------------------------------------- tracks
music = np.zeros((N, 2))
sfx = np.zeros((N, 2))


def place(buf, at, sig, gain=1.0, pan=0.0):
    i = int(at * SR)
    if i >= N:
        return
    if sig.ndim == 1:
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        sig = np.stack([sig * l * 1.414, sig * r * 1.414], axis=1)
    j = min(N, i + len(sig))
    buf[i:j] += sig[: j - i] * gain


# ---------------------------------------------------------------- sounds
def ping(freq=1250, length=1.6):
    t = t_arr(int(length * SR))
    s = np.sin(2 * np.pi * freq * t) * np.exp(-t * 5) + 0.3 * np.sin(2 * np.pi * freq * 2.01 * t) * np.exp(-t * 9)
    return s * env_adsr(len(t), 0.002, 0.3)


def blip(freq=1600, length=0.07):
    t = t_arr(int(length * SR))
    return np.sin(2 * np.pi * freq * t) * env_adsr(len(t), 0.002, 0.03)


def boom(length=2.5, f0=70, f1=28):
    t = t_arr(int(length * SR))
    f = f1 + (f0 - f1) * np.exp(-t * 6)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * np.exp(-t * 1.6)
    s += lowpass(rng.standard_normal(len(t)), 300) * np.exp(-t * 9) * 0.6
    return np.tanh(s * 1.6)


def whoosh(length=0.9, up=True):
    n = int(length * SR)
    t = np.linspace(0, 1, n)
    noise = rng.standard_normal(n)
    out = np.zeros(n)
    # sweep a band-pass through the noise in blocks
    blocks = 40
    for b in range(blocks):
        a, z = b * n // blocks, (b + 1) * n // blocks
        p = (b + 0.5) / blocks
        fc = 300 + (3500 if up else 3500 * (1 - p)) * (p if up else 1)
        seg = bandpass(noise, max(80, fc * 0.6), min(18000, fc * 1.6))[a:z]
        out[a:z] = seg
    env = np.sin(np.pi * t) ** 2 if not up else t**2.2 * np.exp(-(t - 1) ** 2 * 0)
    return out * env * 0.8


def glitch(length=0.45):
    n = int(length * SR)
    out = np.zeros(n)
    i = 0
    while i < n:
        seg = int(rng.uniform(0.01, 0.05) * SR)
        kind = rng.integers(0, 3)
        tt = t_arr(seg)
        if kind == 0:
            s = np.sign(np.sin(2 * np.pi * rng.uniform(200, 2400) * tt))
        elif kind == 1:
            s = rng.standard_normal(seg)
            s = np.round(s * 3) / 3
        else:
            s = np.zeros(seg)
        out[i : i + seg] = s[: n - i] * rng.uniform(0.3, 1)
        i += seg
    return highpass(out, 150) * env_adsr(n, 0.001, 0.05) * 0.5


def static_noise(length):
    n = int(length * SR)
    s = bandpass(rng.standard_normal(n), 900, 4200)
    crackle = (rng.random(n) > 0.9985) * rng.standard_normal(n) * 4
    return (s * 0.5 + crackle) * env_adsr(n, 0.05, 0.1)


def tick(length=0.025):
    t = t_arr(int(length * SR))
    return highpass(rng.standard_normal(len(t)), 2500) * np.exp(-t * 300)


def sonar(freq=520, length=3.0):
    t = t_arr(int(length * SR))
    s = np.sin(2 * np.pi * freq * t) * np.exp(-t * 2.2) * env_adsr(len(t), 0.01, 0.5)
    return s


# ---------------------------------------------------------------- score
def tone(freqs, length, attack=1.5, release=2.0, bright=2500, detune=0.004):
    n = int(length * SR)
    t = t_arr(n)
    out = np.zeros(n)
    for f in freqs:
        for d in (-detune, 0, detune):
            ff = f * (1 + d)
            ph = rng.uniform(0, 2 * np.pi)
            for h in range(1, 9):
                out += np.sin(2 * np.pi * ff * h * t + ph * h) / (h**1.15)
    out = lowpass(out, bright)
    e = np.ones(n)
    na, nr = int(attack * SR), int(release * SR)
    e[:na] = np.linspace(0, 1, na) ** 2
    e[-nr:] *= np.linspace(1, 0, nr) ** 2
    return out * e / (len(freqs) * 12)


def note(name):
    names = {"C": -9, "C#": -8, "D": -7, "D#": -6, "E": -5, "F": -4, "F#": -3, "G": -2, "G#": -1, "A": 0, "A#": 1, "B": 2}
    letter, octave = name[:-1], int(name[-1])
    return 440 * 2 ** ((names[letter] + (octave - 4) * 12) / 12)


# Drone: D1 + A1, slowly breathing, all the way through.
t_all = t_arr(N)
drone = (
    np.sin(2 * np.pi * note("D2") * t_all) * 0.5
    + np.sin(2 * np.pi * note("A1") * t_all) * 0.35
    + np.sin(2 * np.pi * note("D1") * t_all) * 0.45
)
drone *= 0.75 + 0.25 * np.sin(2 * np.pi * t_all / 7.3)
drone += lowpass(rng.standard_normal(N), 180) * 0.18
drone_env = np.interp(
    t_all,
    [0, 0.4, s0("title"), s0("curvature"), s0("curvature") + 0.5, s0("satellite"), DUR - 3.2, DUR - 0.2, DUR],
    [0, 0.55, 0.75, 0.75, 0.45, 0.8, 0.8, 0.0, 0.0],
)
music += reverb(drone * drone_env * 0.32, 0.25)

# Pad chords from the title onwards: Dm – Bb – Gm – A, then Dm – F – C – Dm.
prog = [
    ["D3", "F3", "A3"],
    ["A#2", "D3", "F3"],
    ["G2", "A#2", "D3"],
    ["A2", "C#3", "E3"],
    ["D3", "F3", "A3"],
    ["F2", "A2", "C3"],
    ["C3", "E3", "G3"],
    ["D3", "A3", "D4"],
]
start = s0("title")
step = (DUR - start - 1.0) / len(prog)
for k, ch in enumerate(prog):
    sig = tone([note(n) for n in ch], step + 2.0, attack=1.2, release=2.2, bright=1600 + 200 * k)
    place(music, start + k * step, reverb(sig, 0.45), gain=0.55)

# Heartbeat pulse during the investigation (military radar → satellite).
beat = 60 / 72
t = s0("military")
while t < s0("search") + 1.0:
    if not (s0("curvature") - 0.1 < t < s0("satellite")):
        place(music, t, boom(0.6, 90, 40), gain=0.22)
    t += beat

# High shimmer on the closing line.
c2s, c2e = cap("end", 2)
shim = tone([note("A5"), note("D6")], DUR - c2s, attack=1.0, release=2.5, bright=6000, detune=0.003)
place(music, c2s - 0.2, reverb(shim, 0.6), gain=0.25)

# ---------------------------------------------------------------- sound design
# Hook: radar pings when the sweep crosses the target, then the reply dies.
for k in range(2):
    place(sfx, 0.73 + 2.0 * k, reverb(ping(1250), 0.4), 0.35, pan=0.2)
hook_vanish = cap("hook", 1)[1] + 6 / FPS
place(sfx, hook_vanish, glitch(0.4), 0.55)
place(sfx, hook_vanish + 0.05, boom(1.6, 55, 25), 0.35)
place(sfx, s0("title") - 0.7, whoosh(0.7, up=True), 0.4)
place(sfx, s0("title"), reverb(boom(3.0, 65, 26), 0.3), 0.6)
place(sfx, cap("title", 2)[0], reverb(boom(2.5, 80, 30), 0.3), 0.55)

# Transponder: interrogations and replies.
place(sfx, s0("transponder") - 0.25, whoosh(0.5, up=True), 0.3)
tc1 = cap("transponder", 1)[0]
tc2 = cap("transponder", 2)[0]
for d in (-6, 8, 22):
    place(sfx, tc1 + d / FPS, reverb(blip(1400, 0.06), 0.3), 0.3, pan=-0.3)
for d in (10, 22, 34):
    place(sfx, tc2 + d / FPS, reverb(np.concatenate([blip(2100, 0.04), np.zeros(int(0.03 * SR)), blip(2100, 0.04)]), 0.3), 0.28, pan=0.3)

# Goodnight: radio, clock, fast-forward and the transponder going silent.
g0 = s0("goodnight")
gq0, gq1 = cap("goodnight", 1)
place(sfx, gq0 - 0.15, static_noise(gq1 - gq0 + 0.3), 0.12)
place(sfx, gq0 - 0.15, tick(0.03) * 3, 0.3)
place(sfx, gq1 + 0.1, tick(0.03) * 3, 0.3)
t = g0 + 0.2
while t < cap("goodnight", 2)[0]:
    place(sfx, t, tick(), 0.18)
    t += 1.0
g2s, g2e = cap("goodnight", 2)
for k in range(28):
    place(sfx, g2s + 0.07 + k * 0.038, tick(), 0.12)
silent = g0 + (cap("goodnight", 2)[1] - g0) - 16 / FPS
tt = t_arr(int(0.5 * SR))
fall = np.sin(2 * np.pi * np.cumsum(1500 - 1300 * tt / 0.5) / SR) * np.exp(-tt * 5)
place(sfx, silent, fall, 0.22)
place(sfx, silent, glitch(0.35), 0.45)

# Military radar: a soft blip per primary plot, then the last echo dies.
m0 = s0("military")
mc0 = cap("military", 0)[0]
mc2s, mc2e = cap("military", 2)
plot_start, plot_end = mc0 + 6 / FPS, mc2s + 4 / FPS
for k in range(12):
    place(sfx, plot_start + (plot_end - plot_start) * k / 12, reverb(blip(900, 0.05), 0.4), 0.2, pan=-0.4 + k * 0.06)
place(sfx, mc2s, reverb(ping(700, 1.4), 0.5), 0.25)
place(sfx, mc2e - 2 / FPS, glitch(0.25), 0.35)

# Curvature: air.
place(sfx, s0("curvature"), whoosh(1.4, up=False), 0.3)
# Satellite.
place(sfx, s0("satellite") - 0.4, whoosh(0.5, up=True), 0.35)
sc1 = cap("satellite", 1)[0]
for d in (0, 14, 28):
    place(sfx, sc1 + d / FPS, reverb(ping(2200, 1.2), 0.55), 0.18, pan=-0.2)
place(sfx, cap("satellite", 2)[0], reverb(tone([note("A4"), note("E5")], 2.0, 0.6, 1.2, 5000), 0.6), 0.5)

# Search: sonar, counter, debris.
sr0 = s0("search")
place(sfx, sr0 + 0.1, reverb(sonar(520, 3.0), 0.5), 0.3)
place(sfx, sr0 + 1.3, reverb(sonar(520, 2.5), 0.5), 0.2)
for k in range(18):
    place(sfx, sr0 + 0.2 + k * 0.12, tick(0.02), 0.1)
deb = cap("search", 1)[0]
place(sfx, deb - 4 / FPS, reverb(boom(1.5, 70, 35), 0.4), 0.3)
place(sfx, deb + 18 / FPS, reverb(ping(980, 1.2), 0.45), 0.2)

# Rule: regular position reports.
t = s0("rule") + 0.4
while t < s0("end") - 0.3:
    place(sfx, t, reverb(blip(1800, 0.05), 0.4), 0.14, pan=rng.uniform(-0.5, 0.5))
    t += 1.5

# End: sweep without echo, the verdict, and the final card.
e0 = s0("end") - 16 / FPS
place(sfx, e0, whoosh(0.6, up=False), 0.3)
t = e0 + 0.3
while t < DUR - 1.5:
    place(sfx, t, tick(0.03), 0.16)
    t += 2.0
place(sfx, cap("end", 0)[0], reverb(boom(2.2, 60, 28), 0.3), 0.5)
card = cap("end", 2)[1] + 8 / FPS
place(sfx, card, reverb(boom(3.0, 50, 22), 0.4), 0.45)
place(sfx, card + 0.4, reverb(ping(1250, 2.2), 0.7), 0.25)

# ---------------------------------------------------------------- mix
vo, vsr = sf.read(os.path.join(ROOT, "public/audio/vo.wav"), dtype="float32")
vo = resample_poly(vo, SR, vsr)[:N]
vo = np.pad(vo, (0, N - len(vo)))
vo = highpass(vo, 70)
# gentle presence + compression
vo = vo + 0.25 * bandpass(vo, 2500, 6000)
vo = np.tanh(vo * 1.6) / np.tanh(1.6)

# sidechain: duck music while the voice speaks
win = int(0.05 * SR)
act = np.convolve(np.abs(vo), np.ones(win) / win, mode="same")
act = np.clip(act / (act.max() * 0.15), 0, 1)
act = np.convolve(act, np.ones(int(0.25 * SR)) / int(0.25 * SR), mode="same")
duck = 1 - 0.5 * act

mix = np.stack([vo, vo], axis=1) * 1.0 + music * duck[:, None] * 0.9 + sfx * (1 - 0.25 * act)[:, None]
speech = act > 0.5
db = lambda x: 20 * np.log10(np.sqrt(np.mean(x**2)) + 1e-12)
print(f"during speech: voice {db(vo[speech]):.1f} dB, music {db((music * duck[:, None] * 0.9)[speech]):.1f} dB, sfx {db(sfx[speech]):.1f} dB")
fade = np.ones(N)
fade[-int(0.4 * SR) :] = np.linspace(1, 0, int(0.4 * SR))
mix *= fade[:, None]
mix = np.tanh(mix * 0.9)

with tempfile.TemporaryDirectory() as td:
    raw = os.path.join(td, "raw.wav")
    sf.write(raw, mix.astype(np.float32), SR, subtype="FLOAT")
    out = os.path.join(ROOT, "public/audio/mix.wav")
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-af", "loudnorm=I=-14:TP=-1.5:LRA=9", "-ar", str(SR), "-t", f"{DUR:.3f}", "-c:a", "pcm_s16le", out],
        check=True,
    )
print("wrote public/audio/mix.wav")
