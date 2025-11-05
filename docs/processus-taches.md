# Processus documenté pour les tâches

Cette page récapitule les quatre documents à générer pour chaque tâche ainsi que l'ordre d'utilisation des prompts.

## Vue d'ensemble
1. **Brief de tâche** : structure et objectifs globaux (`docs/templates/tache-template.md`).
2. **Analyse d'implémentation** : diagnostic technique et plan (`docs/templates/analyse-template.md`).
3. **Journal d'implémentation** : suivi des actions et décisions (`docs/templates/implementation-template.md`).
4. **Plan de test** : couverture QA et validations (`docs/templates/plan-tests-template.md`).

Chaque fichier contient :
- Une section *Usage rapide* expliquant quand lancer le prompt.
- Le prompt à copier/coller dans Codex (ajoutez vos informations avant d'envoyer).
- Le modèle Markdown à coller et faire remplir automatiquement.

## Routine proposée
- Créer le dossier `docs/taches/{{TASK_ID}}/`.
- Générer successivement chacun des documents ci-dessus en suivant les instructions fournies dans les fichiers templates.
- Conserver tous les livrables au même endroit (`brief.md`, `{{TASK_ID}}-analyse.md`, `{{TASK_ID}}-implementation.md`, `{{TASK_ID}}-plan-tests.md`).

## Bonnes pratiques
- Remplacer tous les placeholders `{{...}}` avant de considérer un document comme final.
- Tenir le journal d'implémentation à jour en append-only : ajouter des entrées horodatées à la suite sans retirer l'historique.
- Lier les scénarios de test aux anomalies ou tickets correspondants.
- Archiver les décisions clés directement dans les sections dédiées pour faciliter la revue.
