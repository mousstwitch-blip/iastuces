Tu es le réalisateur. L'image jointe est une planche-contact de la vidéo finale (vertical 9:16) : chaque vignette porte son horodatage. Voici le script, scène par scène, avec les temps :

{{scenes}}

Contrôle réellement ce que tu vois :
- la première vignette accroche-t-elle (titre lisible, image forte) ?
- écran noir, image vide ou figée par erreur ?
- texte coupé par les bords, sous-titres illisibles (trop petits, faible contraste, chevauchement avec un autre texte) ?
- image sans rapport avec la narration du moment ?
- rendu global professionnel et homogène ?

Format JSON :
{"score": 0-100, "issues": [{"time": 12.5, "scene": 3, "severity": "bloquant|mineur", "type": "noir|coupe|sous_titres|incoherence|defaut_image|autre", "problem": "..."}], "verdict": "ok|corriger"}

verdict = "corriger" seulement s'il existe au moins un problème bloquant qu'un spectateur remarquerait.
