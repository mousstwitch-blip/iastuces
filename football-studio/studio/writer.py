"""Écriture du script + storyboard, et contrôle qualité n°1 (script)."""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from .llm import LLM
from .research import facts_block, prompt, system_prompt

log = logging.getLogger("studio.writer")

SECTIONS = ["hook", "contexte", "developpement", "rebondissement", "conclusion"]
CAMERAS = ["push_in", "pull_out", "pan_left", "pan_right", "tilt_up", "tilt_down", "orbit"]
TRANSITIONS = ["cut", "fade", "flash", "whip", "zoom", "glitch"]
MOODS = ["epic", "dark", "nostalgic", "tension"]
WORDS_PER_SECOND = 2.75  # débit mesuré de la voix à +10 %


def words(text: str) -> list[str]:
    return re.findall(r"[\wÀ-ÿ'’-]+", text)


def narration_words(script: dict) -> int:
    return sum(len(words(s["narration"])) for s in script["scenes"])


def normalize(script: dict) -> dict:
    """Répare les écarts de format sans toucher au fond."""
    script["mood"] = script.get("mood") if script.get("mood") in MOODS else "epic"
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", str(script.get("accent_color", ""))):
        script["accent_color"] = "#FFD60A"
    scenes = [s for s in script.get("scenes", []) if str(s.get("narration", "")).strip()]
    for i, s in enumerate(scenes):
        s["id"] = i + 1
        s["narration"] = re.sub(r"\s+", " ", s["narration"]).strip()
        if s.get("section") not in SECTIONS:
            s["section"] = "hook" if i == 0 else "conclusion" if i == len(scenes) - 1 else "developpement"
        if s.get("camera") not in CAMERAS:
            s["camera"] = CAMERAS[i % len(CAMERAS)]
        if s.get("transition") not in TRANSITIONS:
            s["transition"] = "fade"
        s["keywords"] = [k for k in (s.get("keywords") or []) if isinstance(k, str)][:3]
        s["facts"] = s.get("facts") or []
        s["type"] = s.get("type") if s.get("type") in ("image", "stat", "map") else "image"
        if s["type"] == "stat":
            st = s.get("stat") or {}
            try:
                st["value"] = float(str(st.get("value")).replace(",", ".").replace(" ", ""))
                st.setdefault("prefix", ""), st.setdefault("suffix", ""), st.setdefault("label", "")
                st["suffix"] = (" " + st["suffix"].strip()) if st["suffix"].strip() and st["suffix"].strip() not in ("%", "°") else st["suffix"].strip()
                s["stat"] = st
            except (TypeError, ValueError):
                s["type"], s["stat"] = "image", None
        if s["type"] == "map":
            pts = []
            for p in (s.get("map") or {}).get("points", [])[:2]:
                try:
                    lat, lon = float(p["lat"]), float(p["lon"])
                    if -85 <= lat <= 85 and -180 <= lon <= 180:
                        pts.append({"name": str(p.get("name", "")), "lat": lat, "lon": lon})
                except (KeyError, TypeError, ValueError):
                    pass
            if pts:
                s["map"] = {"points": pts, "route": bool((s.get("map") or {}).get("route")) and len(pts) == 2}
            else:
                s["type"], s["map"] = "image", None
        ov = s.get("overlay")
        s["overlay"] = {"text": str(ov.get("text", "")).strip(), "sub": str(ov.get("sub") or "").strip()} if isinstance(ov, dict) and ov.get("text") else None
        s.setdefault("image_prompt", s.get("visual_description", ""))
        s.setdefault("visual_description", ""), s.setdefault("animation_prompt", ""), s.setdefault("lighting", "")
    script["scenes"] = scenes
    script.setdefault("social", {"title": script.get("title", ""), "description": "", "hashtags": ["#football"]})
    return script


