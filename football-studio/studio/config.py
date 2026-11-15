"""Configuration centrale : config.toml + variables d'environnement (.env)."""
from __future__ import annotations

import logging
import os
import re
import shutil
import tomllib
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIRS = {
    "prompts": ROOT / "prompts",
    "assets": ROOT / "assets",
    "images": ROOT / "images",
    "audio": ROOT / "audio",
    "videos": ROOT / "videos",
    "projects": ROOT / "projects",
    "logs": ROOT / "logs",
}

log = logging.getLogger("studio")


def load_env() -> None:
    """Charge .env sans jamais écraser une variable déjà définie."""
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip().strip('"').strip("'")
        if value and key.strip() not in os.environ:
            os.environ[key.strip()] = value


def load_config() -> dict:
    load_env()
    with open(ROOT / "config.toml", "rb") as f:
        cfg = tomllib.load(f)
    for d in DIRS.values():
        d.mkdir(parents=True, exist_ok=True)
    return cfg


def secret(name: str) -> str | None:
    """Lit une clé API depuis l'environnement. Ne jamais journaliser la valeur."""
    v = os.environ.get(name, "").strip()
    return v or None


def proxy() -> str | None:
    return os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or None


def have(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def slugify(text: str, max_len: int = 48) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text[:max_len].strip("-") or "video"


def setup_logging(log_file: Path | None = None, verbose: bool = False) -> None:
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    for h in list(root.handlers):
        root.removeHandler(h)
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    console.setFormatter(logging.Formatter("%(asctime)s  %(message)s", "%H:%M:%S"))
    root.addHandler(console)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s"))
        root.addHandler(fh)
    for noisy in ("urllib3", "PIL", "asyncio", "aiohttp"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
