Tu es directeur artistique d'un mini-documentaire football. Les images jointes (dans l'ordre) illustrent ces scènes :

{{scenes}}

Pour CHAQUE image, contrôle :
- correspondance avec la narration et la description voulue ;
- défauts visibles : anatomie (mains, jambes, visages déformés), objets absurdes, texte ou lettres parasites, filigrane, football AMÉRICAIN au lieu de soccer, ballon non rond ;
- continuité artistique avec les autres (réalisme photo, ton cinématographique).

Sois pragmatique : une image d'ambiance correcte est acceptable ; ne rejette que les vrais problèmes qu'un spectateur remarquerait.

Format JSON :
{"images": [{"scene": 1, "ok": true, "score": 0-10, "problem": "", "new_prompt": "si rejetée : NOUVEAU prompt complet EN ANGLAIS (35-60 mots)"}]}

`new_prompt` : le générateur gratuit échoue sur les groupes de personnes, les mains, les gestes et les maillots floqués. Propose donc un concept plus simple à dessiner MAIS toujours propre à cette histoire : un personnage unique de dos ou en silhouette, une foule lointaine, un lieu ou un objet précis de la scène racontée, en gardant le pays, l'époque et les couleurs indiqués dans le prompt d'origine. Évite le ballon ou le stade seul. Écris « soccer », aucun nom réel, aucun texte.
