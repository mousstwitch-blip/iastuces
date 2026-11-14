Écris le script et le storyboard d'un mini-documentaire football vertical de 60 secondes.

Sujet : « {{topic}} »
Angle : {{angle}}

FICHE DE FAITS VÉRIFIÉS (ta seule source autorisée) :
{{facts}}

RÈGLES FACTUELLES
- Chaque affirmation de la narration doit reposer sur un fait de la fiche ; indique les identifiants dans `facts`.
- Les faits "incertain" sont interdits, sauf formulés explicitement comme incertains (« selon la légende », « aurait »).
- N'invente ni citation, ni chiffre, ni date, ni détail.

STRUCTURE NARRATIVE (durées indicatives)
- hook (0-3 s) : UNE phrase de 12 mots maximum, extrêmement intrigante, sans « Saviez-vous », sans « Aujourd'hui ».
- contexte (3-15 s) : qui, où, quand.
- developpement (15-40 s) : révélations progressives, chaque scène relance la curiosité.
- rebondissement (40-53 s) : le moment le plus surprenant ou émouvant.
- conclusion (53-60 s) : chute mémorable + UNE question ouverte qui appelle les commentaires (dernière phrase, terminée par « ? »).

STYLE
- Narration orale, naturelle, au présent de narration de préférence. Phrases courtes (20 mots maximum). Aucun temps mort, aucune répétition.
- Total : entre {{min_words}} et {{max_words}} mots (≈ 60 s à voix haute). C'est impératif.
- 10 à 13 scènes de 3 à 7 secondes ; une idée par scène.
- Écris les nombres comme on veut les entendre (« 1958 » convient, « 2-1 » s'écrit « deux buts à un »).

VISUELS (un par scène, précisément lié à ce qui est dit)
- `type` : "image" (photo IA animée), "stat" (grand chiffre animé sur image), "map" (carte animée : lieu ou trajet).
  Utilise au moins une scène "stat" et, si l'histoire comporte un lieu ou un voyage marquant, une scène "map". Les autres sont "image".
- `image_prompt` : EN ANGLAIS, 35 à 60 mots, description photographique concrète : sujet, action, décor, époque, cadrage, lumière, ambiance. Requis pour tous les types (il sert de fond aux scènes stat).
  * Écris « soccer » (jamais « football » seul) pour éviter le football américain.
  * N'utilise AUCUN nom de personne réelle, de club ou de marque : décris un joueur anonyme vu de dos, en silhouette, de loin ou en gros plan sur un détail (crampons, mains, maillot uni de la bonne couleur). Pas de visage reconnaissable, pas de logo, pas de texte dans l'image.
  * Reste fidèle à l'époque (matériel, tenues, stades, photo noir et blanc si années 1930-1950).
- `animation_prompt` : EN ANGLAIS, mouvement à donner à l'image si un moteur vidéo est disponible.
- `camera` : push_in | pull_out | pan_left | pan_right | tilt_up | tilt_down | orbit
- `lighting` : ambiance lumineuse en quelques mots (français).
- `transition` (vers la scène suivante) : cut | fade | flash | whip | zoom | glitch
- `keywords` : 1 à 3 mots de la narration à mettre en évidence dans les sous-titres (repris tels quels).
- `overlay` : texte court incrusté (date, lieu, nom) ou null. La scène 1 a toujours un overlay percutant de 2 à 5 mots.
- `stat` (type stat) : {"value": nombre, "prefix": "", "suffix": "", "label": "légende courte", "year": false} — valeur exacte issue de la fiche ; "year": true si la valeur est une année. Le suffixe est court (« M€ », « buts », « ans », « % »).
- `map` (type map) : {"points": [{"name": "Ville", "lat": 0.0, "lon": 0.0}], "route": true|false} — 1 ou 2 points ; route=true trace un trajet du premier au second.

Format JSON :
{"title": "...", "mood": "epic|dark|nostalgic|tension", "accent_color": "#RRGGBB",
 "scenes": [{"id": 1, "section": "hook", "narration": "...", "facts": ["F1"], "keywords": ["..."], "type": "image", "visual_description": "description en français", "image_prompt": "...", "animation_prompt": "...", "camera": "push_in", "lighting": "...", "transition": "flash", "overlay": {"text": "...", "sub": "..."}, "stat": null, "map": null}],
 "social": {"title": "titre de publication (≤ 80 caractères)", "description": "2 phrases + appel aux commentaires", "hashtags": ["#football", "..."]}}
