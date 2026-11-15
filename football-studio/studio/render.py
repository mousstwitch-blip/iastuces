"""Moteur de rendu : chaque image de la vidéo est une fonction pure du temps.

Scènes : image IA animée (caméra + parallaxe par carte de profondeur), statistique animée,
carte géographique animée. Par-dessus : incrustations, sous-titres mot à mot, transitions,
particules, vignettage et grain. Les images sont envoyées à FFmpeg par un tube.
"""
from __future__ import annotations

import json
import logging
import math
import multiprocessing as mp
import os
import re
import subprocess
import unicodedata
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .config import ROOT

log = logging.getLogger("studio.render")
cv2.setNumThreads(1)
FONTS = ROOT / "assets" / "fonts"


# ───────────────────────────── Outils ─────────────────────────────
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_out(x, p=3):
    return 1 - (1 - clamp(x)) ** p


def back_out(x, s=1.6):
    x = clamp(x) - 1
    return x * x * ((s + 1) * x + s) + 1


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


@lru_cache(maxsize=64)
def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / name), size)


def text_sprite(lines: list[list[tuple[str, tuple]]], font_name: str, size: int, stroke: int = 0, shadow: int = 0,
                line_gap: float = 0.12, align: str = "center", scales: dict | None = None) -> np.ndarray:
    """Rend un bloc de texte en RGBA. `lines` = lignes de segments (texte, couleur RGB)."""
    def safe(t: str) -> str:  # caractères absents des polices (espaces fines, ≈, emojis…)
        t = t.replace("\u202f", " ").replace("\u00a0", " ").replace("≈", "~").replace("×", "x")
        return "".join(ch for ch in t if ord(ch) < 0x250 or ch in "’‘“”…–—€")

    lines = [[(safe(t), c) for t, c in ln] for ln in lines]
    f = font(font_name, size)
    asc, desc = f.getmetrics()
    lh = int((asc + desc) * (1 + line_gap))
    space = f.getlength(" ")
    widths = [sum(f.getlength(t) for t, _ in ln) + space * (len(ln) - 1) for ln in lines]
    pad = stroke + shadow * 2 + 8
    w, h = int(max(widths)) + 2 * pad, lh * len(lines) + 2 * pad
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def draw(dr, fill_override=None):
        for i, ln in enumerate(lines):
            x = pad + (0 if align == "left" else (max(widths) - widths[i]) / 2)
            y = pad + i * lh
            for t, col in ln:
                dr.text((x, y), t, font=f, fill=fill_override or (*col, 255), stroke_width=stroke, stroke_fill=fill_override or (0, 0, 0, 255))
                x += f.getlength(t) + space

    if shadow:
        sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw(ImageDraw.Draw(sh), (0, 0, 0, 200))
        sh = sh.filter(ImageFilter.GaussianBlur(shadow))
        img.alpha_composite(sh, (0, int(shadow * 0.6)))
    draw(d)
    return np.asarray(img).copy()


def blit(frame: np.ndarray, sprite: np.ndarray, cx: float, cy: float, alpha: float = 1.0, scale: float = 1.0, anchor: str = "c") -> None:
    """Compose un sprite RGBA sur l'image (RGB). `anchor` : c = centre, l = bord gauche centré verticalement."""
    if alpha <= 0.003:
        return
    if abs(scale - 1) > 0.004:
        sprite = cv2.resize(sprite, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR if scale > 1 else cv2.INTER_AREA)
    sh, sw = sprite.shape[:2]
    x0 = int(round(cx - (sw / 2 if anchor == "c" else 0)))
    y0 = int(round(cy - sh / 2))
    H, W = frame.shape[:2]
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + sw), min(H, y0 + sh)
    if xa >= xb or ya >= yb:
        return
    sp = sprite[ya - y0 : yb - y0, xa - x0 : xb - x0]
    a = sp[..., 3:4].astype(np.uint16) * int(alpha * 256) >> 8
    roi = frame[ya:yb, xa:xb].astype(np.uint16)
    frame[ya:yb, xa:xb] = ((roi * (255 - a) + sp[..., :3].astype(np.uint16) * a) // 255).astype(np.uint8)


def wrap_words(text: str, font_name: str, size: int, max_w: int) -> list[str]:
    f = font(font_name, size)
    lines, cur = [], ""
    for w in text.split():
        trial = (cur + " " + w).strip()
        if f.getlength(trial) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    return lines + ([cur] if cur else [])


def fit_text(text: str, font_name: str, size: int, max_w: int, max_lines: int, min_size: int = 40) -> tuple[list[str], int]:
    while True:
        lines = wrap_words(text, font_name, size, max_w)
        widest = max(font(font_name, size).getlength(ln) for ln in lines)
        if (len(lines) <= max_lines and widest <= max_w) or size <= min_size:
            return lines, size
        size = int(size * 0.92)


def fr_number(v: float, decimals: int = 0) -> str:
    s = f"{v:,.{decimals}f}".replace(",", " ").replace(".", ",")
    return s


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if c.isalnum())


