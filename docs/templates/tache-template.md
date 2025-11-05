# Prompt – Dossier de tâche

## Usage rapide
- Utiliser ce prompt dès qu'une nouvelle tâche est définie ou qu'un brief doit être structuré.
- Coller le prompt ci-dessous dans Codex, y ajouter la description brute et les contraintes disponibles.
- Copier ensuite le modèle Markdown et le coller dans la même demande pour que Codex le remplisse.

## Prompt (à copier-coller avant le modèle)
```text
brief {{TASK_ID}}

Tu es chef de projet technique. À partir des informations suivantes, produis un dossier de tâche complet en Markdown.

Description brute :
{{DescriptionBrute}}

Contraintes ou notes complémentaires :
{{ContraintesConnues}}

Consignes :
1. Si le dossier `docs/taches/{{TASK_ID}}/` n'existe pas, crée-le.
2. Génère le fichier `docs/taches/{{TASK_ID}}/brief.md` avec le contenu du modèle rempli.
3. Suivre strictement le modèle Markdown fourni après ce bloc.
4. Remplacer tous les {{...}} par du contenu actionnable et concret.
5. Proposer au moins 3 objectifs et 3 actions.
6. Adapter le ton à un brief interne (clair, concis, orienté action).

Le modèle suit après ce bloc ; inclue-le dans ta réponse en le remplissant intégralement.
```

## Modèle Markdown à remplir
```markdown
# {{TASK_ID}} – {{TASK_TITLE}}

- **Date**: {{DATE}}
- **Auteur**: {{AUTHOR}}
- **Statut**: {{STATUS}}
- **Liens utiles**: {{LINKS}}

## Description succincte
{{DescriptionRapide}}

## Contexte
{{Contexte}}

## Objectifs / résultats attendus
- {{Objectif1}}
- {{Objectif2}}
- {{Objectif3}}

## Travail à réaliser
- [ ] {{Action1}}
- [ ] {{Action2}}
- [ ] {{Action3}}

## Périmètre
- **Inclus**:
  - {{Inclus1}}
  - {{Inclus2}}
- **Exclus**:
  - {{Exclus1}}
  - {{Exclus2}}

## Hypothèses et contraintes
- {{Hypothese1}}
- {{Hypothese2}}
- {{Contrainte1}}

## Dépendances et risques
- **Dépendances**:
  - {{Dependance1}}
  - {{Dependance2}}
- **Risques**:
  - {{Risque1}}
  - {{Risque2}}

## Références
- `{{ReferencePath1}}` — {{ReferenceNote1}}
- `{{ReferencePath2}}` — {{ReferenceNote2}}

## Critères d'acceptation
- {{Critere1}}
- {{Critere2}}
- {{Critere3}}

## Points de contact
- {{Role1}} — {{Personne1}}
- {{Role2}} — {{Personne2}}

## Questions ouvertes / suivi
- {{Question1}}
- {{ActionSuivi1}}
```
