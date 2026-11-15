"""Recherche du sujet, collecte des sources et fiche de faits vérifiés."""
from __future__ import annotations

import datetime as dt
import html
import json
import logging
import random
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

from .config import DIRS
from .llm import LLM

log = logging.getLogger("studio.research")
UA = {"User-Agent": "FootballStudio/1.0 (documentaires football; github.com/mousstwitch-blip/iastuces)"}


def prompt(name: str, **vars) -> str:
    text = (DIRS["prompts"] / f"{name}.md").read_text(encoding="utf-8")
    for k, v in vars.items():
        text = text.replace("{{" + k + "}}", str(v))
    return text


def system_prompt() -> str:
    return (DIRS["prompts"] / "system.md").read_text(encoding="utf-8").strip()


def _get(url: str, **kw) -> requests.Response | None:
    for attempt in range(4):
        try:
            r = requests.get(url, headers=UA, timeout=30, **kw)
            if r.status_code == 200:
                return r
            if r.status_code in (429, 503):
                time.sleep(2 + 3 * attempt)
                continue
            log.debug("HTTP %s pour %s", r.status_code, url)
            return None
        except requests.RequestException as e:
            log.debug("erreur réseau %s : %s", url, e)
            time.sleep(2)
    return None


# ───────────────────────────── Wikipédia ─────────────────────────────
def wiki_search(lang: str, query: str, limit: int = 3) -> list[str]:
    r = _get(f"https://{lang}.wikipedia.org/w/rest.php/v1/search/page", params={"q": query, "limit": limit})
    if not r:
        return []
    return [p["title"] for p in r.json().get("pages", [])]


def _strip_templates(text: str) -> str:
    out, depth, i = [], 0, 0
    while i < len(text):
        two = text[i : i + 2]
        if two == "{{":
            depth += 1
            i += 2
        elif two == "}}" and depth:
            depth -= 1
            i += 2
        else:
            if not depth:
                out.append(text[i])
            i += 1
    return "".join(out)


def clean_wikitext(raw: str) -> str:
    """Convertit du wikitexte en texte lisible (infobox conservée en clé = valeur)."""
    raw = re.sub(r"<!--.*?-->", "", raw, flags=re.S)
    raw = re.sub(r"<ref[^>/]*/>", "", raw)
    raw = re.sub(r"<ref[^>]*>.*?</ref>", "", raw, flags=re.S)
    infobox = ""
    m = re.search(r"\{\{\s*Infobox", raw, re.I)
    if m:
        depth, j = 0, m.start()
        while j < len(raw):
            if raw[j : j + 2] == "{{":
                depth += 1
                j += 2
            elif raw[j : j + 2] == "}}":
                depth -= 1
                j += 2
                if depth == 0:
                    break
            else:
                j += 1
        box = raw[m.start() : j]
        # modèles simples utiles : {{date|28|octobre|1933}} -> 28 octobre 1933
        box = re.sub(r"\{\{(?:date[^|}]*|birth date[^|}]*|death date[^|}]*)\|([^}]*)\}\}", lambda mm: " ".join(mm.group(1).split("|")[:3]), box, flags=re.I)
        lines = [ln.strip(" |") for ln in box.splitlines() if "=" in ln and not ln.strip().startswith("{{")]
        infobox = "\n".join(lines[:40])
        raw = raw[: m.start()] + raw[j:]

    def link(mm: re.Match) -> str:
        inner = mm.group(1)
        if re.match(r"(?i)(fichier|file|image|catégorie|category):", inner):
            return ""
        return inner.split("|")[-1]

    def clean(t: str) -> str:
        t = _strip_templates(t)
        t = re.sub(r"\{\|.*?\|\}", "", t, flags=re.S)
        for _ in range(2):
            t = re.sub(r"\[\[([^\[\]]*)\]\]", link, t)
        t = re.sub(r"\[https?://\S+\s?([^\]]*)\]", r"\1", t)
        t = re.sub(r"<[^>]+>", "", t)
        t = t.replace("'''", "").replace("''", "")
        return html.unescape(t)

    text = clean(raw)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    # coupe les sections sans valeur documentaire
    text = re.split(r"\n==\s*(?:Notes et références|Références|References|Voir aussi|See also|Liens externes|External links|Bibliographie|Notes)\s*==", text)[0]
    if infobox:
        text = "[Infobox]\n" + clean(infobox) + "\n\n" + text
    return text


