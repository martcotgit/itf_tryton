# Analyse 01 – Plan d'intégration du portail client

- **Fiche mission**: `docs/taches/01/brief.md`
- **Date**: 2025-11-05
- **Auteur**: Assistant (lead dev)

## Contexte et objectifs
- Mettre à disposition un portail client sécurisé réutilisant le site vitrine existant tout en l'industrialissant sous Django.
- Offrir l'accès unifié aux commandes, factures, documents et futures fonctions de self-service en s'appuyant sur Tryton comme source de vérité.

## État actuel / inventaire
- **Commandes à lancer**: `docker compose up --build portal traefik && docker compose exec portal python manage.py check`
- **Fichiers / dossiers clefs**:
  - `docs/taches/01/brief.md` — cahier des charges détaillé et décisions existantes.
  - `docker-compose.yml` — doit accueillir les services `portal`, `traefik` et les réseaux associés.
  - `siteweb-itf/src` — base front-end à migrer vers Django (`static/` + `templates/`).
  - `tryton/` — modules existants à étendre (exposition API dédiée si nécessaire).
- **Dépendances critiques**:
  - Django — version actuelle N/A / cible 4.2 LTS (ou 5.x si validation de compatibilité).
  - Tryton — version actuelle 7.6 (image `tryton/tryton:7.6`) / cible 7.6 (alignement avec envs).
  - Python (service portal) — version actuelle N/A / cible 3.12 (image de base Docker).

## Risques et compatibilités
- Latence et timeouts JSON-RPC entre Django et Tryton pouvant dégrader l'expérience client ; mitigation via cache/optimisation.
- Alignement authentification (comptes Tryton directs) exige une gestion stricte des droits et des flux de réinitialisation.
- Charge supplémentaire sur Tryton lors de la migration du front (liste factures/commandes) sans stratégie de pagination ni quotas.

## Plan d'implémentation
1. Valider le périmètre MVP, fixer les choix techniques (versions Django/Python, authentification directe, besoin Redis) et préparer la documentation d'installation.
2. Initialiser le projet `portal/` (structure Django, Dockerfile, service Compose, outils qualité) et intégrer les assets du site vitrine.
3. Développer la couche d'accès Tryton (client JSON-RPC, services métiers) puis livrer les premières vues authentifiées (commandes, factures) avec jeux de tests et scripts d'exploitation.

## Questions ouvertes / décisions
- Confirmer les modalités d'authentification client (tryton-only vs double base) et les exigences d'emailing transactionnel (outil, délivrabilité).
- Décision à documenter : adoption d'un cache (Redis local/partagé) pour soulager Tryton et choix du provider de paiement à intégrer dans le MVP.

## Journal (à compléter pendant l'exécution)
- **Commandes lancées**:
  - `À renseigner` — à compléter lors du développement.
- **Tests exécutés**:
  - `À définir` — en attente.
- **Notes libres**: À compléter.
