# Prompt – Plan de test

## Usage rapide
- Déclencher ce prompt dès que l'implémentation est stabilisée et prête à être vérifiée.
- Coller le prompt puis le modèle Markdown (bloc suivant) dans la même demande.
- (Optionnel) Ajoute en fin de prompt des notes complémentaires si tu veux préciser un focus QA. Supprime la section optionnelle si tu n'as rien à ajouter.

## Prompt (à copier-coller avant le modèle)
```text
test_plan {{TASK_ID}}

Tu es QA lead. En t'appuyant sur le brief `docs/taches/{{TASK_ID}}/brief.md`, l'analyse `docs/taches/{{TASK_ID}}/{{TASK_ID}}-analyse.md` et le journal `docs/taches/{{TASK_ID}}/{{TASK_ID}}-implementation.md`, bâtis un plan de test exhaustif en utilisant le modèle fourni.

Consignes :
1. Si le dossier `docs/taches/{{TASK_ID}}/` n'existe pas, crée-le.
2. Crée ou remplace le fichier `docs/taches/{{TASK_ID}}/{{TASK_ID}}-plan-tests.md` avec le modèle rempli.
3. Utiliser le modèle Markdown donné juste après ce bloc.
4. Détailler les scénarios avec préparation, étapes et résultats attendus.
5. Mentionner les commandes automatisées existantes ou à lancer.
6. Identifier clairement anomalies, décisions et actions restantes.

Cahier des charges additionnel (optionnel) :
{{NotesComplementaires}}

N'oublie pas de copier le modèle Markdown ci-dessous dans ta requête.
```

## Modèle Markdown à remplir
```markdown
# Plan de test {{TASK_ID}} – {{TASK_TITLE}}

- **Date**: {{DATE}}
- **Auteur**: {{AUTHOR}}
- **Version**: {{VERSION}}
- **Environnements**: {{ENVIRONNEMENTS}}
- **Pré-requis**: {{PrerequisGeneraux}}

## Objectif du plan
{{ObjectifPlan}}

## Préparation
- **Jeux de données**:
  - {{Dataset1}}
  - {{Dataset2}}
- **Accès / comptes**:
  - {{Compte1}}
  - {{Compte2}}
- **Configuration / scripts**:
  - `{{CommandePreparation1}}` — {{NotePreparation1}}
  - `{{CommandePreparation2}}` — {{NotePreparation2}}

## Stratégie de test
- **Périmètre couvert**:
  - {{Perimetre1}}
  - {{Perimetre2}}
- **Types de tests**:
  - {{TypeTest1}}
  - {{TypeTest2}}
- **Hors périmètre**:
  - {{HorsPerimetre1}}

## Scénarios détaillés
| ID | Description | Préparation | Étapes | Résultat attendu | Statut | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| {{ScenarioID1}} | {{ScenarioDesc1}} | {{ScenarioPrep1}} | {{ScenarioEtapes1}} | {{ScenarioResultat1}} | {{ScenarioStatut1}} | {{ScenarioNotes1}} |
| {{ScenarioID2}} | {{ScenarioDesc2}} | {{ScenarioPrep2}} | {{ScenarioEtapes2}} | {{ScenarioResultat2}} | {{ScenarioStatut2}} | {{ScenarioNotes2}} |

## Tests automatisés
- Commandes: `{{CommandesAutomatisation}}`
- Résultats attendus: {{ResultatsAttendus}}
- Couverture / limitations: {{Couverture}}

## Suivi des anomalies
- {{Anomalie1}} — Statut {{StatutAnomalie1}} — Lien {{LienAnomalie1}}
- {{Anomalie2}} — Statut {{StatutAnomalie2}} — Lien {{LienAnomalie2}}

## Résumé et décisions
- **Statut global**: {{StatutGlobal}}
- **Décisions prises**:
  - {{Decision1}}
  - {{Decision2}}
- **Actions restantes**:
  - {{ActionRestante1}}
  - {{ActionRestante2}}
```
