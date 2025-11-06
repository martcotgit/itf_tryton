# Analyse 02 – Tryton Client Service

- **Fiche mission**: `docs/taches/02/brief.md`
- **Date**: 2025-11-05
- **Auteur**: Assistant (lead dev)

## Contexte et objectifs
- Centraliser un client JSON-RPC Tryton mutualisé dans l'application Django `portal` pour les besoins auth, commandes et facturation.
- Garantir une API fiable avec authentification gérée, cache Redis et journalisation pour toutes les interactions Tryton.

## État actuel / inventaire
- **Commandes à lancer**: `docker compose up --build portal tryton redis`
- **Fichiers / dossiers clefs**:
  - `portal/apps/core/services/tryton_client.py` — fichier à créer pour encapsuler l'API Tryton et la logique de session.
  - `portal/itf_portal/settings/base.py` — configuration Django où ajouter les variables TRYTON_* et les paramètres de cache.
- **Dépendances critiques**:
  - httpx — version actuelle non installée / cible >=0.27.0
  - django-redis — version actuelle 5.4.0 / cible 5.4.0 (OK)

## Risques et compatibilités
- Perte ou fuite du `session_id` si plusieurs processus partagent la même instance client sans isolation.
- Cache Redis incohérent (TTL mal réglés) pouvant exposer des données périmées aux utilisateurs.
- Credentials Tryton exposés dans les logs ou les exceptions si le masquage n'est pas systématique.

## Plan d'implémentation
1. Ajouter les paramètres d'environnement (TRYTON_RPC_URL, TRYTON_USER, TRYTON_PASSWORD, TRYTON_SESSION_TTL, TIMEOUT) et installer la dépendance HTTP choisie.
2. Créer `TrytonClient` avec gestion d'authentification, requêtes, retries, cache et exceptions dédiées.
3. Exposer l'instance/service via `apps.core` (singleton ou factory), écrire une documentation rapide et préparer les hooks de tests.

## Questions ouvertes / décisions
- Quelle librairie HTTP retenir (requests vs httpx) selon nos standards et contraintes async/retry ?
- Décider si le client doit être instancié à chaud via `AppConfig.ready()` ou fourni par une factory pour éviter les problèmes de thread-safety.

## Journal (à compléter pendant l'exécution)
- **Commandes lancées**:
  - `(à compléter)` — en attente d'implémentation
- **Tests exécutés**:
  - `(à compléter)` — non exécuté
- **Notes libres**: À compléter lors de l'implémentation
