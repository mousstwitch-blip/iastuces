Tu es le rédacteur en chef. Contrôle ce script de mini-documentaire football AVANT production. Sois exigeant.

FICHE DE FAITS VÉRIFIÉS :
{{facts}}

SCRIPT :
{{script}}

CONTRÔLES AUTOMATIQUES DÉJÀ EFFECTUÉS (à corriger s'ils signalent un problème) :
{{auto_issues}}

Vérifie :
1. FAITS — chaque affirmation de la narration est-elle soutenue par la fiche ? Dates, chiffres, noms exacts ? Un fait "incertain" est-il présenté comme certain ? (bloquant)
2. LANGUE — fautes d'orthographe, de grammaire, de conjugaison. (bloquant)
3. COHÉRENCE — l'histoire se comprend-elle sans connaissance préalable ? Chronologie claire ?
4. HOOK — la première phrase arrête-t-elle le défilement en 2 secondes ? (note sur 10)
5. RYTHME — répétitions, phrases trop longues, temps morts, conclusion avec question.
6. VISUELS — chaque image_prompt correspond-il précisément à sa narration ? Contient-il un nom de personne réelle, de club, de marque ou du texte à afficher ? (bloquant)

Format JSON :
{"hook_score": 0-10, "overall_score": 0-100, "issues": [{"scene": 1, "severity": "bloquant|mineur", "type": "fait|langue|coherence|hook|rythme|visuel", "problem": "...", "fix": "correction précise"}], "verdict": "ok|revise"}

verdict = "ok" seulement s'il n'y a aucun problème bloquant, hook_score ≥ 7 et overall_score ≥ 80.
