# Plan d'intégration du portail client

## 1. Contexte et objectifs
- Fournir aux clients un portail sécurisé (authentification, gestion de compte) avec accès aux commandes, factures et documents liés.
- Réutiliser le site actuel (`siteweb-itf/src`) comme base visuelle et le transformer en projet Django exploitable.
- S'appuyer sur Tryton comme source de vérité pour les données commerciales via ses API (JSON-RPC / Proteus / modules maison).
- Garantir un environnement de développement reproductible via Docker Compose et documenter les flux de déploiement.

## 2. Architecture cible (haut niveau)
- **Dépôt** :
  - `docs/` : documentation (dont ce plan).
  - `portal/` : projet Django (code Python, templates, ressources front).
  - `siteweb-itf/` : conservé comme référence statique, migré en bloc dans `portal/` lors de l'initialisation Django.
  - `tryton/` : modules Tryton spécifiques (points d'extension éventuels pour l'API).
- **Services Docker Compose (local)** :
  - `db` (PostgreSQL existant).
  - `tryton` (service actuel).
  - `portal` (nouveau service Django, image basée sur Python 3.12, dépendances `pip`).
  - `traefik` (reverse proxy unique pour router vers Django/Tryton, gère TLS).
- **Flux réseau** :
  - Django ↔ Tryton via JSON-RPC (port 8000) ou via modules Python exécutés dans le même réseau Docker.
  - Clients ↔ Traefik ↔ Django (HTTPS via Traefik dans tous les environnements).
- **Gestion des configurations** :
  - Variables d'environnement pour les secrets (`DJANGO_SECRET_KEY`, `TRYTON_RPC_URL`, `TRYTON_USER`, `TRYTON_PASSWORD`, `PORTAL_DB_URL`, etc.).
  - Fichiers `.env` spécifiques à chaque environnement (local, staging, production) non versionnés.

## 3. Organisation du projet Django (`portal/`)
- **Structure suggérée** :
  ```
  portal/
    Dockerfile
    manage.py
    pyproject.toml / requirements/
    itf_portal/               # configuration Django
      __init__.py
      settings/
        __init__.py
        base.py
        local.py
        production.py
      urls.py
      wsgi.py / asgi.py
    apps/
      core/                   # utilitaires, layout, pages génériques
      accounts/               # gestion des comptes client, profils
      orders/                 # consultation & création de commandes
      billing/                # factures, paiements
      communications/         # notifications, emails, fichiers partagés
    templates/
    static/
    scripts/                  # commandes de gestion (ex: sync_tryton_data.py)
    tests/
      conftest.py
      factories/
  ```
- **Approche front-end** :
  - Migrer en une seule étape les assets (`css`, `js`, `img`) de `siteweb-itf/src` vers `portal/static/`.
  - Transformer `index.html` et toutes les pages existantes en templates Django (`templates/`) dès la phase initiale, en réutilisant les composants actuels.
- **Dépendances initiales** :
  - `Django 4.2 LTS` (ou 5.x si compatibilité validée).
  - `django-environ` ou équivalent pour la configuration.
  - `djangorestframework` (optionnel) pour exposer des APIs REST internes ou alimenter un front externe ultérieur.
  - `requests` ou `httpx` + client JSON-RPC (ex: `trytond.rpc` ou client maison).
  - `django-allauth` ou `django-rest-auth` pour les flux d'inscription/réinitialisation si l'on veut un module éprouvé.
  - Outils dev : `pytest`, `pytest-django`, `black`, `ruff`, `mypy` (optionnel).

## 4. Accès aux données Tryton
- **Options techniques** :
  - JSON-RPC natif de Tryton (exposition par le service `tryton` existant). Avantage : aucune extension requise côté Tryton.
  - Utilisation de `Proteus` (bibliothèque Tryton pour les scripts Python) si la logique doit rester côté serveur Django.
  - Création d'un module Tryton dédié (`tryton/modules/itf_portal_api`) pour simplifier l'exposition de données/logiciels métiers, si nécessaire.
