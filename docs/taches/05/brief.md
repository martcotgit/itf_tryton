# 05 – Commandes client dans le portail

- **Date**: 2025-11-10
- **Auteur**: Codex
- **Statut**: En préparation
- **Liens utiles**: docs/processus-taches.md; portal/apps/accounts/views.py; portal/apps/accounts/templates/accounts/dashboard.html

## Description succincte
Mettre en place, dans la section client du portail, un flux complet de création et de suivi des commandes synchronisé avec Tryton afin que les clients puissent soumettre, consulter et annuler leurs demandes directement en libre-service.

## Contexte
Le portail Django (`portal/`) n'affiche pour l'instant qu'un tableau de bord statique (gabarit `accounts/dashboard.html`) adossé aux vues de `portal/apps/accounts/views.py`. Aucun formulaire ni API n'expose les commandes gérées dans Tryton, ce qui force l'équipe service à saisir manuellement les demandes client. La tâche vise à aligner l'expérience portail sur les processus Tryton 7.6 en réutilisant `portal/apps/core/services/tryton_client.py` pour parler au backend.

## Objectifs / résultats attendus
- Offrir une interface client claire pour créer une commande avec validation des champs obligatoires et messages en français canadien.
- Afficher la liste des commandes Tryton (statut, total, date de livraison prévue) avec un filtrage de base.
- Synchroniser les actions clés (création, annulation, commentaire) vers Tryton en moins de 5 secondes pour éviter les doublons.

## Travail à réaliser
- [ ] Cartographier les données nécessaires (produits autorisés, champs obligatoires, statuts Tryton) et définir le modèle de formulaire.
- [ ] Ajouter les vues Django (formulaire + liste) et brancher les appels RPC via `tryton_client.py`, y compris la gestion d'erreurs côté client.
- [ ] Documenter et outiller les tests unitaires/integres pour garantir qu'une commande soumise depuis le portail se retrouve dans Tryton avec le bon statut initial.

## Périmètre
- **Inclus**:
  - Création et consultation des commandes client dans le portail.
  - Validation métier de premier niveau (champs requis, limites de quantité, statut initial).
- **Exclus**:
  - Paiement en ligne ou traitement de facturation.
  - Automatisation des notifications courriel (à traiter dans une tâche ultérieure).

## Hypothèses et contraintes
- Les clients continuent de s'authentifier via le module `accounts`, aucune modification SSO requise.
- Les API Tryton d'insertion de commandes sont accessibles via le service RPC existant sans déploiement supplémentaire.
- Respect des consignes d'interface (libellés bilingues interdits; uniquement français canadien pour cette section).

## Dépendances et risques
- **Dépendances**:
  - `portal/apps/core/services/tryton_client.py` pour la communication RPC.
  - Flux de données Tryton (module ventes) afin de récupérer produits, taxes et statuts.
- **Risques**:
  - Incohérences possibles si les statuts Tryton changent sans mise à jour du portail.
  - Charge accrue sur le service RPC si la pagination ou les filtres sont mal implémentés.

## Références
- `portal/apps/accounts/views.py` — Vues actuelles de la section client à étendre.
- `portal/apps/accounts/templates/accounts/dashboard.html` — Point d'ancrage UX pour intégrer formulaire et liste des commandes.

## Critères d'acceptation
- Un client authentifié peut créer une commande valide et voir une confirmation contextualisée en moins de cinq secondes.
- La liste des commandes présente au minimum le numéro, la date, le statut Tryton et le montant TTC avec un indicateur lorsque la commande est annulée.
- Toute erreur Tryton est relayée au client via un message en français canadien, journalisée côté serveur et accompagnée d'un identifiant de corrélation.

## Points de contact
- PO Portail client — Amélie G.
- Responsable Tryton / Intégrations — Marc-Antoine B.

## Questions ouvertes / suivi
- Nécessité de limiter la création de commandes à certains groupes (p. ex. clients corporatifs)?
- Décider du mapping final des statuts Tryton vers les libellés affichés afin d'éviter des traductions ambiguës.
