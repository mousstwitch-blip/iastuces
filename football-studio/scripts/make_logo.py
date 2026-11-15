#!/usr/bin/env python3
"""Génère le logo « Hors-Jeu Stories » (PNG 1024×1024, lisible en pastille ronde). Usage : python scripts/make_logo.py"""
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
S, OUT = 2048, 1024
YEL, RED, WHITE, NAVY = (255, 214, 10), (230, 57, 70), (245, 245, 245), (11, 15, 26)
img = Image.new("RGB", (S, S), NAVY)
d = ImageDraw.Draw(img)
# fond : halo central
glow = Image.new("RGB", (S, S), NAVY)
ImageDraw.Draw(glow).ellipse((300, 150, 1750, 1500), fill=(34, 44, 74))
img = Image.blend(img, glow.filter(ImageFilter.GaussianBlur(260)), 0.9)
d = ImageDraw.Draw(img)

cx, cy, R = 1024, 640, 380
# ligne de hors-jeu (jaune, pointillée) derrière le ballon, légèrement inclinée
for i in range(-9, 10):
    x0 = cx + i * 120 - 40
    d.line((x0, cy + 40, x0 + 80, cy + 40), fill=YEL, width=16)

# ballon
ball = Image.new("RGBA", (S, S), (0, 0, 0, 0))
b = ImageDraw.Draw(ball)
b.ellipse((cx - R, cy - R, cx + R, cy + R), fill=WHITE)
def pent(x, y, r, rot):
    return [(x + r * math.cos(rot + k * 2 * math.pi / 5), y + r * math.sin(rot + k * 2 * math.pi / 5)) for k in range(5)]
rot0 = -math.pi / 2
b.polygon(pent(cx, cy, R * 0.34, rot0), fill=NAVY)
for k in range(5):
    a = rot0 + k * 2 * math.pi / 5
    p = (cx + R * 0.34 * math.cos(a), cy + R * 0.34 * math.sin(a))
    q = (cx + R * 0.70 * math.cos(a), cy + R * 0.70 * math.sin(a))
    b.line((p, q), fill=NAVY, width=14)
    ex, ey = cx + R * 0.98 * math.cos(a), cy + R * 0.98 * math.sin(a)
    b.polygon(pent(ex, ey, R * 0.30, a + math.pi), fill=NAVY)           # pièces du bord
mask = Image.new("L", (S, S), 0)
ImageDraw.Draw(mask).ellipse((cx - R, cy - R, cx + R, cy + R), fill=255)
ball.putalpha(mask)
shadow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
ImageDraw.Draw(shadow).ellipse((cx - R, cy - R + 40, cx + R, cy + R + 40), fill=(0, 0, 0, 170))
img.paste(shadow.filter(ImageFilter.GaussianBlur(40)), (0, 0), shadow.filter(ImageFilter.GaussianBlur(40)))
img.paste(ball, (0, 0), ball)
d = ImageDraw.Draw(img)
d.ellipse((cx - R, cy - R, cx + R, cy + R), outline=NAVY, width=10)
# petit drapeau de hors-jeu (rouge) planté sur la ligne, à droite
fx, fy = cx + 560, cy + 40
d.line((fx, fy - 250, fx, fy), fill=WHITE, width=14)
d.polygon([(fx, fy - 250), (fx + 190, fy - 205), (fx, fy - 160)], fill=RED)

def spaced(text, font, y, fill, gap=0):
    w = sum(font.getlength(c) for c in text) + gap * (len(text) - 1)
    x = (S - w) / 2
    for c in text:
        d.text((x, y), c, font=font, fill=fill)
        x += font.getlength(c) + gap
anton = ImageFont.truetype(str(ROOT / "assets/fonts/anton-400.ttf"), 400)
mont = ImageFont.truetype(str(ROOT / "assets/fonts/montserrat-900.ttf"), 128)
spaced("HORS-JEU", anton, 1100, WHITE, 6)
d.rounded_rectangle((520, 1636, 1528, 1646), radius=5, fill=YEL)
spaced("STORIES", mont, 1676, YEL, 46)
out = ROOT / "assets" / "brand"
out.mkdir(parents=True, exist_ok=True)
logo = img.resize((OUT, OUT), Image.LANCZOS)
logo.save(out / "logo.png")
round_ = Image.new("RGBA", (OUT, OUT), (0, 0, 0, 0))
m = Image.new("L", (OUT * 4, OUT * 4), 0)
ImageDraw.Draw(m).ellipse((0, 0, OUT * 4 - 1, OUT * 4 - 1), fill=255)
round_.paste(logo, (0, 0), m.resize((OUT, OUT), Image.LANCZOS))
round_.save(out / "logo_rond.png")
print("ok", out)