def wiki_page(lang: str, title: str, max_chars: int) -> dict | None:
    r = _get(f"https://{lang}.wikipedia.org/w/index.php", params={"title": title, "action": "raw", "redirects": 1})
    if not r:
        return None
    raw = r.text
    m = re.match(r"#(?:REDIRECT|REDIRECTION)\s*\[\[([^\]|#]+)", raw, re.I)
    if m:
        return wiki_page(lang, m.group(1).strip(), max_chars)
    text = clean_wikitext(raw)
    if len(text) < 400:
        return None
    return {
        "title": f"Wikipédia ({lang}) — {title}",
        "url": f"https://{lang}.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_")),
        "lang": lang,
        "text": text[:max_chars],
        "retrieved": dt.date.today().isoformat(),
    }


def google_news(query: str, limit: int = 8) -> list[dict]:
    r = _get("https://news.google.com/rss/search", params={"q": query, "hl": "fr", "gl": "FR", "ceid": "FR:fr"})
    if not r:
        return []
    items = []
    try:
        for it in ET.fromstring(r.content).iter("item"):
            items.append({"title": it.findtext("title", ""), "date": it.findtext("pubDate", ""), "source": it.findtext("source", "")})
            if len(items) >= limit:
                break
    except ET.ParseError:
        pass
    return items


# ───────────────────────────── Sujet ─────────────────────────────
def load_history() -> list[str]:
    path = DIRS["projects"] / "history.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def save_history(title: str) -> None:
    hist = load_history()
    if title not in hist:
        hist.append(title)
    (DIRS["projects"] / "history.json").write_text(json.dumps(hist, ensure_ascii=False, indent=1), encoding="utf-8")


def find_topic(llm: LLM, category: str | None = None, exclude: list[str] | None = None) -> list[dict]:
    """Renvoie les sujets candidats, du plus prometteur au moins prometteur."""
    history = load_history() + (exclude or [])
    data = llm.json(
        prompt(
            "topics",
            count=8,
            category_line=f"Catégorie imposée : {category}." if category else "",
            history="; ".join(history[-60:]) or "aucun",
            seed=random.randint(1000, 9999),
        ),
        system=system_prompt(),
    )
    topics = [t for t in data.get("topics", []) if t.get("title")]
    topics.sort(key=lambda t: -float(t.get("score", 0)))
    return topics


def plan_topic(llm: LLM, topic: str) -> dict:
    data = llm.json(prompt("queries", topic=topic), system=system_prompt())
    data.setdefault("title", topic)
    data["requested"] = topic
    return data


