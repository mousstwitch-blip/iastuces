# Avancement

## Fait
- Code complet du studio (voir README.md), commité et poussé.
- Test court bout-en-bout (4 scènes) : voix, images, mixage, rendu, inspection OK.

## Première vidéo terminée
`videos/20261114-149-0-le-match-ou-une-equipe-a-marque-contre-son.mp4` — 1080×1920, 30 i/s, 61,2 s, −14,1 LUFS, 29 Mo.
Inspection mesurée : aucun problème. Planche-contact relue : `projects/<projet>/planche_contact_manual.jpg`.

## Corrections faites (version 2 de la vidéo)
- Titre du hook borné en hauteur (plus de contact avec les sous-titres), sous-textes blancs et plus grands, question finale en grand.
- Images 3, 4, 6, 8, 11 régénérées avec des concepts simples ; le contrôle visuel propose désormais un nouveau prompt simplifié.
- Tri des corrections : un défaut de texte ne déclenche plus de régénération d'image.

## Défauts restants
- Scène 4 (penalty) : ballon imparfait, gardée avec réserve après 3 essais. Scène 6 : couloir sombre plutôt que vestiaire.
- Limite du générateur gratuit (Pollinations) : ballons parfois déformés, 503 occasionnels (secours procédural).
- Prononciation des noms propres non vérifiée à l'oreille.

## Outils
- `python main.py --resume <projet>` : reprise complète (appelle l'IA).
- `python scripts/rerender.py <projet>` : refait seulement montage + inspection (aucun appel IA, ~3 min).

## Vidéo n°2 (sujet Ali Dia) — interrompue
Limite d'usage Claude atteinte (« 5-hour limit », reprise à 19 h UTC) pendant la relecture du script.
Reprise : `python main.py --resume 20261114-il-appelle-un-club-en-se-faisant-passer-pour-geo` (recherche et brouillon conservés).
Vidéo de référence actuelle : celle du match 149-0 (version corrigée).

## Identité vocale (validée par l'utilisateur, à conserver pour toutes les vidéos)
Narrateur masculin français de France, grave, légèrement rauque, documentaire cinématographique.
Réglages dans `config.toml` [tts] : voix fr-FR-RemyMultilingualNeural, -4 %, -5 Hz, voice_color 0.35,
ton par section [tts.prosody] (mystérieux → calme → intense → émotionnel → final marquant), pauses plus longues aux changements de section.
Budget texte recalé : 125-145 mots (2,5 mots/s). Échantillon : assets/brand/echantillon_voix.mp3
