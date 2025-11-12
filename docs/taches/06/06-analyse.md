# Analyse 06 – CI GitHub pour les tests portail

- **Fiche mission**: `docs/taches/06/brief.md`
- **Date**: 2025-11-11
- **Auteur**: Codex

## Contexte et objectifs
- Les tests Django/pytest ne s’exécutent qu’en local via `docker compose`, ce qui laisse passer des régressions lors des PR.
- Objectif principal : automatiser `pytest` dans GitHub Actions, partager les résultats dans l’onglet Actions et fiabiliser la checklist de déploiement.

## État actuel / inventaire
- **Commandes à lancer**: `cd portal && pip install -r requirements/dev.txt && pytest`
- **Fichiers / dossiers clefs**:
  - `portal/requirements/dev.txt` — énumère les dépendances nécessaires aux tests (pytest, pytest-django, ruff).
  - `docs/deployment-checklist.md` — documentation actuelle décrivant les tests manuels à lancer avant un déploiement.
- **Dépendances critiques**:
  - `pytest` — version actuelle 8.2.1 / cible 8.2.1 (conserver la version pinée).
  - `pytest-django` — version actuelle 4.8.0 / cible 4.8.0 (respecter la compatibilité Django 4.2).

## Risques et compatibilités
- Variables d’environnement Tryton manquantes pouvant faire échouer `TrytonClient()` pendant l’import des modules.
- Temps d’exécution allongé sans cache pip ou sans parallélisation.
- Nécessité d’un SQLite fonctionnel : GitHub Actions doit inclure `python -m pip install --upgrade pip` avant les installs.

## Plan d'implémentation
1. Créer la structure `.github/workflows/` si elle n’existe pas et ajouter `tests.yml` avec les déclencheurs `push` + `pull_request`.
2. Configurer le job pour utiliser `actions/setup-python@v5`, restaurer le cache pip et installer `portal/requirements/dev.txt`.
3. Exécuter `pytest` depuis `portal/` avec `DJANGO_SETTINGS_MODULE=itf_portal.settings.base`, puis exporter les résultats dans la CI (log + statut).

## Questions ouvertes / décisions
- La suite doit-elle aussi couvrir `siteweb-itf` ou uniquement le portail? (à clarifier avec le PO).
- Décision : privilégier `pytest` (et non `manage.py test`) afin de respecter les fixtures Pytest existantes.

## Journal (à compléter pendant l'exécution)
- **Commandes lancées**:
  - `À documenter` — En attente
- **Tests exécutés**:
  - `pytest` — À planifier dans la CI
- **Notes libres**: Ce journal sera complété au fur et à mesure des commits CI.
