# Analyse 08 – Suivi des commandes existantes

- **Fiche mission**: `docs/taches/08/brief.md`
- **Date**: 2025-11-20
- **Auteur**: Codex

## Contexte et objectifs
- Le tableau de bord client offre un bouton « Nouvelle commande » via `OrderCreateView`, mais aucune liste des commandes existantes liées au `party`; les clients doivent encore contacter le support pour suivre leurs demandes.
- Objectifs : exposer une liste paginée des commandes Tryton du client (numéro, statut, date prévue, total TTC, référence), sécurisée par le filtrage `party`, accessible depuis le tableau de bord, avec messages en français canadien.

## État actuel / inventaire
- **Commandes à lancer**: `docker compose run --rm portal python -m pytest portal/apps/accounts/tests`
- **Fichiers / dossiers clefs**:
  - `portal/apps/accounts/views.py` — héberge `ClientDashboardView` et `OrderCreateView`; à étendre avec la vue de liste et la navigation.
  - `portal/apps/accounts/templates/accounts/dashboard.html` — tableau de bord affichant le CTA « Nouvelle commande »; point d’ancrage pour la section commandes.
  - `portal/apps/accounts/templates/accounts` — contient `orders_form.html`; à compléter avec un gabarit de liste (`orders_list.html` ou section dédiée).
  - `portal/apps/accounts/services.py` — `PortalOrderService` gère la création; devra lire les commandes `sale.sale` filtrées par `party`/statut et formater statuts + montants.
  - `portal/apps/core/services/tryton_client.py` — client JSON-RPC utilisé pour les appels Tryton (sessions, contexte compagnie/devise).
- **Dépendances critiques**:
  - Tryton — version actuelle 7.6 / cible 7.6
  - Django — version actuelle 4.2.11 / cible 4.2 LTS

## Risques et compatibilités
- Filtrage incomplet sur le `party` ou les statuts exposant des commandes d’autres clients ou des brouillons internes.
- Volume de commandes sans pagination ni cache entraînant des appels RPC lourds et un tableau de bord lent.
- Décalage des libellés/états entre Tryton et le portail (traductions, codes couleurs) rendant la lecture confuse pour les clients et le support.

## Plan d'implémentation
1. Cartographier la liste cible sur une page dédiée (« Voir mes commandes ») avec colonnes : numéro Tryton, référence client, statut (mappé FR-CA), date de livraison prévue, total TTC (devise compagnie), date de création ; filtres : statut multi-choix (Brouillon, En traitement, Expédiée, Facturée, Annulée), période (30/90/180 jours, défaut 90 j), recherche libre sur numéro/référence ; tri par date de création décroissante ; pagination (taille 10-20).
2. Étendre `PortalOrderService` pour lire `sale.sale` filtré par `party` + filtres choisis, appliquer pagination/tri, calculer total TTC ou fallback sur champ disponible, et exposer un mapping clair des statuts pour le template.
3. Créer la vue/URL/template de liste dédiée, lier le tableau de bord via un CTA, injecter filtres/état de pagination, gérer les messages utilisateur, puis couvrir service + vue + rendu par des tests Django/Pytest.

## Questions ouvertes / décisions
- Emplacement : page dédiée accessible via un lien « Voir mes commandes » depuis le tableau de bord (décidé).
- Filtres retenus : statut (multi-choix), période (30/90/180 jours, défaut 90 j), recherche sur numéro/référence ; tri date création décroissante ; pagination (taille 10-20). Ajustements possibles après premiers retours.

## Journal (à compléter pendant l'exécution)
- **Commandes lancées**:
  - `À documenter` — À compléter
- **Tests exécutés**:
  - `À documenter` — À compléter
- **Notes libres**: À compléter
