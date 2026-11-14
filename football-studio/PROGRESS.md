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
