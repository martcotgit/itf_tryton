# Analyse 10 – Page produits du portail public

- **Fiche mission**: `docs/taches/10/brief.md`
- **Date**: 2025-11-23
- **Auteur**: Codex

## Contexte et objectifs
- Le portail public ne propose qu'une page d'accueil orientée services; il manque une vitrine dédiée aux palettes pour répondre aux recherches spécifiques (48x40, grades A/B, consignation) et réduire les demandes exploratoires aux ventes.
- Construire une page Produits optimisée SEO (FR-CA) avec contenu riche, navigation cohérente et points d'appel à l'action, tout en préparant un futur branchement aux données Tryton.

## État actuel / inventaire
- **Commandes à lancer**: `docker compose up --build && docker compose run --rm portal python manage.py test core`
- **Fichiers / dossiers clefs**:
  - `portal/templates/core/home.html` — Sert de référence stylistique et contient déjà meta + JSON-LD à dupliquer/adapter.
  - `portal/apps/core/views.py` — Déclare la `HomeView`; la future `ProductsView` devra y vivre avec ses URLs et tests associés.
- **Dépendances critiques**:
  - Django — version actuelle 4.2.11 / cible 4.2.11 (structure TemplateView, routing, tests).
  - Tryton 7.6 RPC (scripts `tryton/scripts/create_pallet_products.py`) — version actuelle 7.6 / cible 7.6 (nomenclature produits pour l'intégration future).

## Risques et compatibilités
- Risque de contenu dupliqué avec la page Services/Accueil entraînant une pénalité SEO si les textes ne sont pas différenciés.
- Seuil d'inventaire : pour éviter d'afficher des palettes à zéro stock, il faudra brancher la page sur un service Tryton (`products_service.list_available_palettes()`) qui filtre par disponibilité et met en cache les résultats (Redis 15-30 min) afin de rester aligné sur l'inventaire réel.
- Absence de médias ou données dynamiques pourrait rendre la page statique, réduisant l'engagement si l'information n'est pas maintenue.

## Plan d'implémentation
1. Consolider la structure de page (sections, titres, metadata, JSON-LD) et rédiger les contenus FR-CA par famille de palettes, incluant CTA et FAQ.
2. Implémenter la vue/template `ProductsView`, mettre à jour la navigation (header/footer), ajouter tests de rendu et valider l'accessibilité de base.
3. Documenter le contrat de données avec Tryton, prévoir les placeholders pour filtres et fiches détaillées, puis planifier la génération des pages individuelles.

## Questions ouvertes / décisions
- Quelle source officielle fournit les prix, quantités minimales et disponibilités à afficher (CSV marketing, extraction Tryton, autre)? Tryton
- Souhaite-t-on ajouter une version anglaise ou des témoignages clients sur cette page dès la première itération? Non pas de version anglaise et pas de témoignage pour le moment

## Journal (à compléter pendant l'exécution)
- **Commandes lancées**:
  - `À compléter` — À compléter
- **Tests exécutés**:
  - `À compléter` — À compléter
- **Notes libres**: À compléter
