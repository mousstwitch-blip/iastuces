# Football Studio

Studio automatisé de mini-documentaires football : **une commande → une vidéo verticale de 60 s prête à publier** (TikTok, Reels, Shorts).

```bash
python main.py
```

Le studio trouve un sujet, vérifie les faits, écrit le script, génère les images, la voix, la musique, monte la vidéo, **inspecte réellement le MP4 exporté** et corrige ce qui ne va pas (3 cycles au maximum).

## Installation

Prérequis : Python ≥ 3.11 et [FFmpeg](https://ffmpeg.org/download.html).

```bash
cd football-studio
bash scripts/install.sh      # dépendances + création de .env + vérification
```

`python main.py --check` affiche à tout moment ce qui est installé et quel fournisseur sera utilisé.

## Utilisation

| Commande | Effet |
|---|---|
| `python main.py` | sujet choisi automatiquement |
| `python main.py --topic "La chute incroyable de Manchester United"` | sujet imposé |
| `python main.py --category "transferts historiques"` | sujet automatique dans une catégorie |
| `python main.py --resume 20261114-mon-projet` | reprend un projet interrompu (réutilise ce qui existe déjà) |
| `python main.py --no-vision` | sans contrôle visuel par IA (plus rapide) |
| `python main.py --provider pollinations` | force un fournisseur de texte |

Les tirets et guillemets typographiques collés depuis un téléphone (`–topic “…”`) sont acceptés.

Une vidéo demande environ 15 à 25 minutes sur 4 cœurs (dont ~4 min de rendu par export).

## Ce que fait une exécution

1. **Sujet** — 8 propositions notées, hors sujets déjà traités (`projects/history.json`).
2. **Recherche et vérification** — pages Wikipédia FR et EN (deux éditions indépendantes), titres Google Actualités pour la fraîcheur, et recherche web avec Claude Code. Chaque fait est classé *confirmé* (≥ 2 sources), *source unique* ou *incertain*. Si le dossier est trop mince, le sujet est abandonné pour le suivant.
3. **Script + storyboard** — hook, contexte, développement, rebondissement, conclusion ; un visuel, un mouvement de caméra et une transition par scène.
4. **Contrôle n°1 (script)** — contrôles automatiques (durée, structure, hook, répétitions, faits référencés, faits incertains au conditionnel) + relecture critique par l'IA, puis réécriture. Un script qui garde un problème factuel est refusé.
5. **Voix off** — une piste par scène, horodatage mot à mot. La durée est corrigée (débit, puis réécriture) jusqu'à tenir dans 55-65 s.
6. **Visuels + contrôle n°2** — génération, contrôle technique (noir, flou, uniforme), contrôle par vision IA (correspondance avec la narration, défauts, football américain…), régénération des images rejetées.
7. **Audio** — musique originale synthétisée selon l'ambiance, bruitages calés sur les transitions, ducking automatique sous la voix, normalisation à −14 LUFS.
8. **Montage** — caméra virtuelle et parallaxe 3D (carte de profondeur), chiffres animés, cartes animées, sous-titres mot à mot avec mots-clés en couleur, transitions, grain.
9. **Contrôles n°3 et n°4 (MP4 exporté)** — ffprobe (1080×1920, 30 i/s, H.264, AAC), détection d'écrans noirs, d'images figées, de silences, mesure du niveau sonore, rapport voix/musique, extraction d'images de contrôle, présence des sous-titres mesurée dans les images, planche-contact relue par vision IA.
10. **Contrôle n°5 (correction)** — chaque problème bloquant déclenche une action ciblée (régénérer l'image d'une scène, remixer, réduire les sous-titres, recaler la durée), puis nouvel export et nouvelle inspection.

## Où trouver les résultats

```
videos/<date>-<sujet>.mp4      vidéo finale
videos/<date>-<sujet>.txt      titre, description, hashtags, sources, bilan qualité
projects/<date>-<sujet>/       sources.md, research.json, script.json, storyboard.md,
                               script_qc.json, images_qc.json, qc_report.json,
                               planche_contact_v*.jpg, timeline.json
images/<date>-<sujet>/         images IA et cartes de profondeur
audio/<date>-<sujet>/          voix par scène, mixage final
logs/                          journal détaillé de chaque exécution
```

## Architecture

```
main.py              point d'entrée
config.toml          configuration centrale (format, voix, sous-titres, fournisseurs…)
.env                 clés API (jamais versionné) — modèle : .env.example
prompts/             consignes données à l'IA (modifiables sans toucher au code)
studio/
  llm.py             fournisseurs de texte : claude_cli, anthropic, openai, pollinations
  research.py        sujet, sources, fiche de faits
  writer.py          script, storyboard, contrôle n°1
  images.py          fournisseurs d'images, contrôle n°2, profondeur
  tts.py             voix : Edge TTS, Piper
  sound.py           musique, bruitages, mixage
  render.py          moteur de rendu image par image
  qc.py              inspection du MP4
  pipeline.py        enchaînement et boucle de correction
scripts/             install.sh, fetch_assets.py
assets/              polices (OFL), fond de carte (domaine public), modèles
```

Changer de fournisseur : ajouter une classe dans `llm.py`, `images.py` ou `tts.py` et l'inscrire dans le dictionnaire `PROVIDERS` (ou `get_engines`).

## Fournisseurs et clés API

Aucune clé n'est nécessaire avec la configuration par défaut.

| Rôle | Par défaut (gratuit) | Alternative | Clé |
|---|---|---|---|
| Texte, vérification, vision | commande `claude` (Claude Code, incluse dans ton abonnement) | API Anthropic | `ANTHROPIC_API_KEY` — console.anthropic.com → Settings → API keys |
| | | service compatible OpenAI | `OPENAI_API_KEY` — platform.openai.com/api-keys |
| | Pollinations (sans clé, qualité moindre, sans vision) | | |
| Images | Pollinations / Flux | gpt-image-1, avec `images.allow_paid = true` | `OPENAI_API_KEY` |
| Voix | Edge TTS, voix `fr-FR-HenriNeural` | Piper (hors-ligne, `pip install piper-tts`) | — |
| Musique, bruitages | synthèse intégrée | — | — |

Les clés se placent dans `.env` (copie de `.env.example`). Elles ne sont lues que depuis l'environnement, jamais écrites dans le code ni dans les journaux.

**État des tests.** Testés réellement de bout en bout : `claude_cli`, Pollinations (images), Edge TTS. Pollinations (texte) testé sur un appel simple. Les fournisseurs `anthropic`, `openai` (texte et images) et Piper sont implémentés mais **n'ont pas été testés**, faute de clé ou d'installation.

## Réseau

Hôtes contactés : `fr.wikipedia.org`, `en.wikipedia.org`, `news.google.com`, `image.pollinations.ai`, `text.pollinations.ai`, `speech.platform.bing.com`, et `huggingface.co` + `us.aws.cdn.hf.co` (une seule fois, modèle de profondeur de 99 Mo). Derrière un proxy, `HTTPS_PROXY` est respecté.

## Droits et éthique

- Images générées par IA : ce sont des **illustrations**, pas des archives. Les consignes interdisent les noms de personnes réelles, de clubs et de marques dans les prompts (joueurs de dos, silhouettes, détails) : pas de visage reconnaissable ni de logo.
- Aucune séquence de match, aucune musique ni son tiers : tout l'audio est synthétisé par `studio/sound.py`.
- Polices Anton, Bebas Neue, Montserrat : SIL OFL 1.1. Carte : Natural Earth (domaine public). Modèle Depth-Anything-V2-Small : Apache 2.0.
- TikTok, Instagram et YouTube demandent de signaler les contenus générés par IA : active l'étiquette à la publication.

## Limites connues

- **Pas de génération vidéo** : les plans sont des images IA animées (caméra, parallaxe, particules), pas des joueurs en mouvement. Les champs `animation_prompt` du storyboard sont prêts pour un moteur image→vidéo.
- **Qualité d'image** : Flux gratuit via Pollinations est en dessous des modèles payants (mains, détails, netteté). Le contrôle visuel régénère jusqu'à 3 fois, puis garde l'image en le signalant dans `images_qc.json`.
- **Vérification des faits** : elle réduit fortement le risque d'erreur mais ne le supprime pas. `sources.md` liste chaque fait avec ses sources : relis-le avant de publier, surtout pour un sujet d'actualité ou une personne vivante.
- **Écoute** : le niveau, les silences et le rapport voix/musique sont mesurés, mais aucune IA n'écoute la prononciation. Un nom propre étranger peut être mal prononcé par la voix.
- Sans `claude` ni clé Anthropic/OpenAI, les contrôles par vision sont désactivés (les contrôles mesurés restent actifs).
