# MH370 — Pourquoi un avion disparaît des radars

Mini-documentaire TikTok de 60 s · 1080×1920 · 30 fps · Remotion + React + TypeScript + Three.js.
Le storyboard, la narration et les sources sont dans [`STORYBOARD.md`](STORYBOARD.md).

## Pipeline

```bash
npm i

# 1. Voix off : un WAV par phrase + durations.json (Kokoro TTS, voix ff_siwis ×1,2)
python3 scripts/tts_gen.py <kokoro_dir> scripts/narration.json <dir> 1.2
# 2. Placement sur 60 s → src/data/timeline.json + public/audio/vo.wav
python3 scripts/build_timeline.py <dir>
python3 scripts/vo_envelope.py          # forme d'onde (scène « Bonne nuit »)
# 3. Musique + sound design synthétisés, mixage (−14 LUFS) → public/audio/mix.wav
python3 scripts/build_audio.py
# 4. Rendu, puis grain argentique + audio WAV (ffmpeg)
npx remotion render MH370 out/MH370_raw.mp4
scripts/finish.sh out/MH370_raw.mp4 out/MH370_final.mp4
```

Prévisualisation : `npm run dev` (Remotion Studio). Chaque scène est aussi enregistrée seule, dans le dossier « Scenes ».

Si la voix off change, relance `build_timeline.py` : les scènes, les sous-titres et les effets sonores suivent automatiquement les nouvelles durées.

## Structure

- `src/Documentary.tsx` : timeline, transitions, sous-titres et piste audio.
- `src/scenes/S01…S10` : une scène par séquence du storyboard.
- `src/components` : écran radar, sous-titres karaoké, typographie, perte de signal, vignette.
- `src/three` : globe photoréaliste avec shader jour/nuit et atmosphère, avion de ligne procédural, mer de nuages, satellite et sphère de portée.
- `scripts/` : timeline, mixage audio, extraction géographique, bathymétrie procédurale, finition ffmpeg.

## Licences des assets

| Asset | Source | Licence |
|---|---|---|
| Textures de la Terre (Blue Marble, Black Marble) | NASA, via le paquet npm `three-globe` | Domaine public (NASA) |
| Frontières et côtes | Natural Earth 1:10m, via `world-atlas` | Domaine public |
| Polices Inter Tight, JetBrains Mono | `@fontsource` | SIL OFL 1.1 |
| Voix off | Kokoro-82M (`kokoro-onnx`) | Apache 2.0 |
| Musique et effets sonores | Synthétisés par `scripts/build_audio.py` | Originaux |
| Avion, satellite, nuages, fond marin | Générés procéduralement | Originaux |

Le fond marin de la séquence 8 est **simulé** (illustration, mentionné à l'écran). Le tracé radar de la séquence 5 est **simplifié** (mentionné à l'écran). Les routes aériennes de la séquence 9 sont **illustratives** (mentionné à l'écran).

## Environnement de rendu

`remotion.config.ts` pointe vers le Chromium headless préinstallé et utilise WebGL logiciel (`swangle`). Sur une autre machine, définis `REMOTION_BROWSER` ou supprime `setBrowserExecutable`.
