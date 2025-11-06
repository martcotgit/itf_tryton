# Plan de documentation pour tryton-itf

Ce document de reference sert de boussole pour structurer et maintenir la documentation du projet, cote code comme cote produit. Il complete les consignes operationnelles d'`AGENTS.md` et s'appuie sur les gabarits disponibles dans `docs/templates/`.

## Objectifs et principes
- Rendre chaque role autonome (developpeur, administrateur, utilisateur final) avec une documentation ciblee et maintenable.
- Garantir que toute evolution fonctionnelle s'accompagne d'une mise a jour de la doc correspondante.
- Capitaliser sur les journaux de taches pour nourrir guides, FAQ et runbooks.
- Favoriser une documentation vivante : reviser regulierement, tracer les changements, supprimer le contenu obsolete.

## Personae et besoins documentaires
- **Developpeurs** : setup local, architecture, conventions de code, journaux de decisions, procedures de test et de release.
- **Administrateurs / Ops** : runbooks de supervision, recettes de maintenance, gestion des secrets et de la configuration.
- **Utilisateurs finaux** : guides pas-a-pas, tutoriels orientes metier, references des cas d'usage.
- **Support / QA** : plans de tests regressifs, checklists d'acceptation, historique des incidents.

## Structure cible du dossier `docs/`
L'arborescence suivante sert de cadre. Les elements deja existants (taches, templates) sont conserves.

```text
docs/
  README.md                # Page d'accueil avec cartes mentales et liens croises
  documentation-plan.md    # Ce document (roadmap)
  development/
    setup.md               # Ancien `development-setup.md`
    workflow.md            # Workflow Git, routine Codex, politique de branches
    architecture/
      overview.md          # Vue d'ensemble (modules Tryton, portal Django, integrations)
      data-model.md        # Diagrammes de modeles, contraintes
      api.md               # Points d'entree (RPC, scripts d'import/export)
  guides/
    utilisateurs/
      index.md             # Scenarios fonctionnels, tutoriels
      faq.md
    administrateurs/
      runbooks.md          # Procedures quotidiennes et interventions d'urgence
      configuration.md     # Parametrage, secrets, sauvegardes
  reference/
    modules/
      tryton-module-name.md
      portal-module-name.md
  qualite/
    tests.md               # Strategie de tests, commandes, donnees d'essai
    checklists.md          # Recettes pre-release, smoke-tests
  taches/                  # Livrables generes par le workflow existant
  templates/               # Prompts et gabarits
```

> Astuce : introduire progressivement les fichiers manquants en priorisant ce qui debloque le plus d'utilisateurs (par exemple `development/workflow.md` puis `guides/utilisateurs/index.md`).

## Routine de contribution a la documentation
### Pour toute evolution de code
1. **Analyser** l'effet de la tache sur les publics cibles.
2. **Mettre a jour** la section appropriee (ex. `development/architecture/overview.md` pour un nouveau module).
3. **Etoffer** le plan de test dans `docs/taches/<ID>/*plan-tests*.md` et reporter les scenarios pertinents dans `qualite/tests.md`.
4. **Valider** la lisibilite (liens, captures le cas echeant) avant la revue de code.

### Routine specifique pour l'agent Codex
1. Lire ou rappeler les consignes d'`AGENTS.md` et du dossier `docs/development/`.
2. Verifier l'existence d'un dossier de tache dans `docs/taches/` ; si absent, en creer un via les templates.
3. Elaborer un plan de travail (outil `update_plan`) et documenter les hypotheses dans l'analyse d'implementation.
4. Tenir a jour le journal d'implementation et pointer explicitement les ajustements de documentation.
5. Faire tourner les tests prevus ou ajouter un plan de verification si les tests ne peuvent pas etre executes.
6. Conclure la tache en listant les fichiers modifies, les tests realises et les mises a jour de doc effectuees.

### Revue et maintenance
- **Gardiennage trimestriel** : faire relire chaque sous-dossier par un referent different pour assurer fraicheur et completude.
- **Tableau de bord** : tenir une checklist "doc a jour ?" dans la description des PR.
- **Archives** : deplacer les contenus obsoletes dans `docs/archive/` (compression semestrielle) quand ils ne servent plus mais doivent rester consultables.

## Standards editoriaux
- Format Markdown, titres en anglais quand l'interface l'est, sinon conserver la langue du public cible.
- Prefere les captures d'ecran annotees pour les guides utilisateurs ; conserver les fichiers sources dans `docs/assets/`.
- Ajouter un bloc "Derniere verification" en bas des runbooks critiques avec date + auteur.
- Lorsqu'une decision technique majeure est enteree, creer une fiche courte dans `development/architecture/decisions/adr-YYYYNN.md`.

## Backlog prioritaire pour lancer l'effort
- Migrer `docs/development-setup.md` vers `docs/development/setup.md` et ajouter `docs/README.md`.
- Rediger `development/workflow.md` (branches, rebase, commandes Makefile, obligations de tests).
- Produire un premier `guides/utilisateurs/index.md` couvrant les cas d'usage du portail client.
- Documenter au moins un runbook critique dans `guides/administrateurs/runbooks.md` (ex. rotation des mots de passe Tryton).
- Initialiser `qualite/tests.md` avec la commande de discover et les attentes minimales (unitaires, integration).

La priorisation peut etre geree comme une Epic detaillant ces cinq livrables dans le backlog.

## Suivi
- Integrer une verification "Docs a jour ?" dans le gabarit de PR.
- Ajouter un rappel hebdomadaire Slack / email pour les responsables de modules afin de relire leurs sections.
- Mesurer l'adoption en consultant les journaux Git et en sondant les utilisateurs internes (support, ops) sur les guides fournis.
