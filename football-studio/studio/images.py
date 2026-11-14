"""Génération des visuels IA, carte de profondeur et contrôle qualité n°2 (visuels)."""
from __future__ import annotations

import base64
import io
import json
import logging
import time
import urllib.parse
from pathlib import Path

import cv2
import numpy as np
import requests
from PIL import Image

from .config import ROOT, secret
from .llm import LLM, LLMError
from .research import prompt as tpl

log = logging.getLogger("studio.images")
W, H = 1080, 1920


class ImageError(RuntimeError):
    pass


def _fit(img: Image.Image) -> Image.Image:
    """Recadre en 9:16 puis redimensionne en 1080×1920."""
    w, h = img.size
    target = W / H
    if w / h > target:
        nw = int(h * target)
        img = img.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else:
        nh = int(w / target)
        img = img.crop((0, 0, w, nh))  # on garde le haut : le filigrane éventuel est en bas
    return img.resize((W, H), Image.LANCZOS).convert("RGB")


class ImageProvider:
    name = "base"

    def __init__(self, cfg: dict):
        self.cfg = cfg["images"]

    def generate(self, prompt: str, seed: int) -> Image.Image:
        raise NotImplementedError


class Pollinations(ImageProvider):
    """Flux via Pollinations : gratuit, sans clé (un jeton facultatif retire le filigrane)."""

    name = "pollinations"

    @staticmethod
    def available() -> bool:
        return True

    def generate(self, prompt: str, seed: int) -> Image.Image:
        # Image demandée plus haute que nécessaire : le bas (filigrane) est rogné par _fit.
        params = {"width": 1080, "height": 2048, "model": self.cfg["pollinations_model"], "seed": seed, "nologo": "true", "enhance": "false"}
        headers = {}
        if secret("POLLINATIONS_TOKEN"):
            headers["Authorization"] = f"Bearer {secret('POLLINATIONS_TOKEN')}"
        url = "https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt[:1400], safe="")
        last = ""
        for attempt in range(5):
            try:
                r = requests.get(url, params=params, headers=headers, timeout=180)
                if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
                    return _fit(Image.open(io.BytesIO(r.content)))
                last = f"HTTP {r.status_code}"
            except (requests.RequestException, OSError) as e:
                last = str(e)[:120]
            time.sleep(6 + 6 * attempt)
        raise ImageError(f"Pollinations indisponible ({last})")


class OpenAIImages(ImageProvider):
    """gpt-image-1 (payant). Implémenté selon l'API officielle ; nécessite OPENAI_API_KEY."""

    name = "openai"

    @staticmethod
    def available() -> bool:
        return secret("OPENAI_API_KEY") is not None

    def generate(self, prompt: str, seed: int) -> Image.Image:
        r = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers={"Authorization": f"Bearer {secret('OPENAI_API_KEY')}"},
            json={"model": self.cfg["openai_model"], "prompt": prompt, "size": "1024x1536", "n": 1},
            timeout=240,
        )
        if r.status_code >= 400:
            raise ImageError(f"OpenAI images HTTP {r.status_code} : {r.text[:200]}")
        return _fit(Image.open(io.BytesIO(base64.b64decode(r.json()["data"][0]["b64_json"]))))


class Procedural(ImageProvider):
    """Secours hors-ligne : ambiance de stade nocturne synthétique (jamais d'échec)."""

    name = "procedural"

    @staticmethod
    def available() -> bool:
        return True

    def generate(self, prompt: str, seed: int) -> Image.Image:
        rng = np.random.default_rng(seed)
        y = np.linspace(0, 1, H)[:, None]
        x = np.linspace(0, 1, W)[None, :]
        hue = rng.uniform(0, 1)
        sky = np.stack([0.03 + 0.10 * hue * (1 - y), 0.05 + 0.08 * (1 - y), 0.10 + 0.16 * (1 - y) * (1 - hue * 0.5)], -1) * np.ones((H, W, 1))
        img = sky.copy()
        horizon = 0.56
        pitch = y > horizon
        depth = np.clip((y - horizon) / (1 - horizon), 0, 1)
        stripes = (np.floor(8 / (depth + 0.12)) % 2) * 0.05
        grass = np.stack([0.03 + stripes * 0.4, 0.16 + stripes + 0.12 * depth, 0.05 + stripes * 0.3], -1) * np.ones((H, W, 1))
        img = np.where(pitch[..., None] * np.ones((1, W, 1), bool), grass, img)
        # tribunes : bande de points lumineux
        stand = ((y > 0.40) & (y <= horizon)) * np.ones((1, W), bool)
        noise = rng.random((H, W)) ** 14
        img[stand] += (noise[stand] * 2.5)[:, None] * np.array([1.0, 0.9, 0.7])
        img[stand] += 0.03
        glow = np.zeros((H, W), np.float32)
        for _ in range(rng.integers(3, 6)):
            cx, cy = rng.uniform(0.05, 0.95), rng.uniform(0.18, 0.36)
            d2 = (x - cx) ** 2 + ((y - cy) * H / W) ** 2
            glow += np.exp(-d2 / 0.0006) * 1.6 + np.exp(-d2 / 0.03) * 0.35
        img += glow[..., None] * np.array([1.0, 0.95, 0.85])
        img = cv2.GaussianBlur(img.astype(np.float32), (0, 0), 2.0)
        img += rng.normal(0, 0.012, img.shape)
        return Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))