- **Entités prioritaires** :
  - `party.party` (informations clients + contacts).
  - `sale.sale` (commandes), `sale.line`.
  - `account.invoice` / `account.move`.
  - `product.product` (catalogue pour prise de commande).
- **Stratégie de synchronisation** :
  - Favoriser l'accès à la demande (live) via API.
  - Mettre en cache certaines données peu volatiles (catalogue, listes de statuts) via Redis ou base locale si la latence Tryton devient un problème.
- **Sécurité & permissions** :
  - Créer/mapper des utilisateurs Tryton pour chaque client portail ou utiliser un compte de service avec filtres de domaine.
  - Implémenter une couche d'accès dans Django (`TrytonService` dans `portal/apps/core/services/tryton_client.py`) qui s'assure que les requêtes filtrent par `customer_id`.
  - Traiter les reconnections et renouvellements de session Tryton (gestion du cookie `session_id` si JSON-RPC).

## 5. Plan d'itérations (macro)
1. **Préparation**  
   - Valider les versions (Django, Python, Tryton).  
   - Définir la structure du dépôt (création de `portal/`, fichiers de config initiaux).  
   - Documenter la procédure d'installation locale (`docs/development-setup.md`).
2. **Bootstrap Django**  
   - Générer le projet `portal` avec settings modulaires.  
   - Ajouter Dockerfile + `docker-compose` (service `portal`).  
   - Intégrer linting/tests de base (CI local via `make` ou scripts).
3. **Migration du site vitrine**  
   - Importer l'ensemble des assets statiques existants en une seule migration initiale.  
   - Porter toutes les pages du site vitrine dans Django (views + templates) d'un seul bloc.  
   - Préparer un layout base (`base.html`) + navigation et vérifier la parité visuelle.
4. **Gestion des comptes clients**  
   - Choisir le modèle d'authentification (compte dédié ou SSO Tryton).  
   - Implémenter inscription/activation ou import depuis Tryton.  
   - Mettre en place profils, changement mot de passe, politiques de sécurité (2FA si requis).
5. **Consultation des commandes**  
   - Développer un service `TrytonSalesService`.  
   - Lister les commandes, détail, tracking du statut.  
   - Ajouter filtres, export CSV/PDF si besoin.
6. **Création de commandes (optionnel selon MVP)**  
   - UI pour panier, catalogue produit.  
   - Validation métier avec Tryton (disponibilité, tarifs, taxes).  
   - Gestion des erreurs et messages utilisateur.
7. **Factures & paiements**  
   - Afficher l'historique de factures avec lien de téléchargement (PDF).  
   - Intégrer un fournisseur de paiement si souhaité (Stripe, Moneris, etc.).  
   - Reconciler le statut paiement ↔ Tryton.
8. **Dashboards & notifications**  
   - Page d'accueil personnalisée (statut des commandes, documents récents).  
   - Notifications email / webhook lors de changement d'état important.
9. **Observabilité & déploiement**  
   - Logging structuré (Django + Tryton).  
   - Monitoring (health checks, Sentry ou équivalent).  
   - Pipeline CI/CD (tests, build image, déploiement staging/production).  
   - Documentation utilisateur & support.

## 6. Tâches opérationnelles complémentaires
- Écrire un guide `docs/tryton-api.md` listant les endpoints/objets utilisés, les filtres standard et les conventions d'erreur.
- Ajouter des scripts Makefile/`manage.py` :  
  - `make portal-up`, `make portal-test`, `make portal-lint`.  
  - Commande `sync_tryton_customer --dry-run` pour importer/mettre à jour les comptes clients dans Django.
- Mettre en place des fixtures de tests anonymisées pour reproduire un jeu de données Tryton minimal.
- Préparer un plan de migration si des comptes clients existent déjà (matching email ↔ party).
- Définir les rôles internes (administrateur, support, client) et les permissions associées dans Django (groupes).

