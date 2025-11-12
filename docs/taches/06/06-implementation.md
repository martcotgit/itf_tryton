# Implémentation 06 – CI GitHub pour les tests portail

- **Analyse associée**: `docs/taches/06/06-analyse.md`
- **Date**: 2025-11-11
- **Auteur**: Codex

## Résumé des décisions
- Ajouter un workflow GitHub Actions unique (`tests.yml`) centré sur le portail pour commencer.
- Installer les dépendances via `pip install -r portal/requirements/dev.txt` plutôt qu’un build Docker complet pour réduire le temps d’exécution.

## Journal d'exécution
> Journal append-only : ajouter une ligne horodatée par action (`2025-11-11 10:15 | Action → Résultat`) en conservant les entrées existantes.
- 2025-11-11 10:20 | Initialisation du dossier `docs/taches/06` et des gabarits (brief, analyse, implémentation) → Succès
- 2025-11-11 10:38 | Ajout du workflow GitHub Actions `tests.yml` basé sur `docker compose run` → Succès
- 2025-11-11 10:44 | Mise à jour d'`AGENTS.md` et de `docs/deployment-checklist.md` pour refléter l'usage systématique de docker compose → Succès
- 2025-11-11 10:48 | Exécution de `docker compose run --rm portal pytest --maxfail=1 --disable-warnings -q` → Succès

## Modifications par fichier
| Fichier | Description succincte | Suivi PR / commit |
| --- | --- | --- |
| `docs/taches/06/brief.md` | Création du brief décrivant les objectifs CI | À lier |
| `docs/taches/06/06-analyse.md` | Analyse technique et plan d’implantation | À lier |
| `docs/taches/06/06-implementation.md` | Journal amorcé avec les décisions initiales | À lier |
| `.github/workflows/tests.yml` | Workflow GitHub Actions qui build l'image portail et lance `pytest` via docker compose | À lier |
| `AGENTS.md` | Nouvelle consigne imposant l’usage de `docker compose` pour toutes les commandes | À lier |
| `docs/deployment-checklist.md` | Préparation mise à jour (commande Pytest + vérification du workflow CI) | À lier |

## Tests manuels
- [x] Vérifier l’exécution locale de `pytest` dans `portal/`
- [x] S’assurer que la documentation mentionne la CI avant clôture
- Notes: Tests effectués via `docker compose run --rm portal pytest --maxfail=1 --disable-warnings -q`.

## Tests automatisés
- Commandes: `docker compose run --rm -e DJANGO_SETTINGS_MODULE=itf_portal.settings.base -e DATABASE_URL=sqlite:////tmp/test-db.sqlite3 portal pytest --maxfail=1 --disable-warnings -q`
- Résultats: 38 tests passés, 0 échec, 1 avertissement (attendu Pytest).

## Audits sécurité / qualité
- `npm audit`: Non applicable à cette tâche.
- `composer audit`: Non applicable à cette tâche.

## Points de suivi post-déploiement
- Ajouter, au besoin, un badge de statut CI dans la documentation.
- Étendre le workflow aux modules Tryton lorsqu’ils disposeront de tests automatisés.
