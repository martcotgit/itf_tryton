# Prompt – Journal d'implémentation

## Usage rapide
- Lancer ce prompt après validation de l'analyse et au début du développement.
- Coller le prompt puis le modèle Markdown (bloc suivant) dans la même demande.
- (Optionnel) Ajoute en fin de prompt des notes complémentaires si tu veux préciser des décisions ou contraintes. Supprime la section optionnelle si tu n'as rien à ajouter.

## Prompt (à copier-coller avant le modèle)
```text
implementation {{TASK_ID}}

Tu es lead dev chargé de journaliser l'implémentation. En t'appuyant sur le brief `docs/taches/{{TASK_ID}}/brief.md` et l'analyse `docs/taches/{{TASK_ID}}/{{TASK_ID}}-analyse.md`, remplis le modèle fourni.

Consignes :
1. Si le dossier `docs/taches/{{TASK_ID}}/` n'existe pas, crée-le.
2. Si le fichier `docs/taches/{{TASK_ID}}/{{TASK_ID}}-implementation.md` n'existe pas, crée-le avec le modèle rempli; sinon, ajoute la nouvelle entrée à la suite du journal sans supprimer l'historique.
3. Utiliser le modèle Markdown fourni après ce bloc.
4. Décrire chaque action avec le résultat observé (succès, échec, suivi).
5. Lister les commandes exécutées, tests et audits avec leurs statuts.
6. Mentionner les points de suivi post-déploiement lorsque identifiés.

Cahier des charges additionnel (optionnel) :
{{NotesComplementaires}}

Copie ensuite le modèle Markdown situé après ce bloc dans la même requête.
```

## Modèle Markdown à remplir
```markdown
# Implémentation {{TASK_ID}} – {{TASK_TITLE}}

- **Analyse associée**: `docs/taches/{{TASK_ID}}/{{TASK_ID}}-analyse.md`
- **Date**: {{DATE}}
- **Auteur**: {{AUTHOR}}

## Résumé des décisions
- {{Decision1}}
- {{Decision2}}

## Journal d'exécution
> Journal append-only : ajouter une ligne horodatée par action (`2024-05-16 14:02 | Action → Résultat`) en conservant les entrées existantes.
- {{Action1}} → {{Resultat1}}
- {{Action2}} → {{Resultat2}}

## Modifications par fichier
| Fichier | Description succincte | Suivi PR / commit |
| --- | --- | --- |
| `{{Chemin}}` | {{Description}} | {{Lien}} |

## Tests manuels
- [ ] {{Test1}}
- [ ] {{Test2}}
- Notes: {{NotesTests}}

## Tests automatisés
- Commandes: `{{CommandesTests}}`
- Résultats: {{ResultatsTests}}

## Audits sécurité / qualité
- `npm audit`: {{ResumeAuditNpm}}
- `composer audit`: {{ResumeAuditComposer}}

## Points de suivi post-déploiement
- {{PointSuivi1}}
- {{PointSuivi2}}
```