## 7. Points de vigilance & décisions à prendre
- **Authentification** :  
  - Connexion directe aux comptes Tryton ou base utilisateur séparée synchronisée ?  Réponse: Direct
  - Gestion du reset mot de passe (email transactionnel, OTP, etc.). Réponse: Oui avec email transactionnel
- **Performances** :  
  - Latence JSON-RPC, nécessité d'un cache côté Django ou d'API spécifiques côté Tryton.: Réponse: Cache avec django
  - Volume des factures (stockage de PDF dans Tryton vs filestore Django). Réponse: Dans tryton
- **Sécurité** :  
  - HTTPS end-to-end, durcissement des en-têtes (CSP, HSTS).  
  - Journalisation des accès et traçabilité des actions sensibles (téléchargement facture, création commande).
- **Déploiement** :  
  - Choix de l'orchestrateur (Docker Compose prod, Kubernetes, autre).  Réponse: Docker Compose prod
  - Gestion des montées de version Tryton/Django synchronisées.

## 8. Livrables initiaux à produire
- `portal/` contenant un squelette Django + documentation d'installation.
- `docker-compose.yml` mis à jour avec le service `portal` (et éventuellement `redis` si cache). Documenter les ports et dépendances.
- `docs/development-setup.md` : comment lancer Tryton + Django en local, création des comptes test.
- `docs/architecture-portal.md` (ou enrichir ce plan) : diagrammes simples (UML/SVG) présentant les flux (client ↔ Django ↔ Tryton).
- Scripts d'intégration continue (GitHub Actions / GitLab CI) exécutant lint + tests Django + (optionnel) tests Tryton.

