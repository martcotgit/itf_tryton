# 06 – CI GitHub pour les tests portail

- **Date**: 2025-11-11
- **Auteur**: Codex
- **Statut**: En préparation
- **Liens utiles**: docs/deployment-checklist.md, portal/apps/core/tests/test_tryton_client.py, portal/apps/accounts/tests/, docker-compose.yml

## Description succincte
Mettre en place une exécution automatique des tests du portail client via GitHub Actions afin de bloquer rapidement les régressions et donner de la visibilité aux revues de code.

## Contexte
Les tests sont lancés manuellement via `docker compose run --rm portal python manage.py test` et ne s’exécutent pas lors des Pull Requests. Sans CI, les régressions liées aux validations Tryton simulées et aux formulaires Django ne sont détectées qu’en fin de cycle, ce qui ralentit les correctifs et augmente le risque de déployer du code instable.

## Objectifs / résultats attendus
- Disposer d’un workflow GitHub Actions déclenché sur `push` et `pull_request` pour les branches principales.
- Installer les dépendances Python du portail et exécuter `pytest` avec le module Django configuré.
- Publier un résumé des tests (statut, durée) directement dans l’onglet Actions des PR.

## Travail à réaliser
- [ ] Créer le fichier `.github/workflows/tests.yml` avec le déclencheur standard `push` + `pull_request`.
- [ ] Configurer le job pour installer Python 3.12, mettre en cache le dossier pip et lancer `pip install -r portal/requirements/dev.txt`.
- [ ] Exécuter `pytest` depuis `portal/` avec `DJANGO_SETTINGS_MODULE=itf_portal.settings.base` et documenter la procédure dans `docs/deployment-checklist.md`.

## Périmètre
- **Inclus**:
  - Couverture des tests Django/Pytest du portail (`portal/apps/**/tests`).
  - Documentation des commandes CI dans les guides internes existants.
- **Exclus**:
  - Pipeline Docker complet (build d’images, push registry).
  - Tests Tryton exécutés via `trytond-admin`.

## Hypothèses et contraintes
- L’environnement GitHub Actions doit rester sans secret sensible; utilisation d’identifiants factices pour `TRYTON_USER/TRYTON_PASSWORD`.
- Les tests ne nécessitent pas de base Postgres; SQLite suffit pour la suite Django actuelle.
- Les workflows doivent rester compatibles avec `ubuntu-latest`.

## Dépendances et risques
- **Dépendances**:
  - `portal/requirements/dev.txt` — dépendances de tests.
  - `docs/deployment-checklist.md` — commandes officielles à aligner.
- **Risques**:
  - Temps d’exécution trop long si le cache pip est absent ou mal configuré.
  - Rupture future si d’autres modules (portal/siteweb) nécessitent des services additionnels non couverts par ce workflow.

## Références
- `docs/deployment-checklist.md` — Actuellement la seule mention explicite des tests.
- `portal/apps/core/tests/test_tryton_client.py` — Cas les plus coûteux à maintenir, utiles pour définir la commande Pytest.

## Critères d'acceptation
- Un workflow visible dans GitHub Actions se déclenche automatiquement sur chaque PR et montre le statut des tests.
- Le job échoue si `pytest` retourne un code non nul.
- La procédure de déploiement documente que les tests CI doivent être verts avant livraison.

## Points de contact
- PO technique portail — Martin G.
- DevOps / automatisation — Codex

## Questions ouvertes / suivi
- Faut-il ajouter un badge de statut CI dans `README` ou la doc d’onboarding?
- Prévoir une extension future pour lancer les tests Tryton?*** End Patch
