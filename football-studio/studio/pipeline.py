"""Chef d'orchestre : du sujet à la vidéo finale, avec boucle d'auto-correction."""
from __future__ import annotations

import datetime as dt
import json
import logging
import shutil
import time
from pathlib import Path

from . import images, qc, render, research, sound, tts, writer
from .config import DIRS, ROOT, slugify
from .llm import LLM, get_llm

log = logging.getLogger("studio")


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _save(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


class Project:
    def __init__(self, slug: str):
        self.slug = slug
        self.dir = DIRS["projects"] / slug
        self.images = DIRS["images"] / slug
        self.audio = DIRS["audio"] / slug
        for d in (self.dir, self.images, self.audio):
            d.mkdir(parents=True, exist_ok=True)


# ───────────────────────────── Étapes ─────────────────────────────
def step_topic(cfg: dict, llm: LLM, topic: str | None, category: str | None) -> tuple[Project, dict]:
    """Choisit (ou reçoit) le sujet puis constitue le dossier de faits vérifiés."""
    if topic:
        log.info("① Sujet imposé : %s", topic)
        candidates = [research.plan_topic(llm, topic)]
    else:
        log.info("① Recherche d'un sujet…")
        candidates = research.find_topic(llm, category)
        for c in candidates[:5]:
            log.info("   · %s/100 — %s", c.get("score", "?"), c["title"])
    last_error = "aucun candidat"
    for cand in candidates[:3]:
        proj = Project(dt.date.today().strftime("%Y%m%d") + "-" + slugify(cand["title"]))
        _save(proj.dir / "topic.json", cand)
        log.info("② Recherche et vérification : %s", cand["title"])
        try:
            dossier = research.build_dossier(cfg, llm, cand, proj.dir)
        except RuntimeError as e:
            last_error = str(e)
            log.warning("   %s", e)
            continue
        if dossier["sufficient"]:
            return proj, dossier
        last_error = f"documentation insuffisante pour « {cand['title']} »"
        log.warning("   %s — sujet suivant", last_error)
    raise RuntimeError(f"impossible de documenter un sujet de façon fiable ({last_error})")


def build_timeline(cfg: dict, script: dict, voice: dict, proj: Project) -> dict:
    """Cale chaque scène sur la durée réelle de sa voix off."""
    gap = float(cfg["tts"]["gap"])
    by_id = {v["id"]: v for v in voice["scenes"]}
    scenes, words, cursor = [], [], 0.0
    n = len(script["scenes"])
    # respirations : plus longues aux changements de section et avant la dernière phrase
    gaps = []
    for i, s in enumerate(script["scenes"][:-1]):
        nxt = script["scenes"][i + 1]
        gaps.append(float(cfg["tts"].get("final_gap", gap)) if i + 1 == n - 1 else float(cfg["tts"].get("section_gap", gap)) if nxt["section"] != s["section"] else gap)
    for i, s in enumerate(script["scenes"]):
        v = by_id[s["id"]]
        vo_start = cursor + (0.10 if i == 0 else gaps[i - 1] / 2)
        end = vo_start + v["duration"] + (1.7 if i == n - 1 else gaps[i] / 2)
        minimum = {"stat": 3.2, "map": 3.8 if (s.get("map") or {}).get("route") else 3.2}.get(s["type"], 1.6)
        end = max(end, cursor + minimum)
        depth = proj.images / f"scene_{s['id']:02d}_depth.png"
        scenes.append({
            "id": s["id"], "section": s["section"], "type": s["type"], "start": round(cursor, 3), "end": round(end, 3), "vo_start": round(vo_start, 3),
            "camera": s["camera"], "transition": s["transition"], "narration": s["narration"], "overlay": s.get("overlay"), "stat": s.get("stat"), "map": s.get("map"),
            "route": bool((s.get("map") or {}).get("route")), "image": str(proj.images / f"scene_{s['id']:02d}.jpg"), "depth": str(depth) if depth.exists() else None,
        })
        kw = {render._norm(tok) for k in s.get("keywords", []) for tok in k.split() if len(render._norm(tok)) > 2}
        for w in v["words"]:
            words.append({"text": w["text"], "start": round(vo_start + w["start"], 3), "end": round(vo_start + w["end"], 3), "scene": s["id"], "keyword": render._norm(w["text"]) in kw})
        cursor = end
    duration = round(cursor, 3)
    # transitions choisies selon la dramaturgie (et jamais deux fois la même de suite)
    cycles = {"contexte": ["whip", "fade"], "developpement": ["whip", "zoom", "cut"], "rebondissement": ["flash", "zoom"], "conclusion": ["fade"]}
    for i, sc in enumerate(scenes[:-1]):
        nxt = scenes[i + 1]["section"]
        if sc["section"] == "hook":
            sc["transition"] = "flash"
        elif nxt == "rebondissement" and sc["section"] != "rebondissement":
            sc["transition"] = "glitch"
        elif nxt == "conclusion":
            sc["transition"] = "fade"
        else:
            c = cycles.get(sc["section"], ["fade"])
            sc["transition"] = c[i % len(c)]
    marks = {}
    for sec, frac in (("contexte", 0.06), ("developpement", 0.25), ("rebondissement", 0.68), ("conclusion", 0.88)):
        first = next((sc["start"] for sc in scenes if sc["section"] == sec), None)
        marks[sec] = first if first is not None else duration * frac
    tl = {"width": cfg["video"]["width"], "height": cfg["video"]["height"], "fps": cfg["video"]["fps"], "duration": duration,
          "accent": script["accent_color"], "mood": script["mood"], "marks": marks, "scenes": scenes, "words": words}
    _save(proj.dir / "timeline.json", tl)
    return tl


def step_voice(cfg: dict, llm: LLM, dossier: dict, script: dict, proj: Project) -> tuple[dict, dict, dict]:
    """Voix off + calage. Corrige la durée (débit, puis réécriture) jusqu'à tenir dans 55-65 s."""
    vc = cfg["video"]
    rate = cfg["tts"]["edge_rate"]
    voice = tts.synthesize(cfg, script, proj.audio, rate)
    tl = build_timeline(cfg, script, voice, proj)
    for attempt in range(1, 4):
        dur = tl["duration"]
        if vc["min_duration"] + 0.5 <= dur <= vc["max_duration"] - 0.5:
            break
        speech = voice["speech_total"]
        factor = speech / max(1.0, speech - (dur - vc["target_duration"]))
        new_rate = tts.shift_rate(rate, factor)
        pct = int(new_rate.rstrip("%"))
        log.info("   durée %.1f s hors cible → correction %d", dur, attempt)
        if -14 <= pct <= 12:
            rate = new_rate
            log.info("   ajustement du débit de la voix : %s", rate)
        else:
            delta = round((dur - vc["target_duration"]) * writer.WORDS_PER_SECOND)
            issue = {"scene": 0, "severity": "bloquant", "type": "rythme",
                     "problem": f"la narration dure {dur:.0f} s à voix haute au lieu de {vc['target_duration']:.0f} s",
                     "fix": (f"retirer environ {delta} mots" if delta > 0 else f"ajouter environ {-delta} mots de faits issus de la fiche") + " sans changer la structure ni les visuels des scènes conservées"}
            log.info("   réécriture du script : %s", issue["fix"])
            script = writer.revise(cfg, llm, dossier, script, [issue])
            script["topic"] = dossier["topic"]["title"]
            auto = [i for i in writer.auto_check(script, cfg, dossier) if i["severity"] == "bloquant" and i["type"] == "fait"]
            if auto:
                raise RuntimeError("la réécriture a introduit un problème factuel : " + auto[0]["problem"])
            _save(proj.dir / "script.json", script)
            writer.write_storyboard_md(script, proj.dir / "storyboard.md")
        voice = tts.synthesize(cfg, script, proj.audio, rate)
        tl = build_timeline(cfg, script, voice, proj)
    log.info("   durée de la vidéo : %.1f s", tl["duration"])
    return script, voice, tl


def step_images(cfg: dict, llm: LLM, script: dict, proj: Project, only: dict[int, str] | None = None) -> None:
    images.produce_images(cfg, llm, script, proj.images, proj.dir, only)
    if cfg["render"].get("depth_parallax") and images.depth_available():
        for s in script["scenes"]:
            if s["type"] == "image":
                images.depth_map(proj.images / f"scene_{s['id']:02d}.jpg", proj.images / f"scene_{s['id']:02d}_depth.png")


# ───────────────────────────── Corrections ─────────────────────────────
def plan_fixes(report: dict, script: dict | None = None) -> dict:
    """Traduit les problèmes détectés en actions de correction ciblées."""
    plan = {"regen": {}, "remix": None, "captions": False, "retime": False, "rerender": False, "unfixable": []}
    for i in report["issues"]:
        if i["severity"] != "bloquant":
            continue
        typ, scene = i["type"], i.get("scene")
        kinds = {s["id"]: s["type"] for s in (script or {}).get("scenes", [])}
        texte = any(w in i["detail"].lower() for w in ("glyphe", "caractère", "police", "emoji", "texte", "titre", "sous-titre"))
        if typ in ("noir", "defaut_image", "incoherence", "fige") and scene and kinds.get(int(scene), "image") == "image" and not texte:
            plan["regen"][int(scene)] = "clear well-lit subject, coherent anatomy, correct soccer scene" if typ != "noir" else "bright, well exposed, clearly lit scene"
        elif typ == "voix_couverte":
            plan["remix"] = 0.7
        elif typ in ("loudness", "audio"):
            plan["remix"] = plan["remix"] or 1.0
        elif typ in ("sous_titres", "coupe"):
            plan["captions"] = True
        elif typ == "duree":
            plan["retime"] = True
        elif typ in ("format", "sync"):
            plan["rerender"] = True
        else:
            plan["unfixable"].append(i)
    return plan


# ───────────────────────────── Pipeline complet ─────────────────────────────
def run(cfg: dict, topic: str | None = None, category: str | None = None, resume: str | None = None) -> Path:
    t0 = time.time()
    llm = get_llm(cfg)

    if resume:
        proj = Project(resume)
        dossier = _load(proj.dir / "research.json")
        if dossier is None:
            raise RuntimeError(f"projet « {resume} » introuvable ou sans dossier de recherche")
        log.info("Reprise du projet %s", resume)
    else:
        proj, dossier = step_topic(cfg, llm, topic, category)

    script = _load(proj.dir / "script.json")
    if script is None:
        log.info("③ Écriture du script et du storyboard (contrôle n°1)…")
        script = writer.write_script(cfg, llm, dossier, proj.dir)
    log.info("   « %s » — %d scènes, %d mots, ambiance %s", script.get("title"), len(script["scenes"]), writer.narration_words(script), script["mood"])

    log.info("④ Voix off…")
    script, voice, tl = step_voice(cfg, llm, dossier, script, proj)

    log.info("⑤ Visuels IA (contrôle n°2)…")
    step_images(cfg, llm, script, proj)
    tl = build_timeline(cfg, script, voice, proj)

    log.info("⑥ Musique, bruitages et mixage…")
    mix_path = proj.audio / "mix.wav"
    music_gain = 1.0
    mix_stats = sound.mix_all(cfg, voice, tl["scenes"], tl["marks"], tl["duration"], tl["mood"], mix_path, music_gain)

    history = []
    max_cycles = int(cfg["qc"]["max_correction_cycles"])
    video = None
    for cycle in range(0, max_cycles + 1):
        tag = f"v{cycle + 1}"
        log.info("⑦ Montage et export (%s)…", tag)
        video = render.render_video(tl, cfg, mix_path, proj.dir / f"montage_{tag}.mp4", proj.dir)
        log.info("⑧ Inspection de la vidéo exportée (contrôles n°3 et n°4)…")
        report = qc.inspect(video, tl, cfg, proj.dir, mix_stats, llm, tag)
        report["cycle"] = cycle
        m = report["metrics"]
        log.info("   %s×%s · %s i/s · %.1f s · %s LUFS · %d image(s) de contrôle · %d problème(s)", m.get("width"), m.get("height"), m.get("fps"), m.get("duration", 0), m.get("lufs"), len(m.get("control_frames", [])), len(report["issues"]))
        for i in report["issues"]:
            log.info("   %s [%s] %s", "✗" if i["severity"] == "bloquant" else "·", i["type"], i["detail"])
        history.append(report)
        _save(proj.dir / "qc_report.json", history)
        if report["ok"]:
            log.info("   ✔ vidéo conforme")
            break
        if cycle == max_cycles:
            log.warning("   limite de %d cycles de correction atteinte", max_cycles)
            break
        plan = plan_fixes(report, script)
        report["fix_plan"] = {k: v for k, v in plan.items() if v}
        _save(proj.dir / "qc_report.json", history)
        if not any([plan["regen"], plan["remix"], plan["captions"], plan["retime"], plan["rerender"]]):
            log.warning("   problèmes sans correction automatique : %s", [u["detail"] for u in plan["unfixable"]])
            break
        log.info("⑨ Correction automatique (cycle %d/%d)…", cycle + 1, max_cycles)
        if plan["retime"]:
            log.info("   → recalage de la durée")
            script, voice, tl = step_voice(cfg, llm, dossier, script, proj)
            plan["remix"] = plan["remix"] or music_gain
        if plan["regen"]:
            log.info("   → régénération des images des scènes %s", sorted(plan["regen"]))
            step_images(cfg, llm, script, proj, only=plan["regen"])
        if plan["captions"]:
            cfg["captions"]["size"] = int(cfg["captions"]["size"] * 0.9)
            cfg["captions"]["y_ratio"] = min(float(cfg["captions"]["y_ratio"]), 0.68)
            log.info("   → sous-titres réduits à %d px", cfg["captions"]["size"])
        tl = build_timeline(cfg, script, voice, proj)
        if plan["remix"]:
            music_gain *= plan["remix"]
            log.info("   → nouveau mixage (musique × %.2f)", music_gain)
            mix_stats = sound.mix_all(cfg, voice, tl["scenes"], tl["marks"], tl["duration"], tl["mood"], mix_path, music_gain)

    final = DIRS["videos"] / f"{proj.slug}.mp4"
    shutil.copyfile(video, final)
    report = history[-1]
    write_publication(script, dossier, report, final)
    research.save_history(dossier["topic"]["title"])
    for old in proj.dir.glob("montage_v*.mp4"):
        old.unlink()
    status = "CONFORME" if report["ok"] else "À VÉRIFIER (problèmes restants, voir qc_report.json)"
    log.info("━━ Terminé en %.0f s — %s", time.time() - t0, status)
    log.info("   Vidéo      : %s", final.relative_to(ROOT))
    log.info("   Publication: %s", final.with_suffix(".txt").relative_to(ROOT))
    log.info("   Dossier    : %s (script, storyboard, sources, rapports, planche-contact)", proj.dir.relative_to(ROOT))
    return final


def write_publication(script: dict, dossier: dict, report: dict, final: Path) -> None:
    """Pack de publication prêt à copier-coller (TikTok / Instagram / YouTube Shorts)."""
    soc = script.get("social", {})
    m = report["metrics"]
    tags = [t if t.startswith("#") else "#" + t for t in soc.get("hashtags", [])]
    for t in ("#football", "#foot", "#histoiredufoot"):
        if t.lower() not in [x.lower() for x in tags]:
            tags.append(t)
    question = script["scenes"][-1]["narration"] if script.get("scenes") else ""
    title = soc.get("title") or script.get("title", "")
    desc = soc.get("description", "")
    srcs = [s["title"] for s in dossier["sources"]]
    blocking = [i["detail"] for i in report["issues"] if i["severity"] == "bloquant"]
    lines = [
        "═══ TIKTOK / INSTAGRAM REELS ═══",
        desc,
        "",
        " ".join(tags[:10]),
        "",
        "═══ YOUTUBE SHORTS ═══",
        "Titre : " + title[:95],
        "",
        desc,
        "",
        "Sources : " + "; ".join(srcs[:6]),
        ("Illustrations générées par IA et photos (crédits photo : à compléter). " if any((ROOT / "photos" / final.stem).glob("scene_*.*")) else "Images générées par IA (illustrations). ") + "Musique et bruitages originaux.",
        "",
        " ".join(["#Shorts"] + tags[:4]),
        "",
        "═══ COMMENTAIRE À ÉPINGLER ═══",
        question,
        "",
        "═══ AVANT DE PUBLIER ═══",
        "- Activer l'étiquette « contenu généré par IA » sur chaque plateforme.",
        "- Relire les faits : projects/" + final.stem + "/sources.md",
        "",
        "═══ SOURCES COMPLÈTES ═══",
    ]
    lines += [f"{s['title']} : {s['url']}" for s in dossier["sources"]]
    lines += ["", "═══ CONTRÔLE QUALITÉ ═══",
              f"{m.get('width')}×{m.get('height')}, {m.get('fps')} i/s, {m.get('duration', 0):.1f} s, {m.get('lufs')} LUFS, {m.get('size_mb')} Mo",
              "Statut : " + ("conforme" if not blocking else "à vérifier — " + "; ".join(blocking))]
    final.with_suffix(".txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