## 9. Prochaines étapes immédiates
1. Valider ce plan avec l'équipe (besoins métiers, priorités MVP).
2. Initialiser le dossier `portal/` (commande `django-admin startproject itf_portal`).
3. Ajouter les dépendances Python + Dockerfile + service `portal` dans Compose.
4. Migrer toutes les pages du site vitrine dans Django pour disposer d'une base fonctionnelle complète.
5. Implémenter une preuve de concept de connexion à Tryton (récupérer les commandes d'un client fictif).

## 10. Plan d'implémentation par étapes

### Étape 0 — Alignement & préparation (1-2 jours)
- Confirmer le périmètre MVP et valider ce plan avec les parties prenantes.
- Créer une feuille de route partagée (Jira/Linear) avec les user stories clés.
- Nettoyer la branche principale, définir la stratégie de branches (ex: `feature/portal-*`).
- Préparer un jeu de données Tryton de démonstration (clients tests, commandes, factures).

### Étape 1 — Infrastructure de base (2-3 jours)
- Ajouter le service `portal` et `traefik` au `docker-compose.yml` local ; vérifier le routage.
- Créer `portal/Dockerfile` avec installation des dépendances Python.
- Générer `portal/manage.py` via `django-admin startproject itf_portal`.
- Écrire `docs/development-setup.md` (prérequis, commandes `docker compose`).
- Mise en place Makefile ou scripts utilitaires (`make portal-up`, `portal-down`, `portal-shell`).

### Étape 2 — Configuration Django & outils (2 jours)
- Structurer les settings (`base.py`, `local.py`, `production.py`) avec `django-environ`.
- Configurer la base de données (PostgreSQL via Compose) + migration initiale.
- Ajouter outils de qualité : `black`, `ruff`, `pytest`, `pytest-django`, CI locale (GitHub Actions/Tox).
- Mettre en place un pipeline de tests automatique (lint + tests) déclenché sur PR.

### Étape 3 — Migration du site vitrine (3-4 jours)
- Copier tout le contenu de `siteweb-itf/src` dans `portal/static/` et `portal/templates/`.
- Créer une app `apps/core` gérant les vues publiques (home, pages marketing).
- Reproduire la navigation et le layout (`base.html`, partials) en respectant le design actuel.
- Configurer les routes publiques (`urls.py`) et vérifier la parité visuelle via Traefik.
- Retirer le besoin du service statique précédent dans `siteweb-itf` (une fois validé).

### Étape 4 — Authentification & gestion des comptes (4-5 jours)
- Décider entre compte Tryton direct ou base utilisateurs Django synchronisée ; documenter.
- Mettre en place `django-allauth` (ou implémentation custom) pour inscription/connexion.
- Créer les modèles `CustomerProfile` si base Django séparée (liens vers `party` Tryton).
- Gérer les flux : inscription, activation courriel, réinitialisation mot de passe, changement email.
- Protéger les vues / templates nécessitant authentification.

### Étape 5 — Intégration Tryton (POC → service partagé) (3-4 jours)
- Créer un module `portal/apps/core/services/tryton_client.py` encapsulant les appels JSON-RPC.
- Lire la configuration de connexion depuis l'environnement (`TRYTON_RPC_URL`, credentials).
- Implémenter un test de fumée (`pytest`) vérifiant l'accès Tryton en local.
- Documenter les endpoints utilisés dans `docs/tryton-api.md`.
- (Optionnel) Prototype module Tryton `itf_portal_api` si besoin d'API dédiées.

### Étape 6 — Module Commandes (sales) (4-6 jours)
- Créer l'app `apps/orders` avec vues liste/détail (`OrderListView`, `OrderDetailView`).
- Implémenter le service `TrytonSalesService` : filtrer par client connecté.
- Afficher les statuts, montants, lignes de commandes ; gérer la pagination.
- Ajouter tests d'intégration simulant un utilisateur client (fixtures Tryton).
- Préparer export PDF/CSV si requis (peut être poussé à une étape ultérieure).

### Étape 7 — Création de commandes (si dans le MVP) (5-7 jours)
- Construire un catalogue produits (service `TrytonProductService`).
- Mettre en place UI panier (session ou table temporaire).
- Valider les règles métier : disponibilité stock, tarification, taxes via Tryton.
- Gérer confirmation de commande, envoi de notification email.
- Tests couvrant les scénarios heureux + échecs (stock insuffisant, validation Tryton échouée).

### Étape 8 — Factures & paiements (4-6 jours)
- App `apps/billing` : liste de factures, détail, téléchargement PDF (via Tryton).
- Intégrer le provider de paiement choisi (Stripe/Moneris) si prévu.
- Synchroniser le statut de paiement avec Tryton (webhooks ou polling).
- Tests de réconciliation + gestion des erreurs (paiement refusé, double paiement).

### Étape 9 — Tableau de bord & communications (3-5 jours)
- Créer un dashboard personnalisé (vue `DashboardView`) consolidant commandes, factures, alertes.
- Module `communications` : historique des notifications, centre de documents partagés.
- Configurer envoi d'emails transactionnels (template HTML + queue si nécessaire).
- Ajouter préférences de notification utilisateur.

### Étape 10 — Observabilité, sécurité & durcissement (3-4 jours)
- Configurer logs structurés (JSON) et suivre les événements sensibles.
- Ajouter métriques/healthchecks (endpoint `/health/`, intégrer Sentry/Prometheus si prévu).
- Appliquer politiques sécurité : CSP, HSTS, gestion des mots de passe, verrouillage compte.
- Revue RGPD : politique de conservation, suppression compte client.
- Exécuter tests de pénétration internes ou audit (si programmé).

### Étape 11 — QA finale & déploiement (3-5 jours)
- Réaliser une passe QA complète (scripts de tests, checklists manuelles).
- Préparer scripts de déploiement (CI/CD) pour staging puis production.
- Écrire `docs/release-checklist.md` (pré-prod, prod, rollback).
- Former le support interne (guide utilisateur, FAQ).
- Go/No-Go meeting puis déploiement initial.

### Maintenance continue
- Collecter feedback utilisateur, ouvrir issues pour itérations futures (ex: mobile, reporting).
- Mettre en place cadence de mises à jour Tryton/Django (patchs sécurité).
- Suivre les indicateurs clés (adoption portail, commandes, support).
