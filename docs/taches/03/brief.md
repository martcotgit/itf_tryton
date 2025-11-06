# Brief 02 – Portail client (navigation & authentification)

## 1. Contexte et objectif métier
- Ajouter une entrée « Client » sur le portail public afin de diriger les clients vers une zone sécurisée.
- Priorité de ce sprint : mettre en place le flux « Se connecter » (formulaire + authentification) et exposer l’ossature de la section Client.
- Préparer l’expérience « S’inscrire » via un bouton dédié qui renverra vers la future tâche d’inscription.

## 2. Périmètre fonctionnel de la tâche 02
- Mettre à jour la navigation (header) du site pour exposer le lien `Client`.
- Créer la page d’atterrissage « Espace client » contenant :
  - un formulaire de connexion (« Se connecter »),
  - un appel à l’action « S’inscrire » (redirection temporaire ou page en construction).
- Après authentification, rediriger vers une page tableau de bord minimale (« Client ») listant les sections à implémenter ultérieurement : Factures, Devis, Commandes, Profil.
- Garantir la possibilité de revenir au site public (lien « Retour au site »).
- Hors scope : création de compte, récupération de mot de passe, intégration Tryton des données, design détaillé des sous-sections.

## 3. Architecture & composants impactés
- **Front / Templates** :
  - `portal/templates/base.html` ou `portal/templates/core/home.html` pour l’ajout du lien dans l’en-tête.
  - Nouveau template `portal/templates/accounts/login.html` (hérite de `base.html`) et `portal/templates/accounts/dashboard.html`.
- **Django** :
  - Créer une app `accounts` dans `portal/apps/accounts/` (views, urls, forms).
  - Utiliser l’authentification Django native (`django.contrib.auth`) : `LoginView`, `AuthenticationForm`, session middleware existant.
  - Définir les URLs dans `portal/apps/accounts/urls.py` + inclusion dans `portal/apps/core/urls.py`.
  - Ajouter un décorateur `login_required`/CBV `LoginRequiredMixin` pour protéger le tableau de bord.
- **Statique** : prévoir classes CSS réutilisables depuis `portal/static/css/style.css`; si besoin, ajouter styles ciblés.
- **Configuration** : vérifier que `AUTHENTICATION_BACKENDS`, `TEMPLATES`, `LOGIN_URL`, `LOGIN_REDIRECT_URL` sont alignés dans `portal/itf_portal/settings/base.py`.

## 4. Parcours utilisateur cible
1. Depuis la page d’accueil, clic sur le lien `Client`.
2. Atterrissage sur `GET /client/` :
   - formulaire de login avec champs Email / Mot de passe + bouton « Se connecter »,
   - bloc informatif avec bouton « S’inscrire » (lien placeholder).
3. Soumission valide → authentification via Django ; redirection vers `/client/tableau-de-bord/`.
4. Tableau de bord affiche un message de bienvenue, les liens vers sections à venir, et un bouton de déconnexion (`POST /logout/`).
5. En cas d’échec (credentials invalides), rester sur la page login avec messages d’erreur.

## 5. Livrables attendus
- App Django `accounts` structurée (`__init__.py`, `urls.py`, `views.py`, `forms.py`, `templates/accounts/`).
- Vue de connexion personnalisée (héritée ou wrapper de `LoginView`) avec contenu marketing conforme à la charte.
- Page tableau de bord protégée (`ClientDashboardView`).
- Tests Django pour :
  - affichage du formulaire,
  - login réussi/échoué,
  - protection de la route `/client/tableau-de-bord/`.
- Documentation courte (README/app docstring) expliquant comment étendre la zone client.

## 6. Considérations UX, sécurité et dette
- Afficher des messages d’erreur conviviaux, sans indiquer si l’email existe.
- Prévoir la gestion du paramètre `next` pour conserver le flux en cas d’accès direct à une page protégée.
- Préparer des identifiants de test (fixture ou commande `createsuperuser`) pour la démo.
- Limiter les tentatives de login successives (middleware ou intégration ultérieure) – noter dans dettes.
- Veiller à ce que le bouton « S’inscrire » mène vers une URL distincte (`/client/inscription/`) afin de faciliter la future tâche.
