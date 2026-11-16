Écris le script et le storyboard d'un mini-documentaire football vertical de 60 secondes.

Sujet : « {{topic}} »
Angle : {{angle}}

FICHE DE FAITS VÉRIFIÉS (ta seule source autorisée) :
{{facts}}

RÈGLES FACTUELLES
- Chaque affirmation de la narration doit reposer sur un fait de la fiche ; indique les identifiants dans `facts`.
- Les faits "incertain" sont interdits, sauf formulés explicitement comme incertains (« selon la légende », « aurait »).
- N'invente ni citation, ni chiffre, ni date, ni détail.

OBJECTIF N°1 : LA RÉTENTION. Le spectateur doit rester jusqu'à la dernière seconde, puis revoir la vidéo.

STRUCTURE EN 5 ACTES (vidéo de 64 à 72 s ; `section` = nom de l'acte)
- hook — ACTE 1 (0-12 s) : la scène 1 est un choc (12 mots max : chiffre, score, paradoxe). Puis 2 ou 3 scènes qui posent l'énigme et PROMETTENT une révélation à la fin (« et la fin de l'histoire va vous glacer », « retenez ce chiffre »).
- contexte — ACTE 2 (12-24 s) : qui, où, quand. Sa DERNIÈRE scène finit par un cliffhanger (« Mais ce n'est pas le plus fou… », mini-question).
- developpement — ACTE 3 (24-38 s) : l'escalade. Sa dernière scène finit par un cliffhanger.
- rebondissement — ACTE 4 (38-50 s) : le tournant. Sa dernière scène finit par un cliffhanger.
- conclusion — ACTE 5 (50-70 s) : LA RÉVÉLATION promise à l'acte 1, puis une question ou un sondage pour les commentaires (« Team A ou team B ? »), puis la DERNIÈRE scène : une phrase de BOUCLE (12 mots max) qui se termine en rejoignant la première phrase de la vidéo, de sorte qu'en revoyant la vidéo la phrase 1 la prolonge naturellement.
  Exemple : 1re phrase « 149 buts. Tous contre son propre camp. » … dernière phrase « Et tout ça a commencé par un simple chiffre : »

DRAMATURGIE (impératif)
- Le hook pose une énigme (« comment ? », « pourquoi ? ») ; la réponse n'arrive qu'au rebondissement. Ne révèle jamais plus tôt l'issue de l'histoire.
- Progression de cause à effet : chaque scène découle de la précédente (« donc », « mais »), jamais une simple liste de faits.
- Chaque information n'est donnée qu'une fois. Chaque phrase est limpide pour quelqu'un qui ne connaît rien au sujet : on sait toujours qui fait quoi à qui.
- La tension monte jusqu'au rebondissement, puis le dénouement apporte la résolution.

STYLE
- Narration orale, naturelle, au présent de narration de préférence. Phrases courtes (20 mots maximum). Aucun temps mort, aucune répétition.
- Total : entre {{min_words}} et {{max_words}} mots (≈ 68 s à voix haute). C'est impératif.
- 16 à 20 scènes ; une idée par scène ; 14 mots maximum par scène (≈ 3 à 5 s) ; UNE PHRASE = UNE IDÉE, 12 mots maximum par phrase. Aucun temps mort.
- Écris les nombres comme on veut les entendre (« 1958 » convient, « 2-1 » s'écrit « deux buts à un »).

VISUELS (un par scène, précisément lié à ce qui est dit)
- `type` : "image" (photo IA animée), "stat" (grand chiffre animé sur image), "map" (carte animée : lieu ou trajet).
  Utilise au moins une scène "stat" et, si l'histoire comporte un lieu ou un voyage marquant, une scène "map". Les autres sont "image".
- `image_prompt` : EN ANGLAIS, 35 à 60 mots, description photographique concrète : sujet, action, décor, époque, cadrage, lumière, ambiance. Requis pour tous les types (il sert de fond aux scènes stat).
  * Écris « soccer » (jamais « football » seul) pour éviter le football américain.
  * N'utilise AUCUN nom de personne réelle, de club ou de marque : décris un joueur anonyme vu de dos, en silhouette, de loin ou en gros plan sur un détail (crampons, mains, maillot uni de la bonne couleur). Pas de visage reconnaissable, pas de logo, pas de texte dans l'image.
  * SPÉCIFIQUE AU SUJET : chaque image doit être reconnaissable comme appartenant à CETTE histoire. Chaque prompt précise le pays ou la ville (architecture, végétation, lumière, climat), l'époque (tenues, matériel, voitures, grain photo), les couleurs réelles des maillots, et un élément propre à la scène racontée (le lieu exact, l'objet, la situation).
  * Au maximum DEUX images dont le sujet est seulement un ballon, un stade ou un trophée. Deux scènes consécutives n'ont jamais le même sujet ni le même cadrage (alterne plans larges, plans moyens, gros plans ; intérieurs et extérieurs ; personnes et lieux).
  * Montre des humains en situation : un personnage unique vu de dos ou en silhouette, une foule vue de loin, des supporters de dos. Le générateur rate les groupes de joueurs en gros plan, les mains, les gestes précis et les numéros : évite-les. Maillots unis sans numéro.
  * Reste fidèle à l'époque (matériel, tenues, stades, photo noir et blanc si années 1930-1950).
- `animation_prompt` : EN ANGLAIS, mouvement à donner à l'image si un moteur vidéo est disponible.
- `camera` : push_in | pull_out | pan_left | pan_right | tilt_up | tilt_down | orbit
- `lighting` : ambiance lumineuse en quelques mots (français).
- `transition` (vers la scène suivante) : cut | fade | flash | whip | zoom | glitch
- `keywords` : 1 à 3 mots de la narration à mettre en évidence dans les sous-titres (repris tels quels).
- `overlay` : texte court incrusté (date, lieu, nom) ou null. La scène 1 a toujours un overlay percutant de 2 à 5 mots. La DERNIÈRE scène (boucle) reprend EXACTEMENT l'overlay `text` de la scène 1 (même chiffre ou score : dernière image = première image), avec `sub` = le sondage court (ex. « OUI OU NON ? »). Un overlay ou un mot-clé n'affirme jamais seul ce que la narration nuance (accusation, soupçon).
- `stat` (type stat) : {"value": nombre, "prefix": "", "suffix": "", "label": "légende courte", "year": false} — valeur exacte issue de la fiche ; "year": true si la valeur est une année. Le suffixe est court (« M€ », « buts », « ans », « % »).
- `map` (type map) : {"points": [{"name": "Ville", "lat": 0.0, "lon": 0.0}], "route": true|false} — 1 ou 2 points ; route=true trace un trajet du premier au second.

Format JSON :
{"title": "...", "mood": "epic|dark|nostalgic|tension", "accent_color": "#RRGGBB",
 "scenes": [{"id": 1, "section": "hook", "narration": "...", "facts": ["F1"], "keywords": ["..."], "type": "image", "visual_description": "description en français", "image_prompt": "...", "animation_prompt": "...", "camera": "push_in", "lighting": "...", "transition": "flash", "overlay": {"text": "...", "sub": "..."}, "stat": null, "map": null}],
 "social": {"title": "titre de publication (≤ 80 caractères)", "description": "2 phrases + appel aux commentaires", "hashtags": ["#football", "..."]}}
