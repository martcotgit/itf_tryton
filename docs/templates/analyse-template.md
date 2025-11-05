# Prompt – Analyse d'implémentation

## Usage rapide
- Déclencher ce prompt une fois le brief validé et avant toute implémentation.
- Coller le prompt puis le modèle Markdown (bloc suivant) dans la même demande.
- (Optionnel) Ajoute en fin de prompt des notes complémentaires si tu veux transmettre de nouvelles informations. Supprime la section optionnelle si tu n'as rien à ajouter.

## Prompt (à copier-coller avant le modèle)
```text
analysis {{TASK_ID}}

Tu es lead développeur. En t'appuyant sur le brief `docs/taches/{{TASK_ID}}/brief.md`, rédige une analyse complète en suivant le modèle donné.

Consignes :
1. Si le dossier `docs/taches/{{TASK_ID}}/` n'existe pas, crée-le.
2. Crée ou remplace le fichier `docs/taches/{{TASK_ID}}/{{TASK_ID}}-analyse.md` avec le modèle rempli.
3. Suivre le modèle Markdown qui suit ce bloc.
4. Si des informations manquent dans le brief, les signaler dans la section « Questions ouvertes / décisions ».
5. Proposer un plan d'implémentation en étapes numérotées.
6. Documenter les risques, dépendances et commandes de diagnostic.

Cahier des charges additionnel (optionnel) :
{{NotesComplementaires}}

Copie également le modèle Markdown situé après ce bloc avant d'envoyer ta demande.
```

## Modèle Markdown à remplir
```markdown
# Analyse {{TASK_ID}} – {{TASK_TITLE}}

- **Fiche mission**: `docs/taches/{{TASK_ID}}/brief.md`
- **Date**: {{DATE}}
- **Auteur**: {{AUTHOR}}

## Contexte et objectifs
- {{ContexteResume}}
- {{ObjectifsPrincipaux}}

## État actuel / inventaire
- **Commandes à lancer**: `{{Commandes}}`
- **Fichiers / dossiers clefs**:
  - `{{Chemin1}}` — {{Notes1}}
  - `{{Chemin2}}` — {{Notes2}}
- **Dépendances critiques**:
  - {{Paquet1}} — version actuelle {{VersionActuelle1}} / cible {{VersionCible1}}
  - {{Paquet2}} — version actuelle {{VersionActuelle2}} / cible {{VersionCible2}}

## Risques et compatibilités
- {{Risque1}}
- {{Risque2}}
- {{Risque3}}

## Plan d'implémentation
1. {{Etape1}}
2. {{Etape2}}
3. {{Etape3}}

## Questions ouvertes / décisions
- {{Question1}}
- {{Decision1}}

## Journal (à compléter pendant l'exécution)
- **Commandes lancées**:
  - `{{Commande}}` — {{Resultat}}
- **Tests exécutés**:
  - `{{Test}}` — {{Statut}}
- **Notes libres**: {{Notes}}
```
