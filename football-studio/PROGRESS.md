# Avancement

## Fait
- Code complet du studio (voir README.md), commité et poussé.
- Test court bout-en-bout (4 scènes) : voix, images, mixage, rendu, inspection OK.

## Première vidéo terminée
`videos/20261114-149-0-le-match-ou-une-equipe-a-marque-contre-son.mp4` — 1080×1920, 30 i/s, 61,2 s, −14,1 LUFS, 29 Mo.
Inspection mesurée : aucun problème. Planche-contact relue : `projects/<projet>/planche_contact_manual.jpg`.

## Défauts connus à traiter (par ordre d'intérêt)
1. Images IA faibles sur les scènes 3, 4, 6, 8, 11 (Pollinations gratuit) : joueurs à l'allure de rugbymen, flocage illisible, scène 11 peu lisible.
2. Boucle de correction : un défaut de texte (glyphe manquant) a été traité comme un défaut d'image → régénérations inutiles. Corrigé à la source (caractères filtrés), mais le tri des problèmes reste à affiner.
3. Sous-titre sur deux lignes trop proche du bandeau du titre pendant le hook.
4. Sous-titres d'incrustation rouges (couleur d'accent) petits et peu contrastés.
5. Plan final statique (7 s) ; la question finale mériterait un grand texte.

## Outils
- `python main.py --resume <projet>` : reprise complète (appelle l'IA).
- `python scripts/rerender.py <projet>` : refait seulement montage + inspection (aucun appel IA, ~3 min).
