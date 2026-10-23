"""Generates public/tex/bathymetry.jpg: a procedural, hill-shaded multibeam-style
seabed (illustration only, not real survey data)."""
import os, numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 1600, 2400
rng = np.random.default_rng(370)

from scipy.ndimage import gaussian_filter, rotate

def field(sigma):
    n = gaussian_filter(rng.standard_normal((H + 400, W + 400)), sigma)
    n = rotate(n, 32, reshape=False, mode="reflect")[200:200 + H, 200:200 + W]
    return (n - n.mean()) / n.std()

h = np.zeros((H, W))
for sigma, amp, ridged in [((140, 60), 1.0, True), ((60, 26), 0.55, True), ((22, 12), 0.22, False), ((7, 5), 0.035, False)]:
    f = field(sigma)
    h += amp * (-np.abs(f) if ridged else f)
yy, xx = np.mgrid[0:H, 0:W]
for k in range(4):
    off = rng.uniform(-600, 2600)
    h += 0.5 * np.tanh(((xx * 0.55 + yy * 0.83) - off) / 18.0)
h = (h - h.min()) / (h.max() - h.min())

# hillshade
gy, gx = np.gradient(h * 520)
slope = np.pi / 2 - np.arctan(np.hypot(gx, gy))
aspect = np.arctan2(-gx, gy)
az, alt = np.radians(315), np.radians(40)
shade = np.sin(alt) * np.sin(slope) + np.cos(alt) * np.cos(slope) * np.cos(az - aspect)
shade = np.clip(shade, 0, 1)

stops = [(0.0, (40, 20, 92)), (0.25, (30, 80, 190)), (0.45, (25, 165, 170)), (0.65, (210, 205, 90)), (0.82, (232, 130, 60)), (1.0, (230, 70, 60))]
pos = np.array([s[0] for s in stops]); cols = np.array([s[1] for s in stops], dtype=float)
rgb = np.stack([np.interp(h, pos, cols[:, i]) for i in range(3)], axis=-1)
rgb *= (0.35 + 0.85 * shade)[..., None]
contour = (np.abs((h * 24) % 1 - 0.5) > 0.47)
rgb[contour] *= 0.7
Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).save(os.path.join(ROOT, "public/tex/bathymetry.jpg"), quality=90)
print("ok")