# ───────────────────────────── Sous-titres ─────────────────────────────
def caption_groups(words: list[dict], max_words: int, max_chars: int = 17) -> list[dict]:
    groups, cur = [], []

    def flush():
        if cur:
            groups.append({"words": list(cur), "start": cur[0]["start"], "end": cur[-1]["end"], "scene": cur[0]["scene"]})
            cur.clear()

    for w in words:
        if cur and (w["scene"] != cur[0]["scene"] or len(cur) >= max_words or sum(len(x["show"]) for x in cur) + len(w["show"]) > max_chars or w["start"] - cur[-1]["end"] > 0.6):
            flush()
        cur.append(w)
        if re.search(r"[.,;:!?…]$", w["text"]):
            flush()
    flush()
    for i, g in enumerate(groups):
        nxt = groups[i + 1]["start"] if i + 1 < len(groups) else g["end"] + 0.5
        g["show_from"] = g["start"] - 0.04
        g["show_to"] = nxt if nxt - g["end"] < 0.45 else g["end"] + 0.25
    return groups


def prepare_words(timeline: dict) -> list[dict]:
    out = []
    for w in timeline["words"]:
        show = re.sub(r"[«»\"“”().,;:…]", "", w["text"]).replace("’", "'").strip(" -–—").upper()
        if show:
            out.append(dict(w, show=show))
    return out