def auto_check(script: dict, cfg: dict, dossier: dict) -> list[dict]:
    """Contrôles déterministes : durée, structure, hook, répétitions, prompts visuels."""
    sc = cfg["script"]
    issues: list[dict] = []
    scenes = script["scenes"]

    def add(scene, sev, typ, problem, fix):
        issues.append({"scene": scene, "severity": sev, "type": typ, "problem": problem, "fix": fix})

    n = narration_words(script)
    est = n / WORDS_PER_SECOND + 0.18 * len(scenes)
    if n < sc["min_words"]:
        add(0, "bloquant", "rythme", f"narration trop courte : {n} mots (≈ {est:.0f} s)", f"ajouter {sc['min_words'] - n + 5} mots de contenu factuel issu de la fiche")
    if n > sc["max_words"]:
        add(0, "bloquant", "rythme", f"narration trop longue : {n} mots (≈ {est:.0f} s)", f"retirer {n - sc['max_words'] + 5} mots en supprimant les détails secondaires")
    if not 9 <= len(scenes) <= 14:
        add(0, "bloquant", "rythme", f"{len(scenes)} scènes", "viser 10 à 13 scènes")
    if scenes:
        hook = scenes[0]
        if len(words(hook["narration"])) > 14:
            add(1, "bloquant", "hook", f"hook de {len(words(hook['narration']))} mots", "une seule phrase de 12 mots maximum")
        if re.match(r"(?i)\s*(saviez-vous|aujourd'hui|bonjour|dans cette vidéo)", hook["narration"]):
            add(1, "bloquant", "hook", "introduction banale", "ouvrir directement sur le fait le plus intrigant")
        if not hook.get("overlay"):
            add(1, "mineur", "visuel", "pas d'overlay sur le hook", "ajouter un overlay percutant de 2 à 5 mots")
        if not scenes[-1]["narration"].rstrip(" »\"").endswith("?"):
            add(len(scenes), "bloquant", "rythme", "la conclusion ne se termine pas par une question", "terminer par une question ouverte qui appelle les commentaires")
    if scenes:
        last = scenes[-1]
        if len(words(last["narration"])) > 14 or len(re.findall(r"[.!?…]+", last["narration"])) > 1:
            add(last["id"], "bloquant", "rythme", "la scène finale ne doit contenir que la question (12 mots maximum)", "déplacer le reste dans la scène de dénouement qui précède")
        if not last.get("overlay"):
            add(last["id"], "bloquant", "visuel", "pas d'overlay sur la scène finale", "overlay.text = la question résumée en 2 à 6 mots")
        if sum(s["section"] == "conclusion" for s in scenes) < 2:
            add(0, "bloquant", "coherence", "pas de scène de dénouement avant la question finale", "ajouter une scène conclusion qui dit ce qu'il est advenu ensuite")
    people = r"(?i)\b(player|man|men|woman|goalkeeper|referee|coach|crowd|fans?|supporters?|spectators?|boy|child|children|silhouette|figure|people|team|captain|president|journalist)\b"
    generic = [s["id"] for s in scenes if s["type"] == "image" and re.search(r"(?i)\b(ball|stadium|trophy|pitch|net)\b", s.get("image_prompt", "")) and not re.search(people, s.get("image_prompt", ""))]
    if len(generic) > 2:
        add(0, "bloquant", "visuel", f"trop d'images génériques sans personnage (scènes {generic})", "remplacer par des visuels propres à l'histoire : personnage de dos, foule, lieu précis")
    order = [SECTIONS.index(s["section"]) for s in scenes]
    if order != sorted(order):
        add(0, "mineur", "coherence", "sections dans le désordre", "respecter hook → contexte → developpement → rebondissement → conclusion")
    for sec in SECTIONS:
        if sec not in [s["section"] for s in scenes]:
            add(0, "bloquant", "coherence", f"section « {sec} » absente", f"ajouter une scène {sec}")
    if not any(s["type"] == "stat" for s in scenes):
        add(0, "mineur", "visuel", "aucune scène de type stat", "transformer une scène chiffrée en type stat")

    known = {f.get("id") for f in dossier["facts"]}
    uncertain = {f.get("id") for f in dossier["facts"] if f.get("status") == "incertain"}
    seen_sentences: set[str] = set()
    for s in scenes:
        nw = len(words(s["narration"]))
        if nw > 20:
            add(s["id"], "bloquant", "rythme", f"scène de {nw} mots (18 maximum)", "scinder en deux scènes ou raccourcir")
        for sent in re.split(r"(?<=[.!?…])\s+", s["narration"]):
            if len(words(sent)) > 24:
                add(s["id"], "mineur", "rythme", f"phrase trop longue : « {sent[:60]}… »", "couper en deux phrases")
            key = re.sub(r"\W+", " ", sent.lower()).strip()
            if key and key in seen_sentences:
                add(s["id"], "bloquant", "rythme", f"phrase répétée : « {sent[:60]} »", "supprimer la répétition")
            seen_sentences.add(key)
        if not s["facts"] and s["section"] not in ("conclusion",):
            add(s["id"], "mineur", "fait", "aucun fait de la fiche référencé", "rattacher la scène à des identifiants de faits")
        bad = [f for f in s["facts"] if f not in known]
        if bad:
            add(s["id"], "bloquant", "fait", f"faits inconnus de la fiche : {bad}", "n'utiliser que des faits de la fiche")
        unc = [f for f in s["facts"] if f in uncertain]
        if unc and not re.search(r"(?i)\b(aurait|auraient|serait|seraient|selon|dit-on|raconte|légende|paraît|rumeur|peut-être)\b", s["narration"]):
            add(s["id"], "bloquant", "fait", f"fait incertain {unc} présenté comme certain", "le retirer ou le formuler au conditionnel")
        ip = s.get("image_prompt", "")
        if len(ip.split()) < 15:
            add(s["id"], "bloquant", "visuel", "image_prompt trop court", "35 à 60 mots en anglais")
        if re.search(r"(?i)\bfootball\b", ip) and not re.search(r"(?i)soccer", ip):
            add(s["id"], "mineur", "visuel", "« football » sans « soccer » dans image_prompt", "écrire soccer")
        for kw in s["keywords"]:
            if kw.lower() not in s["narration"].lower():
                s["keywords"] = [k for k in s["keywords"] if k != kw]
    return issues