# ───────────────────────────── Dossier ─────────────────────────────
def collect_sources(cfg: dict, topic: dict) -> list[dict]:
    rc = cfg["research"]
    sources: list[dict] = []
    seen: set[str] = set()
    per_lang = max(2, rc["max_pages"] // len(rc["languages"]) + 1)
    for lang in rc["languages"]:
        count = 0
        for q in topic.get(f"queries_{lang}", [])[:4]:
            for title in wiki_search(lang, q, 2):
                key = f"{lang}:{title}"
                if key in seen or count >= per_lang:
                    continue
                seen.add(key)
                page = wiki_page(lang, title, rc["max_chars_per_page"])
                if page:
                    page["id"] = f"S{len(sources) + 1}"
                    sources.append(page)
                    count += 1
                    log.info("  source %s : %s", page["id"], page["title"])
                time.sleep(0.6)
    return sources


def build_dossier(cfg: dict, llm: LLM, topic: dict, workdir: Path) -> dict:
    """Collecte les sources, croise les informations et produit research.json + sources.md."""
    sources = collect_sources(cfg, topic)
    news = google_news(topic["title"] + " football") if cfg["research"].get("news_check") else []
    web = bool(cfg["research"].get("web_search")) and llm.web
    if len(sources) < 2 and not web:
        raise RuntimeError(f"sources insuffisantes pour « {topic['title']} » ({len(sources)} page trouvée)")

    src_block = "\n\n".join(f"[{s['id']}] {s['title']} — {s['url']}\n{s['text']}" for s in sources) or "(aucune page Wikipédia trouvée)"
    news_block = ""
    if news:
        news_block = "TITRES D'ACTUALITÉ RÉCENTS (pour dater le sujet, pas des sources de faits) :\n" + "\n".join(
            f"- {n['date'][:16]} — {n['title']}" for n in news
        )
    web_rule = (
        " ; tu DOIS en plus vérifier sur le web (WebSearch) les 5 à 8 faits clés — dates, chiffres, noms — auprès de sources de presse ou institutionnelles,"
        " et lister dans extra_sources les pages réellement consultées"
        if web
        else ""
    )
    data = llm.json(
        prompt(
            "facts",
            topic=topic["title"],
            angle=topic.get("angle", ""),
            today=dt.date.today().isoformat(),
            sources=src_block,
            news=news_block,
            web_rule=web_rule,
        ),
        system=system_prompt(),
        web=web,
    )
    facts = [f for f in data.get("facts", []) if f.get("claim")]
    dossier = {
        "topic": topic,
        "sufficient": bool(data.get("sufficient", True)) and len(facts) >= 8,
        "summary": data.get("summary", ""),
        "facts": facts,
        "contradictions": data.get("contradictions", []),
        "sources": [{k: s[k] for k in ("id", "title", "url", "retrieved")} for s in sources]
        + [dict(e, retrieved=dt.date.today().isoformat()) for e in data.get("extra_sources", []) if e.get("url")],
        "news": news,
        "web_verified": web,
    }
    (workdir / "research.json").write_text(json.dumps(dossier, ensure_ascii=False, indent=1), encoding="utf-8")
    write_sources_md(dossier, workdir / "sources.md")
    n_ok = sum(f.get("status") == "confirme" for f in facts)
    n_unc = sum(f.get("status") == "incertain" for f in facts)
    log.info("  %d faits (%d confirmés par ≥2 sources, %d incertains), %d sources", len(facts), n_ok, n_unc, len(dossier["sources"]))
    return dossier


def write_sources_md(d: dict, path: Path) -> None:
    label = {"confirme": "✅ confirmé (≥ 2 sources)", "source_unique": "🟡 source unique", "incertain": "⚠️ incertain"}
    lines = [f"# Sources — {d['topic']['title']}", "", f"_Dossier établi le {dt.date.today().isoformat()}._", "", d["summary"], "", "## Sources consultées", ""]
    lines += [f"- **{s['id']}** — [{s['title']}]({s['url']}) (consulté le {s.get('retrieved', '')})" for s in d["sources"]]
    lines += ["", "## Faits retenus", "", "| # | Fait | Sources | Statut | Note |", "|---|---|---|---|---|"]
    for f in d["facts"]:
        lines.append(
            f"| {f.get('id', '')} | {f['claim'].replace('|', '/')} | {', '.join(f.get('sources', []))} | {label.get(f.get('status'), f.get('status', ''))} | {str(f.get('note', '')).replace('|', '/')} |"
        )
    if d["contradictions"]:
        lines += ["", "## Contradictions et incertitudes relevées", ""] + [f"- {c}" for c in d["contradictions"]]
    if d["news"]:
        lines += ["", "## Actualité récente (contrôle de fraîcheur)", ""] + [f"- {n['date'][:16]} — {n['title']}" for n in d["news"]]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def facts_block(d: dict) -> str:
    return "\n".join(
        f"{f.get('id')} [{f.get('status')}] {f['claim']}" + (f" (note : {f['note']})" if f.get("note") else "") for f in d["facts"]
    )