PROVIDERS = {"openai": OpenAIImages, "pollinations": Pollinations, "procedural": Procedural}


def get_provider(cfg: dict) -> ImageProvider:
    wanted = cfg["images"].get("provider", "auto")
    if wanted != "auto":
        if wanted not in PROVIDERS or not PROVIDERS[wanted].available():
            raise ImageError(f"fournisseur d'images « {wanted} » inconnu ou non configuré")
        return PROVIDERS[wanted](cfg)
    if cfg["images"].get("allow_paid") and OpenAIImages.available():
        return OpenAIImages(cfg)
    return Pollinations(cfg)


# ───────────────────────────── Contrôles techniques ─────────────────────────────
def technical_issues(img: Image.Image) -> list[str]:
    a = np.asarray(img.convert("L"), np.float32)
    issues = []
    if a.mean() < 16:
        issues.append(f"image presque noire (luminance {a.mean():.0f})")
    if a.mean() > 238:
        issues.append("image surexposée")
    if a.std() < 14:
        issues.append(f"image uniforme (contraste {a.std():.0f})")
    sharp = cv2.Laplacian(cv2.resize(a, (540, 960)), cv2.CV_32F).var()
    if sharp < 4:
        issues.append(f"image floue (netteté {sharp:.0f})")
    return issues


def full_prompt(cfg: dict, scene: dict, extra: str = "") -> str:
    parts = [scene["image_prompt"].strip().rstrip("."), extra.strip(), cfg["images"]["style_suffix"]]
    return ". ".join(p for p in parts if p)


def generate_scene(cfg: dict, provider: ImageProvider, scene: dict, out: Path, attempt: int = 0, extra: str = "") -> dict:
    """Génère l'image d'une scène ; bascule sur le générateur procédural en dernier recours."""
    seed = 1000 * scene["id"] + 7 * attempt + 13
    prompt = full_prompt(cfg, scene, extra)
    used = provider.name
    try:
        img = provider.generate(prompt, seed)
    except ImageError as e:
        log.warning("  scène %d : %s -> image procédurale de secours", scene["id"], e)
        img, used = Procedural(cfg).generate(prompt, seed), "procedural"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, quality=95)
    return {"scene": scene["id"], "file": str(out), "provider": used, "seed": seed, "prompt": prompt, "attempt": attempt, "technical": technical_issues(img)}


def vision_review(llm: LLM, scenes: list[dict], files: list[Path], tmp: Path) -> dict[int, dict]:
    """Contrôle visuel par IA, par lots de 6 images réduites."""
    result: dict[int, dict] = {}
    for i in range(0, len(scenes), 6):
        batch, paths = scenes[i : i + 6], []
        for s, f in zip(batch, files[i : i + 6]):
            small = tmp / f"review_{s['id']:02d}.jpg"
            Image.open(f).resize((432, 768), Image.LANCZOS).save(small, quality=85)
            paths.append(small)
        desc = "\n".join(f"Image {k + 1} = scène {s['id']} — narration : « {s['narration']} » — visuel voulu : {s['visual_description']}" for k, s in enumerate(batch))
        try:
            data = llm.json(tpl("image_check", scenes=desc), images=paths)
        except LLMError as e:
            log.warning("  contrôle visuel IA indisponible : %s", e)
            continue
        for item in data.get("images", []):
            try:
                result[int(item["scene"])] = item
            except (KeyError, TypeError, ValueError):
                pass
    return result


