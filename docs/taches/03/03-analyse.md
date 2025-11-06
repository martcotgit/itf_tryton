# Analyse 03 – Portail client (navigation & authentification)

- **Fiche mission**: `docs/taches/03/brief.md`
- **Date**: 2025-11-06
- **Auteur**: Martin

## Contexte et objectifs
- Le portail public doit exposer une entrée « Client » menant vers un espace sécurisé pour les clients existants.
- Livrer le flux de connexion complet (formulaire, authentification, redirection, CTA « S’inscrire ») et un tableau de bord minimal annonçant les sections futures.

## État actuel / inventaire
- **Commandes à lancer**: `docker compose run --rm portal python manage.py test apps.accounts`
- **Fichiers / dossiers clefs**:
  - `portal/apps/core/urls.py` — Point d’entrée actuel du portail, doit inclure les routes de l’app `accounts`.
  - `portal/templates/base.html` — Template principal à enrichir avec la navigation et les liens Client / Retour site public.
- **Dépendances critiques**:
  - Django — version actuelle 4.2.11 / cible 4.2.11
  - psycopg[binary] — version actuelle 3.1.18 / cible 3.1.18

## Risques et compatibilités
- Oublier de protéger le tableau de bord avec l’authentification exposerait des données clientes par inadvertance.
- La page d’accueil n’hérite pas encore de `base.html`; une navigation incohérente peut émerger si la refactorisation n’est pas alignée.
- Une mauvaise gestion du paramètre `next` casserait les redirections lorsqu’un utilisateur tente d’accéder directement à une page sécurisée.

## Plan d'implémentation
1. Initialiser l’app `accounts` (config, URLs, templates), l’enregistrer côté settings et intégrer le lien « Client » dans la navigation.
2. Étendre `LoginView` pour personnaliser le formulaire, brancher les templates `accounts/login.html`, bouton « S’inscrire » et messages.
3. Créer le tableau de bord protégé + vue logout, sécuriser les redirections (`LOGIN_REDIRECT_URL`, `next`) et couvrir le flux par des tests Django.

## Questions ouvertes / décisions
- Confirmer si le brief (entête « Tâche 02 ») correspond bien à la tâche 03 ou si un ajustement fonctionnel est attendu.
- Décision: S’appuyer sur `django.contrib.auth.views.LoginView` et `LoginRequiredMixin` pour limiter le code d’authentification sur-mesure.

## Journal (à compléter pendant l'exécution)
- **Commandes lancées**:
  - `docker compose run --rm portal python manage.py test apps.accounts` — à planifier
- **Tests exécutés**:
  - `python -m unittest apps.accounts` — non exécuté
- **Notes libres**: À compléter lors du développement.