def _dump(script: dict) -> str:
    return json.dumps(script, ensure_ascii=False, indent=1)


def write_script(cfg: dict, llm: LLM, dossier: dict, workdir: Path) -> dict:
    """Génère le script puis le soumet à l'auto-critique (max_revisions cycles)."""
    sc = cfg["script"]
    facts = facts_block(dossier)
    topic = dossier["topic"]
    script = normalize(
        llm.json(
            prompt("script", topic=topic["title"], angle=topic.get("angle", ""), facts=facts, min_words=sc["min_words"], max_words=sc["max_words"]),
            system=system_prompt(),
        )
    )
    report = []
    for cycle in range(1, sc["max_revisions"] + 1):
        auto = auto_check(script, cfg, dossier)
        review = llm.json(
            prompt("critique", facts=facts, script=_dump(script), auto_issues=json.dumps(auto, ensure_ascii=False, indent=1) if auto else "aucun problème détecté"),
            system=system_prompt(),
        )
        issues = auto + [i for i in review.get("issues", []) if i.get("problem")]
        blocking = [i for i in issues if i.get("severity") == "bloquant"]
        ok = not blocking and review.get("verdict") == "ok"
        report.append({"cycle": cycle, "words": narration_words(script), "hook_score": review.get("hook_score"), "overall_score": review.get("overall_score"), "issues": issues, "ok": ok})
        log.info(
            "  contrôle script %d : %d mots, hook %s/10, note %s/100, %d problème(s) dont %d bloquant(s)",
            cycle, narration_words(script), review.get("hook_score"), review.get("overall_score"), len(issues), len(blocking),
        )
        (workdir / "script_qc.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        if ok or (not issues):
            break
        if cycle == sc["max_revisions"]:
            # Dernier cycle : on n'accepte un script imparfait que si rien de factuel ne reste en suspens.
            if any(i.get("type") == "fait" for i in blocking):
                raise RuntimeError("le script contient encore des problèmes factuels après correction : " + "; ".join(i["problem"] for i in blocking))
            log.warning("  script accepté avec %d remarque(s) non factuelle(s) restante(s)", len(issues))
            break
        script = revise(cfg, llm, dossier, script, issues)
    script["topic"] = topic["title"]
    (workdir / "script.json").write_text(_dump(script), encoding="utf-8")
    write_storyboard_md(script, workdir / "storyboard.md")
    return script


def revise(cfg: dict, llm: LLM, dossier: dict, script: dict, issues: list[dict]) -> dict:
    sc = cfg["script"]
    new = llm.json(
        prompt(
            "revise",
            facts=facts_block(dossier),
            script=_dump(script),
            issues="\n".join(f"- scène {i.get('scene', '?')} [{i.get('severity')}/{i.get('type')}] {i.get('problem')} → {i.get('fix', '')}" for i in issues),
            min_words=sc["min_words"],
            max_words=sc["max_words"],
        ),
        system=system_prompt(),
    )
    return normalize(new)


def write_storyboard_md(script: dict, path: Path) -> None:
    lines = [f"# {script.get('title', '')}", "", f"Ambiance : {script['mood']} · couleur d'accent : {script['accent_color']} · {narration_words(script)} mots", ""]
    for s in script["scenes"]:
        lines += [
            f"## Scène {s['id']} — {s['section']} ({s['type']})",
            "",
            f"**Narration :** {s['narration']}",
            "",
            f"- Visuel : {s['visual_description']}",
            f"- Prompt image : `{s['image_prompt']}`",
            f"- Prompt animation : `{s['animation_prompt']}`",
            f"- Caméra : {s['camera']} · lumière : {s['lighting']} · transition : {s['transition']}",
            f"- Mots-clés : {', '.join(s['keywords']) or '—'} · faits : {', '.join(s['facts']) or '—'}",
        ]
        if s.get("overlay"):
            lines.append(f"- Incrustation : {s['overlay']['text']} {('/ ' + s['overlay']['sub']) if s['overlay']['sub'] else ''}")
        if s.get("stat"):
            lines.append(f"- Statistique : {s['stat']}")
        if s.get("map"):
            lines.append(f"- Carte : {s['map']}")
        lines.append("")
    soc = script.get("social", {})
    lines += ["## Publication", "", f"**{soc.get('title', '')}**", "", soc.get("description", ""), "", " ".join(soc.get("hashtags", []))]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