def produce_images(cfg: dict, llm: LLM | None, script: dict, img_dir: Path, workdir: Path, only: dict[int, str] | None = None) -> list[dict]:
    """Génère (ou régénère, pour `only` = {scène: consigne}) les images puis les contrôle.

    Boucle : génération -> contrôle technique -> contrôle IA -> régénération des images rejetées.
    """
    provider = get_provider(cfg)
    ic = cfg["images"]
    report_path = workdir / "images_qc.json"
    report: dict[str, dict] = json.loads(report_path.read_text()) if report_path.exists() else {}
    scenes = script["scenes"]
    todo: dict[int, str] = dict(only) if only is not None else {s["id"]: "" for s in scenes if not (img_dir / f"scene_{s['id']:02d}.jpg").exists()}
    use_vision = bool(ic.get("vision_check")) and llm is not None and llm.vision
    log.info("  fournisseur d'images : %s · contrôle visuel IA : %s", provider.name, "oui" if use_vision else "non")

    for rnd in range(ic["max_attempts"]):
        if not todo:
            break
        for s in scenes:
            if s["id"] not in todo:
                continue
            prev = report.get(str(s["id"]), {}).get("attempt", -1)
            info = generate_scene(cfg, provider, s, img_dir / f"scene_{s['id']:02d}.jpg", attempt=prev + 1, extra=todo[s["id"]])
            report[str(s["id"])] = info
            log.info("  scène %2d : image générée (%s, essai %d)%s", s["id"], info["provider"], info["attempt"] + 1, " ⚠ " + ", ".join(info["technical"]) if info["technical"] else "")
        checked = [s for s in scenes if s["id"] in todo]
        retry: dict[int, str] = {s["id"]: "" for s in checked if report[str(s["id"])]["technical"]}
        if use_vision:
            good = [s for s in checked if s["id"] not in retry]
            reviews = vision_review(llm, good, [img_dir / f"scene_{s['id']:02d}.jpg" for s in good], workdir)
            for s in good:
                rv = reviews.get(s["id"])
                if not rv:
                    continue
                report[str(s["id"])]["vision"] = rv
                if not rv.get("ok", True):
                    retry[s["id"]] = str(rv.get("prompt_fix", ""))
                    log.info("  scène %2d : rejetée par le contrôle visuel (%s)", s["id"], rv.get("problem", ""))
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        todo = retry
    if todo:
        log.warning("  %d image(s) conservée(s) malgré des réserves après %d essais : scènes %s", len(todo), ic["max_attempts"], sorted(todo))
    for sid in todo:
        report[str(sid)]["accepted_with_reservations"] = True
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    return [report[str(s["id"])] for s in scenes if str(s["id"]) in report]


# ───────────────────────────── Profondeur (parallaxe) ─────────────────────────────
_DEPTH_SESSION = None
DEPTH_MODEL = ROOT / "assets" / "models" / "depth_anything_v2_small.onnx"


def depth_available() -> bool:
    if DEPTH_MODEL.exists():
        return True
    try:
        import subprocess, sys

        subprocess.run([sys.executable, str(ROOT / "scripts" / "fetch_assets.py"), "--only-depth"], check=True, capture_output=True, timeout=900)
    except Exception as e:  # réseau coupé, etc. : la parallaxe est simplement désactivée
        log.warning("  modèle de profondeur indisponible (%s) : parallaxe 3D désactivée", str(e)[:120])
    return DEPTH_MODEL.exists()


def depth_map(image_path: Path, out: Path) -> Path | None:
    """Carte de profondeur 0-255 (255 = proche) via Depth-Anything-V2-Small (ONNX, CPU)."""
    global _DEPTH_SESSION
    if out.exists() and out.stat().st_mtime >= image_path.stat().st_mtime:
        return out
    try:
        import onnxruntime as ort

        if _DEPTH_SESSION is None:
            opts = ort.SessionOptions()
            opts.log_severity_level = 3
            _DEPTH_SESSION = ort.InferenceSession(str(DEPTH_MODEL), opts, providers=["CPUExecutionProvider"])
        img = cv2.cvtColor(cv2.imread(str(image_path)), cv2.COLOR_BGR2RGB)
        x = cv2.resize(img, (294, 518), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
        x = (x - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]
        x = x.transpose(2, 0, 1)[None].astype(np.float32)
        d = _DEPTH_SESSION.run(None, {_DEPTH_SESSION.get_inputs()[0].name: x})[0].squeeze()
        lo, hi = np.percentile(d, 1), np.percentile(d, 99)
        d = np.clip((d - lo) / max(hi - lo, 1e-6), 0, 1)
        d = cv2.GaussianBlur(cv2.resize(d, (W // 2, H // 2), interpolation=cv2.INTER_CUBIC), (0, 0), 9)
        cv2.imwrite(str(out), (d * 255).astype(np.uint8))
        return out
    except Exception as e:
        log.warning("  profondeur impossible pour %s : %s", image_path.name, str(e)[:120])
        return None
