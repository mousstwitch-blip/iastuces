"""Fournisseurs de modèles de langage, interchangeables.

Tous exposent la même interface :
    llm.complete(prompt, system="", images=[...], web=False) -> str
    llm.json(prompt, ...) -> dict | list

Pour ajouter un fournisseur : sous-classer LLM, implémenter `_call`, l'ajouter à PROVIDERS.
"""
from __future__ import annotations

import base64
import json
import logging
import re
import subprocess
import tempfile
import time
from pathlib import Path

import requests

from .config import have, secret

log = logging.getLogger("studio.llm")


class LLMError(RuntimeError):
    pass


def extract_json(text: str):
    """Extrait le premier objet/tableau JSON d'une réponse (avec ou sans bloc ```)."""
    m = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    candidates = [m.group(1)] if m else []
    candidates.append(text)
    for cand in candidates:
        starts = [i for i in (cand.find("{"), cand.find("[")) if i >= 0]
        if not starts:
            continue
        start = min(starts)
        closer = "}" if cand[start] == "{" else "]"
        end = cand.rfind(closer)
        while end > start:
            try:
                return json.loads(cand[start : end + 1])
            except json.JSONDecodeError:
                end = cand.rfind(closer, start, end)
    raise LLMError("réponse sans JSON valide : " + text[:300])


class LLM:
    name = "base"
    vision = False
    web = False

    def __init__(self, cfg: dict):
        self.cfg = cfg["llm"]
        self.timeout = int(self.cfg.get("timeout", 420))

    def _call(self, prompt: str, system: str, images: list[Path], web: bool) -> str:
        raise NotImplementedError

    def complete(self, prompt: str, system: str = "", images: list[Path] | None = None, web: bool = False) -> str:
        images = [Path(p) for p in (images or [])]
        if images and not self.vision:
            raise LLMError(f"le fournisseur {self.name} ne sait pas lire les images")
        last: Exception | None = None
        for attempt in range(3):
            try:
                t0 = time.time()
                out = self._call(prompt, system, images, web and self.web)
                log.debug("%s: %d car. -> %d car. en %.0fs", self.name, len(prompt), len(out), time.time() - t0)
                if out.strip():
                    return out
                last = LLMError("réponse vide")
            except (requests.RequestException, subprocess.TimeoutExpired, LLMError) as e:
                last = e
                log.warning("%s : tentative %d échouée (%s)", self.name, attempt + 1, str(e)[:200])
                time.sleep(3 * (attempt + 1))
        raise LLMError(f"{self.name} : échec après 3 tentatives ({last})")

    def json(self, prompt: str, system: str = "", images: list[Path] | None = None, web: bool = False):
        prompt_json = prompt + "\n\nRéponds UNIQUEMENT avec le JSON demandé, sans texte avant ni après."
        last: Exception | None = None
        for _ in range(2):
            raw = self.complete(prompt_json, system, images, web)
            try:
                return extract_json(raw)
            except LLMError as e:
                last = e
                log.warning("JSON invalide, nouvelle demande")
        raise LLMError(str(last))


class ClaudeCLI(LLM):
    """Utilise la commande `claude` (Claude Code) : aucun coût supplémentaire ni clé API."""

    name = "claude_cli"
    vision = True
    web = True

    @staticmethod
    def available() -> bool:
        return have("claude")

    def _call(self, prompt, system, images, web):
        tools = []
        if images:
            tools.append("Read")
            listing = "\n".join(f"- {p.resolve()}" for p in images)
            prompt = f"Commence par lire ces images avec l'outil Read :\n{listing}\n\n{prompt}"
        if web:
            tools += ["WebSearch", "WebFetch"]
        cmd = ["claude", "-p", "--output-format", "text"]
        if self.cfg.get("claude_cli_model"):
            cmd += ["--model", self.cfg["claude_cli_model"]]
        if tools:
            cmd += ["--allowedTools", ",".join(tools)]
        full = (system + "\n\n" if system else "") + prompt
        # Répertoire neutre : le modèle ne charge pas le contexte du dépôt.
        with tempfile.TemporaryDirectory(prefix="studio-llm-") as cwd:
            r = subprocess.run(cmd, input=full, capture_output=True, text=True, timeout=self.timeout, cwd=cwd)
        if r.returncode != 0:
            raise LLMError(f"claude a renvoyé le code {r.returncode} : {(r.stderr or r.stdout)[:300]}")
        return r.stdout


