# Avancement

## Fait
- Code complet du studio (voir README.md), commité et poussé.
- Test court bout-en-bout (4 scènes) : voix, images, mixage, rendu, inspection OK.

## État au moment de la pause (demandée par l'utilisateur)
Projet `projects/20261114-149-0-le-match-ou-une-equipe-a-marque-contre-son/` :
- fait : sujet, research.json + sources.md (28 faits, 11 sources), script.json validé (13 scènes, 181 mots, 88/100).
- interrompu à : voix off → 67,9 s, trop long ; il faut retirer ~22 mots (correction automatique à la reprise).
- pas encore fait : images IA, mixage, rendu, inspection du MP4.

## Prochaine étape (sur ordre)
`python main.py --resume 20261114-149-0-le-match-ou-une-equipe-a-marque-contre-son`
puis regarder planche-contact + qc_report.json, corriger les vrais défauts seulement.

## Reprise après interruption
`python main.py --resume <dossier de projects/>` réutilise recherche, script et images existants.
