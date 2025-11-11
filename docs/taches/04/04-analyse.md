# Analyse 04 – Gestion du profil client du portail

- **Fiche mission**: `docs/taches/04/brief.md`
- **Date**: 2025-11-10
- **Auteur**: Codex

## Contexte et objectifs
- Le portail client dispose maintenant d’un flux d’authentification et d’inscription, mais aucune page ne permet au client de maintenir ses informations; les équipes de support doivent encore passer par Tryton manuellement.
- L’objectif est de fournir une page « Profil » complète (identité + coordonnées + mot de passe) avec synchronisation bidirectionnelle fiable vers Tryton et une expérience utilisateur claire.

## État actuel / inventaire
- **Commandes à lancer**: `docker compose run --rm portal python manage.py test apps.accounts`
- **Fichiers / dossiers clefs**:
  - `portal/apps/accounts/views.py` — Contient les vues `ClientDashboardView`, `ClientSignupView` et constitue le point d’entrée pour une future `ProfileView`.
  - `portal/apps/accounts/services.py` — Encapsule les appels RPC Tryton; devra être enrichi pour lire/mettre à jour les fiches parties et les mots de passe.
- **Dépendances critiques**:
  - Django — version actuelle 4.2.11 / cible 4.2.11 (stable LTS utilisée par le portail).
  - Tryton (serveur via `tryton/tryton:7.6`) — version actuelle 7.6 / cible 7.6 (alignée sur l’image Docker).

## Risques et compatibilités
- Une erreur RPC Tryton silencieuse pourrait laisser croire au client que ses données sont sauvegardées alors qu’elles ont été rejetées (perte de confiance).
- Le changement de mot de passe doit respecter les validateurs locaux et les règles Tryton; une désynchronisation pourrait bloquer la connexion via le portail.
- Ajout de champs supplémentaires dans le profil peut introduire des divergences avec les structures Tryton (addresses, contact mechanisms) si les mappings ne sont pas verrouillés.

## Plan d'implémentation
1. Étendre `PortalAccountService` pour récupérer les données du `party` lié à l’utilisateur, exposer une méthode de mise à jour (coordonnées + mécanismes de contact) et une méthode dédiée au changement de mot de passe (avec gestion précise des erreurs RPC).
2. Créer les formulaires Django (`ClientProfileForm`, `ClientPasswordForm`) et la vue `ProfileView` protégée (`LoginRequiredMixin`) qui pré-remplit les champs, applique les validateurs existants et orchestre les appels de service; ajouter le template `accounts/profile.html` et la navigation depuis le tableau de bord.
3. Couvrir l’ensemble avec des tests (`portal/apps/accounts/tests/test_profile.py`) simulant les appels Tryton, documenter les commandes dans `docs/taches/04/04-implementation.md` et mettre à jour les messages utilisateur/localisation.

## Questions ouvertes / décisions
- Confirmation requise sur la profondeur d’édition pour l’adresse postale (simple adresse unique ou gestion multi-adresses Tryton?). Réponse: Multi adresse
- Décision à consigner : conservation du mot de passe côté Tryton uniquement (le portail n’enregistre qu’un hash local via Django) ou alignement strict sur Tryton comme source de vérité. Oui le mot de passe se gère dans Tryton

## Journal (à compléter pendant l'exécution)
- **Commandes lancées**:
  - `N/A` — À compléter durant l’implémentation.
- **Tests exécutés**:
  - `N/A` — À compléter durant l’implémentation.
- **Notes libres**: À remplir au fil de la réalisation (observations, anomalies, suivis).