def _b64(path: Path) -> tuple[str, str]:
    media = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return media, base64.b64encode(path.read_bytes()).decode()


class Anthropic(LLM):
    name = "anthropic"
    vision = True

    @staticmethod
    def available() -> bool:
        return secret("ANTHROPIC_API_KEY") is not None

    def _call(self, prompt, system, images, web):
        content: list[dict] = []
        for p in images:
            media, data = _b64(p)
            content.append({"type": "image", "source": {"type": "base64", "media_type": media, "data": data}})
        content.append({"type": "text", "text": prompt})
        body = {"model": self.cfg["anthropic_model"], "max_tokens": 8000, "messages": [{"role": "user", "content": content}]}
        if system:
            body["system"] = system
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": secret("ANTHROPIC_API_KEY"), "anthropic-version": "2023-06-01"},
            json=body,
            timeout=self.timeout,
        )
        if r.status_code >= 400:
            raise LLMError(f"Anthropic HTTP {r.status_code} : {r.text[:300]}")
        return "".join(b.get("text", "") for b in r.json()["content"] if b.get("type") == "text")


class OpenAICompat(LLM):
    name = "openai"
    vision = True
    url_key = "openai_base_url"
    model_key = "openai_model"

    @staticmethod
    def available() -> bool:
        return secret("OPENAI_API_KEY") is not None

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {secret('OPENAI_API_KEY')}"}

    def _endpoint(self) -> str:
        return self.cfg[self.url_key].rstrip("/") + "/chat/completions"

    def _call(self, prompt, system, images, web):
        content: list[dict] = [{"type": "text", "text": prompt}]
        for p in images:
            media, data = _b64(p)
            content.append({"type": "image_url", "image_url": {"url": f"data:{media};base64,{data}"}})
        messages = ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": content if images else prompt}
        ]
        r = requests.post(
            self._endpoint(), headers=self._headers(), json={"model": self.cfg[self.model_key], "messages": messages}, timeout=self.timeout
        )
        if r.status_code >= 400:
            raise LLMError(f"{self.name} HTTP {r.status_code} : {r.text[:300]}")
        return r.json()["choices"][0]["message"]["content"] or ""


class Pollinations(OpenAICompat):
    """Modèle gratuit et sans clé (qualité inférieure, pas de vision)."""

    name = "pollinations"
    vision = False
    model_key = "pollinations_model"

    @staticmethod
    def available() -> bool:
        return True

    def _headers(self) -> dict:
        tok = secret("POLLINATIONS_TOKEN")
        return {"Authorization": f"Bearer {tok}"} if tok else {}

    def _endpoint(self) -> str:
        return "https://text.pollinations.ai/openai"


PROVIDERS: dict[str, type[LLM]] = {
    "claude_cli": ClaudeCLI,
    "anthropic": Anthropic,
    "openai": OpenAICompat,
    "pollinations": Pollinations,
}


def get_llm(cfg: dict) -> LLM:
    wanted = cfg["llm"].get("provider", "auto")
    if wanted != "auto":
        if wanted not in PROVIDERS:
            raise LLMError(f"fournisseur LLM inconnu : {wanted} (choix : {', '.join(PROVIDERS)})")
        cls = PROVIDERS[wanted]
        if not cls.available():
            raise LLMError(f"le fournisseur LLM « {wanted} » n'est pas configuré (voir README, section Clés API)")
        return cls(cfg)
    for name, cls in PROVIDERS.items():
        if cls.available():
            log.info("Modèle de langage : %s", name)
            return cls(cfg)
    raise LLMError("aucun fournisseur LLM disponible")
