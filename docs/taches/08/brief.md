# 08 – Liste des commandes client dans le portail

- **Date**: 2025-11-20
- **Auteur**: Codex
- **Statut**: En préparation
- **Liens utiles**: portal/apps/accounts/views.py; portal/apps/accounts/services.py; portal/apps/accounts/templates/accounts/dashboard.html; portal/apps/accounts/templates/accounts/orders_form.html

## Description succincte
Permettre aux utilisateurs du portail client de consulter leurs commandes existantes (numéro, statut, date prévue, montant, référence) directement depuis le tableau de bord, en complément du flux de création déjà en place.

## Contexte
Le tableau de bord actuel offre un bouton « Nouvelle commande » mais aucune vue ne liste les commandes déjà déposées dans Tryton. Les clients doivent contacter le support pour suivre leurs demandes ou vérifier les montants. L’objectif est d’exposer une liste sécurisée et paginée des commandes liées au `party` Tryton de l’utilisateur authentifié, avec des libellés en français canadien et un accès simple depuis le tableau de bord.

## Objectifs / résultats attendus
- Afficher la liste des commandes Tryton liées au client (numéro, statut, date prévue, total TTC, référence client) dans le portail.
- Assurer un filtrage strict par `party` et des messages en français canadien en cas d’erreur ou d’absence de données.
- Offrir une navigation claire depuis le tableau de bord (section dédiée ou page) avec pagination ou limitation du nombre d’entrées pour préserver la performance.

## Travail à réaliser
- [ ] Cartographier les données nécessaires et le périmètre d’affichage pour la liste des commandes (colonnes : numéro, référence client, statut FR-CA, date prévue, total TTC + devise, date de création; filtres : statut multi-choix, période 30/90/180 jours par défaut 90 j, recherche numéro/référence; pagination/tri date création décroissante).
- [ ] Étendre `PortalOrderService` pour lire les commandes `sale.sale` filtrées par `party`, appliquer filtres/pagination, mapper les statuts et récupérer les totaux.
- [ ] Ajouter la vue/URL/template de liste dédiée (lien « Voir mes commandes » depuis le tableau de bord), plus les tests Django/Pytest couvrant service, vue et rendu.

## Périmètre
- **Inclus**:
  - Consultation des commandes du client authentifié avec tri/pagination de base.
  - Mapping des statuts Tryton vers des libellés en français canadien.
- **Exclus**:
  - Actions avancées (annulation, duplication, commentaires) hors périmètre immédiat.
  - Export ou impression PDF des commandes.

## Hypothèses et contraintes
- Les commandes sont lisibles via Tryton 7.6 et accessibles avec le client RPC existant (`get_tryton_client()`).
- L’utilisateur portail est déjà mappé à un `party` Tryton (précondition des tâches précédentes).
- Interface entièrement en français canadien; réutilisation des classes et styles existants.

## Dépendances et risques
- **Dépendances**:
  - `portal/apps/core/services/tryton_client.py` pour les appels JSON-RPC.
  - `portal/apps/accounts/services.py` (PortalOrderService) pour la logique d’accès aux commandes.
- **Risques**:
  - Pagination manquante ou requêtes non filtrées entraînant des délais importants côté Tryton.
  - Exposition involontaire de commandes d’autres parties si le filtrage `party` est incomplet.

## Références
- `portal/apps/accounts/views.py` — Vues actuelles du tableau de bord et du formulaire de commande.
- `portal/apps/accounts/templates/accounts/dashboard.html` — Point d’ancrage UX pour le lien vers la liste des commandes.

## Critères d'acceptation
- Un client authentifié voit sa liste de commandes avec numéro, statut, date prévue et total, limitée/paginée pour de bonnes performances.
- Les erreurs Tryton sont capturées et présentées en français canadien sans divulguer de détails sensibles, avec consignation côté serveur.
- La navigation vers la liste est disponible depuis le tableau de bord et respecte les protections d’accès (login requis).

## Points de contact
- PO Portail client — Amélie G.
- Référent Tryton — Marc-Antoine B.

## Questions ouvertes / suivi
- Emplacement décidé : page dédiée accessible via un lien « Voir mes commandes » depuis le tableau de bord.
- Filtres retenus : statut (multi-choix), période (30/90/180 jours, défaut 90 j), recherche numéro/référence; tri date création décroissante; pagination taille 10-20 (ajustable après retours).
