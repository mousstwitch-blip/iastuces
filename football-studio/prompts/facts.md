Sujet : « {{topic}} »
Angle : {{angle}}
Date du jour : {{today}}

Voici des extraits de sources. Chaque source a un identifiant entre crochets.

{{sources}}

{{news}}

Ta mission : établir la FICHE DE FAITS VÉRIFIÉS qui servira à écrire la vidéo.

Règles :
1. N'inscris que des faits présents dans les sources ci-dessus{{web_rule}}.
2. Pour chaque fait, cite les identifiants des sources qui le soutiennent.
3. `status` :
   - "confirme" : au moins deux sources indépendantes concordent (ex. Wikipédia fr ET en, ou Wikipédia ET un site de presse).
   - "source_unique" : une seule source, sans contradiction.
   - "incertain" : sources contradictoires, légende, rumeur, chiffre disputé, formulation vague.
4. Vérifie soigneusement dates, scores, montants, âges, noms propres. Si deux sources divergent, note-le dans `contradictions` et classe le fait "incertain".
5. Ne présente jamais une hypothèse comme un fait : indique-le dans `note`.
6. Vise 15 à 25 faits, dont ceux qui portent l'émotion et la surprise de l'histoire.
7. Si les sources ne suffisent pas à raconter une histoire solide, mets "sufficient": false.

Format JSON :
{"sufficient": true, "summary": "résumé factuel en 3 phrases", "facts": [{"id": "F1", "claim": "fait précis et autonome", "sources": ["S1", "S3"], "status": "confirme", "note": ""}], "contradictions": ["..."], "extra_sources": [{"id": "W1", "title": "...", "url": "https://..."}]}

`extra_sources` : uniquement les pages web que tu as réellement consultées en plus (sinon liste vide).