# ───────────────────────────── Rendu ─────────────────────────────
class Renderer:
    def __init__(self, timeline: dict, cfg: dict):
        self.tl, self.cfg = timeline, cfg
        self.W, self.H, self.fps = timeline["width"], timeline["height"], timeline["fps"]
        self.duration = timeline["duration"]
        self.scenes = timeline["scenes"]
        self.accent = hex_rgb(timeline.get("accent", "#FFD60A"))
        self.T = float(cfg["render"]["transition"])
        self.cc = cfg["captions"]
        self.groups = caption_groups(prepare_words(timeline), int(self.cc["max_words"]))
        self._img: dict[int, tuple] = {}
        self._sprites: dict = {}
        W, H = self.W, self.H
        ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
        self.Xn, self.Yn = xs - W / 2, ys - H / 2
        # vignettage + dégradés haut/bas pour la lisibilité des textes
        r = np.sqrt((self.Xn / (W * 0.75)) ** 2 + (self.Yn / (H * 0.75)) ** 2)
        vig = 1 - 0.42 * np.clip(r - 0.35, 0, 1) ** 1.6
        yy = ys / H
        vig *= 1 - 0.30 * np.clip((yy - 0.52) / 0.3, 0, 1) * np.clip((0.98 - yy) / 0.12, 0, 1) - 0.22 * np.clip((0.2 - yy) / 0.2, 0, 1)
        self.shade = cv2.merge([np.clip(vig * 255, 0, 255).astype(np.uint8)] * 3)
        rng = np.random.default_rng(5)
        self.grain = [np.clip(128 + rng.normal(0, 26, (H // 2, W // 2)), 0, 255).astype(np.uint8) for _ in range(5)]
        self.grain = [cv2.merge([cv2.resize(g, (W, H), interpolation=cv2.INTER_LINEAR)] * 3) for g in self.grain]
        self.particles = [self._particle_layer(rng, 46, (2, 5)), self._particle_layer(rng, 16, (7, 16))]
        self._geo = None

    # ── éléments partagés ──
    def _particle_layer(self, rng, count: int, radius: tuple[int, int]) -> np.ndarray:
        layer = np.zeros((self.H, self.W), np.float32)
        for _ in range(count):
            x, y, r = int(rng.integers(0, self.W)), int(rng.integers(0, self.H)), int(rng.integers(*radius))
            cv2.circle(layer, (x, y), r, float(rng.uniform(0.25, 0.9)), -1, cv2.LINE_AA)
        layer = cv2.GaussianBlur(layer, (0, 0), radius[1] * 0.55)
        tint = np.array([1.0, 0.93, 0.8], np.float32)
        return np.clip(layer[..., None] * tint * 255 * (1.4 if radius[1] < 8 else 0.55), 0, 255).astype(np.uint8)

    def sprite(self, key, builder):
        if key not in self._sprites:
            self._sprites[key] = builder()
        return self._sprites[key]

    def load(self, sc: dict):
        if sc["id"] not in self._img:
            img = cv2.cvtColor(cv2.imread(sc["image"]), cv2.COLOR_BGR2RGB)
            img = cv2.resize(img, (self.W, self.H), interpolation=cv2.INTER_LANCZOS4)
            # étalonnage commun : contraste doux, ombres froides, hautes lumières chaudes
            x = img.astype(np.float32) / 255
            x = x + 0.10 * (x - 0.5) * (1 - np.abs(2 * x - 1))
            lum = x.mean(axis=2, keepdims=True)
            x = x + (lum - 0.5) * np.array([0.035, 0.0, -0.045], np.float32)
            img = (np.clip(x, 0, 1) * 255).astype(np.uint8)
            img = cv2.addWeighted(img, 1.45, cv2.GaussianBlur(img, (0, 0), 2.2), -0.45, 0)  # accentuation
            depth = None
            if sc.get("depth") and os.path.exists(sc["depth"]):
                depth = cv2.resize(cv2.imread(sc["depth"], cv2.IMREAD_GRAYSCALE), (self.W // 4, self.H // 4), interpolation=cv2.INTER_AREA).astype(np.float32) / 255 - 0.5
            blurred = None
            if sc["type"] == "stat":
                small = cv2.GaussianBlur(cv2.resize(img, (self.W // 4, self.H // 4)), (0, 0), 5)
                blurred = (cv2.resize(small, (self.W, self.H), interpolation=cv2.INTER_CUBIC) * 0.8).astype(np.uint8)
            self._img[sc["id"]] = (img, depth, blurred)
            if len(self._img) > 4:  # mémoire bornée
                del self._img[next(iter(self._img))]
        return self._img[sc["id"]]

    # ── scène image : caméra virtuelle + parallaxe ──
    def camera(self, move: str, p: float) -> tuple[float, float, float, float, float, float]:
        """Renvoie (zoom, décalage x, décalage y, parallaxe x, parallaxe y, parallaxe radiale)."""
        W, H = self.W, self.H
        q = 2 * p - 1
        if move == "push_in":
            return 1.07 + 0.13 * p, 0, 0, 0, 0, 34 * p
        if move == "pull_out":
            return 1.20 - 0.13 * p, 0, 0, 0, 0, 34 * (1 - p)
        if move == "pan_left":
            return 1.15, 0.050 * W * q, 0, -26 * q, 0, 8
        if move == "pan_right":
            return 1.15, -0.050 * W * q, 0, 26 * q, 0, 8
        if move == "tilt_up":
            return 1.14, 0, 0.040 * H * q * -1, 0, 22 * q, 8
        if move == "tilt_down":
            return 1.14, 0, 0.040 * H * q, 0, -22 * q, 8
        return 1.11 + 0.04 * p, 12 * math.sin(q * 1.4), 0, 30 * math.sin(q * 1.5), 6 * math.cos(q * 1.5), 14 * p  # orbit

    def image_frame(self, sc: dict, t: float, source: np.ndarray | None = None, strength: float = 1.0) -> np.ndarray:
        img, depth, _ = self.load(sc)
        src = img if source is None else source
        dur = sc["end"] - sc["start"]
        p = clamp((t + self.T) / (dur + 2 * self.T))
        s, ox, oy, px, py, zr = self.camera(sc["camera"], p)
        s = 1 + (s - 1) * strength
        if dur > 4.5:  # relance visuelle : recadrage d'impact à mi-plan
            punch = ease_out((t - dur * 0.5) / 0.22, 4)
            s *= 1 + 0.09 * punch
            oy -= 0.02 * self.H * punch
        W, H = self.W, self.H
        if depth is None:
            M = np.float32([[1 / s, 0, W / 2 - W / (2 * s) + ox], [0, 1 / s, H / 2 - H / (2 * s) + oy]])
            return cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
        w4, h4 = W // 4, H // 4
        M4 = np.float32([[1 / s, 0, w4 / 2 - w4 / (2 * s) + ox / 4], [0, 1 / s, h4 / 2 - h4 / (2 * s) + oy / 4]])
        d = cv2.warpAffine(depth, M4, (w4, h4), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
        d = cv2.resize(d, (W, H), interpolation=cv2.INTER_LINEAR)
        k = zr / (W / 2)
        mx = self.Xn * (1 / s) + (W / 2 + ox) - d * (px + k * self.Xn) * strength
        my = self.Yn * (1 / s) + (H / 2 + oy) - d * (py + k * self.Yn) * strength
        return cv2.remap(src, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    # ── incrustations ──
    def draw_overlay(self, frame: np.ndarray, sc: dict, t: float, hook: bool) -> None:
        ov = sc.get("overlay")
        if not ov:
            return
        dur = sc["end"] - sc["start"]
        out = 1 - smooth((t - (dur - 0.30)) / 0.25)
        if hook:
            def build():
                size = 190
                while True:  # le bloc titre doit tenir au-dessus de la zone des sous-titres
                    lines, size = fit_text(ov["text"].upper(), "anton-400.ttf", size, self.W - 150, 3, 90)
                    if len(lines) * size * 1.12 <= 560 or size <= 90:
                        break
                    size = int(size * 0.92)
                segs = [[(ln, (255, 255, 255) if i < len(lines) - 1 or len(lines) == 1 else self.accent)] for i, ln in enumerate(lines)]
                return text_sprite(segs, "anton-400.ttf", size, stroke=6, shadow=14, line_gap=-0.13)
            sp = self.sprite(("hook", sc["id"]), build)
            a = ease_out((t + 0.05) / 0.22)
            scale = 1.22 - 0.22 * back_out((t + 0.05) / 0.30) + 0.02 * clamp(t / dur)
            cy = 250 + sp.shape[0] / 2
            blit(frame, sp, self.W / 2, cy, a * out, scale)
            bar_w = int((sp.shape[1] - 60) * ease_out((t - 0.15) / 0.4))
            if bar_w > 4 and out > 0.02:
                y = int(cy + sp.shape[0] / 2 - 4)
                col = tuple(int(c * out + frame[y, self.W // 2, i] * (1 - out)) for i, c in enumerate(self.accent))
                cv2.rectangle(frame, (self.W // 2 - bar_w // 2, y), (self.W // 2 + bar_w // 2, y + 10), col, -1)
            if ov.get("sub"):
                sub = self.sprite(("hooksub", sc["id"]), lambda: text_sprite([[(ln, (255, 255, 255))] for ln in fit_text(ov["sub"].upper(), "montserrat-800.ttf", 54, self.W - 160, 2, 36)[0]], "montserrat-800.ttf", fit_text(ov["sub"].upper(), "montserrat-800.ttf", 54, self.W - 160, 2, 36)[1], stroke=5, shadow=6))
                blit(frame, sub, self.W / 2, cy + sp.shape[0] / 2 + 34 + sub.shape[0] / 2, ease_out((t - 0.35) / 0.3) * out)
            return

        def build():
            lines, size = fit_text(ov["text"].upper(), "anton-400.ttf", 104, self.W - 260, 2, 60)
            title = text_sprite([[(ln, (255, 255, 255))] for ln in lines], "anton-400.ttf", size, stroke=3, shadow=8, line_gap=0.04, align="left")
            sub = None
            if ov.get("sub"):
                sl, ss = fit_text(ov["sub"].upper(), "montserrat-800.ttf", 50, self.W - 260, 2, 34)
                sub = text_sprite([[(ln, (255, 255, 255))] for ln in sl], "montserrat-800.ttf", ss, stroke=5, shadow=6, align="left")
            return title, sub
        title, sub = self.sprite(("chip", sc["id"]), build)
        k = ease_out((t - 0.25) / 0.4)
        a = k * out
        if a <= 0.01:
            return
        x = 96 - (1 - k) * 60
        y = 250
        total_h = title.shape[0] + (sub.shape[0] - 14 if sub is not None else 0)
        bar = frame[y + 10 : y + total_h - 10, 64:74]
        bar[:] = (bar * (1 - a) + np.array(self.accent) * a).astype(np.uint8)
        blit(frame, title, x - 10, y + title.shape[0] / 2, a, anchor="l")
        if sub is not None:
            blit(frame, sub, x - 8, y + title.shape[0] - 14 + sub.shape[0] / 2, a, anchor="l")

    # ── scène statistique ──
    def stat_frame(self, sc: dict, t: float) -> np.ndarray:
        _, _, blurred = self.load(sc)
        frame = self.image_frame(sc, t, source=blurred, strength=0.6)
        st = sc["stat"]
        dur = sc["end"] - sc["start"]
        count_dur = min(1.3, max(0.6, dur - 1.0))
        k = ease_out((t - 0.35) / count_dur, 4)
        target = float(st["value"])
        decimals = 0 if abs(target - round(target)) < 1e-6 else 1
        is_year = bool(st.get("year")) and decimals == 0
        fmt = (lambda v: str(int(round(v)))) if is_year else (lambda v: fr_number(v, decimals))
        st = dict(st, prefix=str(st.get("prefix", "")).upper(), suffix=str(st.get("suffix", "")).upper())
        final_txt = f"{st.get('prefix', '')}{fmt(target)}{st.get('suffix', '')}"
        _, size = fit_text(final_txt.replace(" ", " "), "anton-400.ttf", 400, self.W - 140, 1, 120)
        val = target * k if not is_year else target - (1 - k) * 60
        txt = f"{st.get('prefix', '')}{fmt(val)}{st.get('suffix', '')}" if k < 0.999 else final_txt
        sp = self.sprite(("num", sc["id"], txt), lambda: text_sprite([[(txt, (255, 255, 255))]], "anton-400.ttf", size, stroke=4, shadow=16))
        a = ease_out(t / 0.3)
        punch = 1 + 0.10 * math.exp(-max(0, t - 0.35 - count_dur) * 9) * (1 if t >= 0.35 + count_dur else 0)
        cy = self.H * (0.43 if sc.get("overlay") else 0.33)  # sous le bandeau éventuel
        blit(frame, sp, self.W / 2, cy, a, punch)
        done = ease_out((t - 0.35 - count_dur * 0.7) / 0.45)
        bw = int(320 * done)
        yb = int(cy + size * 0.62)
        if bw > 2:
            cv2.rectangle(frame, (self.W // 2 - bw, yb), (self.W // 2 + bw, yb + 12), self.accent, -1)
        if st.get("label"):
            def build():
                lines, ls = fit_text(st["label"].upper(), "montserrat-800.ttf", 58, self.W - 200, 3, 36)
                return text_sprite([[(ln, (255, 255, 255))] for ln in lines], "montserrat-800.ttf", ls, stroke=4, shadow=8)
            lab = self.sprite(("lab", sc["id"]), build)
            blit(frame, lab, self.W / 2, yb + 50 + lab.shape[0] / 2 + (1 - done) * 30, done)
        return frame

    # ── scène carte ──
    def geo(self):
        if self._geo is None:
            data = json.loads((ROOT / "assets" / "geo" / "countries.json").read_text())
            rings = []
            for c in data:
                if c["name"] == "Antarctica":
                    continue
                for r in c["rings"]:
                    a = np.asarray(r, np.float32)
                    if np.abs(np.diff(a[:, 0])).max() > 180:  # anneau à cheval sur l'antiméridien
                        a[:, 0] = np.where(a[:, 0] < 0, a[:, 0] + 360, a[:, 0])
                    rings.append((a, a[:, 0].min(), a[:, 0].max(), a[:, 1].min(), a[:, 1].max()))
            self._geo = rings
        return self._geo

    def map_frame(self, sc: dict, t: float) -> np.ndarray:
        W, H = self.W, self.H
        pts = sc["map"]["points"]
        route = sc["map"].get("route") and len(pts) == 2
        dur = sc["end"] - sc["start"]
        p = clamp((t + self.T) / (dur + 2 * self.T))
        if route:
            lat0 = (pts[0]["lat"] + pts[1]["lat"]) / 2
            lon0 = (pts[0]["lon"] + pts[1]["lon"]) / 2
            c = math.cos(math.radians(lat0))
            span_x = abs(pts[0]["lon"] - pts[1]["lon"]) * c
            span_y = abs(pts[0]["lat"] - pts[1]["lat"])
            k_fit = min((W * 0.62) / max(span_x, 0.5), (H * 0.36) / max(span_y, 0.5), 160)
            k = k_fit * (0.90 + 0.14 * smooth(p))
        else:
            lat0, lon0 = pts[0]["lat"], pts[0]["lon"]
            c = math.cos(math.radians(lat0))
            k = 13 * (1 - ease_out(p * 1.5, 3)) + 62 * ease_out(p * 1.5, 3) + 10 * p
        cx, cy = W / 2, H * 0.40

        def proj(lon, lat):
            return (lon - lon0) * c * k + cx, -(lat - lat0) * k + cy

        frame = np.empty((H, W, 3), np.uint8)
        frame[:] = (8, 13, 24)
        # graticule
        step = 10 if k < 30 else 5 if k < 70 else 2
        lon_a, lon_b = lon0 - cx / (c * k), lon0 + cx / (c * k)
        lat_a, lat_b = lat0 - (H - cy) / k, lat0 + cy / k
        for lon in np.arange(math.floor(lon_a / step) * step, lon_b + step, step):
            x = int(proj(lon, 0)[0])
            cv2.line(frame, (x, 0), (x, H), (17, 26, 44), 2)
        for lat in np.arange(math.floor(lat_a / step) * step, lat_b + step, step):
            y = int(proj(0, lat)[1])
            cv2.line(frame, (0, y), (W, y), (17, 26, 44), 2)
        polys = []
        for a, x0, x1, y0, y1 in self.geo():
            if x1 < lon_a or x0 > lon_b or y1 < lat_a or y0 > lat_b:
                continue
            if max((x1 - x0) * c, y1 - y0) * k < 3:
                continue
            q = np.empty((len(a), 2), np.float32)
            q[:, 0] = (a[:, 0] - lon0) * c * k + cx
            q[:, 1] = -(a[:, 1] - lat0) * k + cy
            polys.append(np.clip(q * 16, -2e6, 2e6).astype(np.int32))
        cv2.fillPoly(frame, polys, (24, 38, 62), cv2.LINE_AA, 4)
        edge = tuple(int(0.45 * ac + 0.55 * 150) for ac in self.accent)
        glow = np.zeros((H // 2, W // 2, 3), np.uint8)
        cv2.polylines(glow, [(q // 2) for q in polys], True, edge, 3, cv2.LINE_AA, 4)
        glow = cv2.resize(cv2.GaussianBlur(glow, (0, 0), 5), (W, H), interpolation=cv2.INTER_LINEAR)
        frame = cv2.add(frame, (glow * 0.7).astype(np.uint8))
        cv2.polylines(frame, polys, True, edge, 2, cv2.LINE_AA, 4)

        def pin(pt, t0):
            a = ease_out((t - t0) / 0.35)
            if a <= 0:
                return
            x, y = proj(pt["lon"], pt["lat"])
            for j in range(2):
                ph = ((t - t0) * 0.8 + j * 0.5) % 1.0
                rad = int(18 + 90 * ph)
                col = tuple(int(ch * (1 - ph) * a) for ch in self.accent)
                ring = np.zeros_like(frame[max(0, int(y) - 120) : int(y) + 120, max(0, int(x) - 120) : int(x) + 120])
                if ring.size:
                    cv2.circle(ring, (int(x) - max(0, int(x) - 120), int(y) - max(0, int(y) - 120)), rad, col, 5, cv2.LINE_AA)
                    roi = frame[max(0, int(y) - 120) : int(y) + 120, max(0, int(x) - 120) : int(x) + 120]
                    roi[:] = cv2.add(roi, ring)
            r = int(20 * back_out((t - t0) / 0.35))
            cv2.circle(frame, (int(x), int(y)), r + 7, (255, 255, 255), -1, cv2.LINE_AA)
            cv2.circle(frame, (int(x), int(y)), r, self.accent, -1, cv2.LINE_AA)
            if pt.get("name"):
                def build():
                    _, size = fit_text(pt["name"].upper(), "anton-400.ttf", 84, W - 240, 1, 44)
                    return text_sprite([[(pt["name"].upper(), (255, 255, 255))]], "anton-400.ttf", size, stroke=5, shadow=10)
                lab = self.sprite(("pin", sc["id"], pt["name"]), build)
                lx = clamp(x, lab.shape[1] / 2 + 30, W - lab.shape[1] / 2 - 30)
                blit(frame, lab, lx, y - 78 - (1 - a) * 20, a)

        if route:
            (xa, ya), (xb, yb) = proj(pts[0]["lon"], pts[0]["lat"]), proj(pts[1]["lon"], pts[1]["lat"])
            prog = smooth((t - 1.1) / min(1.4, max(0.6, dur - 2.2)))
            if prog > 0:
                dist = math.hypot(xb - xa, yb - ya)
                mxp, myp = (xa + xb) / 2, (ya + yb) / 2 - dist * 0.28
                u = np.linspace(0, prog, max(2, int(60 * prog)))[:, None]
                curve = (1 - u) ** 2 * np.array([xa, ya]) + 2 * u * (1 - u) * np.array([mxp, myp]) + u**2 * np.array([xb, yb])
                cv2.polylines(frame, [(curve * 16).astype(np.int32)], False, (255, 255, 255), 10, cv2.LINE_AA, 4)
                cv2.polylines(frame, [(curve * 16).astype(np.int32)], False, self.accent, 6, cv2.LINE_AA, 4)
                hx, hy = curve[-1]
                cv2.circle(frame, (int(hx), int(hy)), 13, (255, 255, 255), -1, cv2.LINE_AA)
            pin(pts[0], 0.75)
            pin(pts[1], 1.1 + min(1.4, max(0.6, dur - 2.2)) - 0.1)
        else:
            pin(pts[0], 0.75)
        return frame

    # ── assemblage ──
    def scene_frame(self, idx: int, t_abs: float) -> np.ndarray:
        sc = self.scenes[idx]
        t = t_abs - sc["start"]
        if sc["type"] == "stat" and not (idx == 0 and sc.get("overlay")):  # le titre du hook prime sur le compteur
            frame = self.stat_frame(sc, t)
        elif sc["type"] == "map":
            frame = self.map_frame(sc, t)
        else:
            frame = self.image_frame(sc, t, strength=1.0 if sc.get("depth") or sc["type"] == "image" else 1.0)
            if idx > 0:  # éclat lumineux bref à l'ouverture du plan
                leak = 0.20 * math.exp(-max(t, 0) * 7)
                if leak > 0.01:
                    frame = cv2.addWeighted(frame, 1.0, np.full_like(frame, (255, 214, 170)), leak, 0)
        self.draw_overlay(frame, sc, t, hook=idx in (0, len(self.scenes) - 1))
        return frame

    def transition(self, kind: str, a: np.ndarray, b: np.ndarray, p: float, seed: int) -> np.ndarray:
        W, H = self.W, self.H
        if kind == "cut":
            return a if p < 0.5 else b
        if kind == "fade":
            k = smooth(p)
            return cv2.addWeighted(a, 1 - k, b, k, 0)
        if kind == "flash":
            base = a if p < 0.5 else b
            glow = (1 - abs(2 * p - 1)) ** 1.5
            return cv2.addWeighted(base, 1.0, np.full_like(base, 255), glow * 0.92, 0)
        if kind == "whip":
            e = smooth(p)
            shift = int(e * W)
            out = np.empty_like(a)
            if shift < W:
                out[:, : W - shift] = a[:, shift:]
            if shift > 0:
                out[:, W - shift :] = b[:, :shift]
            kx = int(math.sin(math.pi * p) * 170) | 1
            return cv2.blur(out, (kx, 1)) if kx > 2 else out
        if kind == "zoom":
            def scaled(img, s):
                M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, s)
                return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            if p < 0.5:
                q = p * 2
                out = scaled(a, 1 + 1.6 * q**2.2)
                out = cv2.addWeighted(out, 1.0, np.full_like(out, 255), 0.5 * q**3, 0)
            else:
                q = (1 - p) * 2
                out = scaled(b, 1 + 0.9 * q**2.2)
                out = cv2.addWeighted(out, 1.0, np.full_like(out, 255), 0.5 * q**3, 0)
            return out
        # glitch
        rng = np.random.default_rng(seed + int(p * 12))
        base = (a if p < 0.5 else b).copy()
        amp = int(46 * (1 - abs(2 * p - 1)) + 6)
        base[..., 0] = np.roll(base[..., 0], amp, axis=1)
        base[..., 2] = np.roll(base[..., 2], -amp, axis=1)
        for _ in range(7):
            y = int(rng.integers(0, H - 160))
            h = int(rng.integers(20, 160))
            base[y : y + h] = np.roll(base[y : y + h], int(rng.integers(-140, 140)), axis=1)
        return base

    def draw_captions(self, frame: np.ndarray, t: float) -> None:
        g = next((g for g in self.groups if g["show_from"] <= t < g["show_to"]), None)
        if g is None:
            return
        active = -1
        for i, w in enumerate(g["words"]):
            if t >= w["start"] - 0.03:
                active = i
        cc = self.cc

        def build():
            words = g["words"]
            size = int(cc["size"])
            f = cc["font"]
            max_w = self.W - 150
            while True:
                fo = font(f, size)
                lines, cur, cw = [], [], 0.0
                for i, w in enumerate(words):
                    wl = fo.getlength(w["show"]) + (fo.getlength(" ") if cur else 0)
                    if cur and cw + wl > max_w:
                        lines.append(cur)
                        cur, cw = [], 0.0
                        wl = fo.getlength(w["show"])
                    cur.append(i)
                    cw += wl
                lines.append(cur)
                widest = max(sum(fo.getlength(words[i]["show"]) for i in ln) + fo.getlength(" ") * (len(ln) - 1) for ln in lines)
                if (len(lines) <= 2 and widest <= max_w) or size <= 48:
                    break
                size = int(size * 0.92)
            segs = []
            for ln in lines:
                row = []
                for i in ln:
                    w = words[i]
                    col = hex_rgb(cc["keyword_color"]) if w.get("keyword") and i <= active else hex_rgb(cc["active_color"]) if i == active else hex_rgb(cc["color"])
                    row.append((w["show"], col))
                segs.append(row)
            return text_sprite(segs, f, size, stroke=max(8, size // 9), shadow=7, line_gap=0.06)

        sp = self.sprite(("cap", id(g), active), build)
        pop = 0.86 + 0.14 * back_out((t - g["show_from"]) / 0.14)
        a = ease_out((t - g["show_from"]) / 0.08)
        blit(frame, sp, self.W / 2, self.H * float(cc["y_ratio"]), a, pop)

    def frame(self, n: int) -> np.ndarray:
        t = (n + 0.5) / self.fps
        idx = next((i for i, s in enumerate(self.scenes) if t < s["end"]), len(self.scenes) - 1)
        sc = self.scenes[idx]
        half = self.T / 2
        frame = None
        if idx + 1 < len(self.scenes) and t > sc["end"] - half and sc["transition"] != "cut":
            p = (t - (sc["end"] - half)) / self.T
            frame = self.transition(sc["transition"], self.scene_frame(idx, t), self.scene_frame(idx + 1, t), p, sc["id"])
        elif idx > 0 and t < sc["start"] + half and self.scenes[idx - 1]["transition"] != "cut":
            prev = self.scenes[idx - 1]
            p = (t - (prev["end"] - half)) / self.T
            frame = self.transition(prev["transition"], self.scene_frame(idx - 1, t), self.scene_frame(idx, t), p, prev["id"])
        if frame is None:
            frame = self.scene_frame(idx, t)
        if not frame.flags.writeable or frame.base is not None:
            frame = frame.copy()
        # particules en avant-plan (profondeur), vignettage, grain
        for li, layer in enumerate(self.particles):
            speed = (26, 60)[li]
            dy = int(t * speed) % self.H
            dx = int(math.sin(t * 0.35 + li) * 40)
            moved = np.roll(layer, (-dy, dx), axis=(0, 1))
            frame = cv2.addWeighted(frame, 1.0, moved, 0.5 + 0.2 * math.sin(t * 1.3 + li * 2), 0)
        frame = cv2.multiply(frame, self.shade, scale=1 / 255)
        g = float(self.cfg["render"]["grain"])
        if g > 0:
            frame = cv2.addWeighted(frame, 1.0, self.grain[n % len(self.grain)], g * 2, -128 * g * 2)
        if self.cfg["video"].get("channel_name"):
            mark = self.sprite("mark", lambda: text_sprite([[(self.cfg["video"]["channel_name"], (255, 255, 255))]], "montserrat-800.ttf", 34, stroke=2, shadow=4))
            blit(frame, mark, self.W / 2, 190, 0.7)
        self.draw_captions(frame, t)
        if t > self.duration - 0.5:  # fondu de sortie complet, après la fin de la narration
            frame = cv2.convertScaleAbs(frame, alpha=smooth((self.duration - t) / 0.5))
        return frame


# ───────────────────────────── Export ─────────────────────────────
def _render_part(args) -> str:
    timeline, cfg, a, b, out = args
    r = Renderer(timeline, cfg)
    v = cfg["video"]
    cmd = [
        "ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{r.W}x{r.H}", "-r", str(r.fps), "-i", "-",
        "-c:v", "libx264", "-preset", "medium", "-crf", str(v["crf"]), "-pix_fmt", "yuv420p", "-g", str(r.fps * 2), "-threads", "2", out,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for n in range(a, b):
            proc.stdin.write(r.frame(n).tobytes())
    finally:
        proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError(f"ffmpeg a échoué sur le segment {out}")
    return out


def render_video(timeline: dict, cfg: dict, audio: Path, out: Path, tmp: Path) -> Path:
    """Rend toutes les images en parallèle puis assemble vidéo + audio en MP4 (H.264 / AAC)."""
    total = int(round(timeline["duration"] * timeline["fps"]))
    workers = int(cfg["render"].get("workers") or 0) or max(1, (os.cpu_count() or 2))
    workers = min(workers, 8)
    step = math.ceil(total / workers)
    jobs = [(timeline, cfg, a, min(total, a + step), str(tmp / f"part_{i:02d}.mp4")) for i, a in enumerate(range(0, total, step))]
    log.info("  rendu de %d images sur %d processus…", total, len(jobs))
    with mp.get_context("fork").Pool(len(jobs)) as pool:
        parts = pool.map(_render_part, jobs)
    lst = tmp / "parts.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in parts))
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(audio), "-map", "0:v", "-map", "1:a",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", f"{timeline['duration']:.3f}", "-movflags", "+faststart", str(out)],
        check=True,
    )
    for p in parts:
        Path(p).unlink(missing_ok=True)
    return out
