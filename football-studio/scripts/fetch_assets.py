#!/usr/bin/env python3
"""Télécharge et prépare les assets libres de droits du studio.

- Polices (SIL OFL 1.1) : Anton, Bebas Neue, Montserrat  -> assets/fonts/*.ttf
- Fond de carte (domaine public, Natural Earth via world-atlas) -> assets/geo/countries.json
- Modèle de profondeur Depth-Anything-V2-Small (Apache 2.0) -> assets/models/ (optionnel, --depth)

Les polices et la carte sont déjà versionnées dans le dépôt : ce script ne sert
qu'à les régénérer. Nécessite npm, et `pip install fonttools brotli`.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONTS = {
    "@fontsource/anton": ["anton-latin-400-normal.woff2"],
    "@fontsource/bebas-neue": ["bebas-neue-latin-400-normal.woff2"],
    "@fontsource/montserrat": [
        "montserrat-latin-600-normal.woff2",
        "montserrat-latin-800-normal.woff2",
        "montserrat-latin-900-normal.woff2",
    ],
}
DEPTH_URL = "https://huggingface.co/onnx-community/depth-anything-v2-small/resolve/main/onnx/model.onnx"


def npm_pack(pkg: str, tmp: Path) -> Path:
    out = subprocess.run(["npm", "pack", pkg, "--silent"], cwd=tmp, capture_output=True, text=True, check=True)
    tgz = tmp / out.stdout.strip().splitlines()[-1]
    dest = tmp / tgz.stem
    with tarfile.open(tgz) as tf:
        tf.extractall(dest, filter="data")
    return dest / "package"


def fetch_fonts(tmp: Path) -> None:
    from fontTools.ttLib import TTFont

    out_dir = ROOT / "assets" / "fonts"
    out_dir.mkdir(parents=True, exist_ok=True)
    for pkg, files in FONTS.items():
        pkg_dir = npm_pack(pkg, tmp)
        for name in files:
            font = TTFont(pkg_dir / "files" / name)
            font.flavor = None
            target = out_dir / (name.replace("-latin", "").replace("-normal.woff2", "") + ".ttf")
            font.save(target)
            print("police :", target.name)
        lic = pkg_dir / "LICENSE"
        if lic.exists():
            (out_dir / f"LICENSE-{pkg.split('/')[-1]}.txt").write_text(lic.read_text())


def decode_topojson(topo: dict, obj: str) -> list[dict]:
    """Décode un TopoJSON (arcs delta-encodés + quantification) en polygones lon/lat."""
    sx, sy = topo["transform"]["scale"]
    tx, ty = topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((round(x * sx + tx, 2), round(y * sy + ty, 2)))
        arcs.append(pts)

    def ring(indices: list[int]) -> list[tuple[float, float]]:
        pts: list[tuple[float, float]] = []
        for i in indices:
            a = arcs[i] if i >= 0 else arcs[~i][::-1]
            pts.extend(a if not pts else a[1:])
        # supprime les points consécutifs identiques (après arrondi)
        dedup = [pts[0]]
        for p in pts[1:]:
            if p != dedup[-1]:
                dedup.append(p)
        return dedup

    feats = []
    for g in topo["objects"][obj]["geometries"]:
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]] if g["type"] == "Polygon" else []
        rings = [ring(p[0]) for p in polys if p]  # anneau extérieur uniquement
        rings = [r for r in rings if len(r) >= 4]
        if rings:
            feats.append({"name": g.get("properties", {}).get("name", ""), "rings": rings})
    return feats


def fetch_geo(tmp: Path) -> None:
    pkg_dir = npm_pack("world-atlas", tmp)
    topo = json.loads((pkg_dir / "countries-50m.json").read_text())
    feats = decode_topojson(topo, "countries")
    out = ROOT / "assets" / "geo" / "countries.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(feats, separators=(",", ":")))
    print(f"carte : {len(feats)} pays -> {out.name} ({out.stat().st_size // 1024} Ko)")


def fetch_depth() -> None:
    import requests

    out = ROOT / "assets" / "models" / "depth_anything_v2_small.onnx"
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and out.stat().st_size > 50_000_000:
        print("modèle de profondeur déjà présent")
        return
    with requests.get(DEPTH_URL, stream=True, timeout=120) as r:
        r.raise_for_status()
        tmp = out.with_suffix(".part")
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
        tmp.rename(out)
    print("modèle de profondeur :", out.stat().st_size // (1 << 20), "Mo")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--depth", action="store_true", help="télécharge aussi le modèle de profondeur (99 Mo)")
    ap.add_argument("--only-depth", action="store_true")
    args = ap.parse_args()
    if not args.only_depth:
        with tempfile.TemporaryDirectory() as t:
            fetch_fonts(Path(t))
            fetch_geo(Path(t))
    if args.depth or args.only_depth:
        fetch_depth()
    return 0


if __name__ == "__main__":
    sys.exit(main())
