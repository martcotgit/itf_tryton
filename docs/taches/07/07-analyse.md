# Analyse 07 – Formulaire de commandes (phase initiale)

- **Fiche mission**: `docs/taches/07/brief.md`
- **Date**: 2025-11-12
- **Auteur**: Codex

## Contexte et objectifs
- Doter le portail client d’un premier formulaire « Nouvelle commande » afin de remplacer les échanges manuels et créer directement des brouillons `sale.sale` dans Tryton.
- Garantir que la structure du formulaire (métadonnées, lignes produits, validations) et les services associés respectent les règles métier existantes, en français canadien, avec un flux fiable et traçable.

## État actuel / inventaire
- **Commandes à lancer**: `docker compose run --rm portal python -m pytest portal/apps/accounts/tests/test_orders_form.py`
- **Fichiers / dossiers clefs**:
  - `portal/apps/accounts/forms.py` — accueillera `OrderDraftForm` et le formset de lignes avec validations locales.
  - `portal/apps/accounts/views.py` — ajoutera `OrderCreateView`, protections d’accès et gestion des messages utilisateur.
  - `portal/apps/accounts/templates/accounts/dashboard.html` — devra afficher le CTA « Nouvelle commande » et les liens de navigation.
  - `portal/apps/accounts/templates/accounts/orders_form.html` (à créer) — gabarit du formulaire, réutilisant les classes `form-input`.
  - `portal/apps/accounts/services.py` & `portal/apps/core/services/tryton_client.py` — base de `PortalOrderService`, récupération des parties, adresses, produits autorisés.
  - `portal/apps/accounts/tests/` — contiendra les tests unitaires/intégrés dédiés (`test_orders_form.py`).
- **Dépendances critiques**:
  - tryton/tryton — version actuelle 7.6 / cible 7.6 (image Docker de référence pour la création des commandes).
  - Django — version actuelle 4.2.11 / cible 4.2 LTS (support de Form/FormSet, vues CBV, messages).

## Risques et compatibilités
- Temps de réponse lent ou erreurs si le chargement des produits/adresses se fait à chaque requête sans cache, impactant l’expérience utilisateur.
- Divergence entre validations portail et règles Tryton (quantités, références uniques) pouvant provoquer des erreurs RPC difficiles à comprendre pour le client.
- Gestion insuffisante des erreurs techniques (timeouts, authentification Tryton) qui laisserait l’utilisateur sans confirmation et pourrait créer des doublons lors d’une nouvelle tentative.

## Plan d'implémentation
1. Cartographier les données nécessaires (produits commandables, adresses de livraison, paramètres par défaut) et définir les interfaces du `PortalOrderService`.
2. Implémenter `PortalOrderService` (récupération du party, préparation `sale.sale`/`sale.line`, gestion des exceptions) en s’appuyant sur `get_tryton_client()`.
3. Créer `OrderDraftForm` + formset de lignes (1-5 items), avec validations (quantité > 0, produit obligatoire, déduplication) et instrumentation des messages localisés.
4. Ajouter `OrderCreateView`, les URLs et les gabarits (`orders_form.html`, fragments de lignes), plus le CTA « Nouvelle commande » sur le tableau de bord.
5. Écrire les tests Django/Pytest (formulaire, vue, service avec client Tryton simulé), puis documenter les commandes exécutées dans le journal de tâche.

## Questions ouvertes / décisions
- Faut-il restreindre l’accès au formulaire à certains groupes (clients corporatifs) dès cette phase? Non
- Quel libellé exact doit être affiché pour les produits (nom complet, SKU, combinaison)? Nom complet
- Doit-on afficher un récapitulatif (taxes, total estimé) avant soumission ou laisser Tryton produire ces informations plus tard? plus tard

## Journal (à compléter pendant l'exécution)
- **Commandes lancées**:
  - `À documenter` — À compléter
- **Tests exécutés**:
  - `À documenter` — À compléter
- **Notes libres**: À compléter
