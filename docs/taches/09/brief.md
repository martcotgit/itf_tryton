# 09 – Section Factures du tableau de bord

- **Date**: 2025-11-20
- **Auteur**: Codex
- **Statut**: En préparation
- **Liens utiles**: portal/apps/accounts/views.py; portal/apps/accounts/templates/accounts/dashboard.html; portal/apps/accounts/services.py; tryton/modules/itf_portal_invoice/

## Description succincte
Ajouter un nouveau bloc « Factures » dans le tableau de bord avec un bouton « Voir mes factures ». Ce bouton ouvre une page dédiée listant les factures du client par lots de 20 entrées avec leurs numéros, dates, statuts en français canadien et montants dus.

## Contexte
Le tableau de bord actuel ne présente que des commandes et des raccourcis génériques; les clients doivent contacter le support pour obtenir leurs factures. La disponibilité directe de ces informations dans le portail réduira les échanges courriel, fluidifiera le suivi des comptes et préparera l’intégration future d’un bouton de paiement.

## Objectifs / résultats attendus
- Ajouter un bouton « Voir mes factures » dans le tableau de bord qui mène vers la nouvelle page dédiée.
- Afficher les factures du client dans une vue paginée (20 par page) avec colonnes numéro, dates clé, statut FR-CA et montant dû.
- Sécuriser l’accès en filtrant strictement sur le `party` Tryton associé à l’utilisateur connecté et gérer les erreurs avec des messages en français canadien.

## Travail à réaliser
- [ ] Recenser les champs `account.invoice` nécessaires (numéro, dates, statut, montant dû) et définir le contrat de données pour la liste paginée (20).
- [ ] Étendre le service portail pour récupérer les factures filtrées par `party`, appliquer tri/pagination et retourner les statuts traduits + montants dus.
- [ ] Ajouter le bouton « Voir mes factures » dans la vue du tableau de bord, créer la page/listing correspondante et couvrir service/vue avec des tests (dont cas vide).

## Périmètre
- **Inclus**:
  - Bouton « Voir mes factures » sur le tableau de bord.
  - Page dédiée listant les factures avec pagination fixe (20).
- **Exclus**:
  - Création ou modification de factures depuis le portail.
  - Processus de paiement en ligne (redirection vers fournisseur ou intégration passerelle).

## Hypothèses et contraintes
- Les factures proviennent du modèle standard `account.invoice` exposé via l’API Tryton 7.6 et interrogé par le client RPC existant.
- Chaque utilisateur portail est déjà lié à un `party` Tryton unique; sinon, la section restera vide.
- Interface 100 % en français canadien, textes stockés côté template pour faciliter les traductions.

## Dépendances et risques
- **Dépendances**:
  - `portal/apps/accounts/services.py` pour l’accès aux données Tryton côté portail.
  - Module Tryton standard `account_invoice` pour la structure des données factures.
- **Risques**:
  - Requêtes non filtrées pouvant exposer des factures d’un autre client si le `party` est mal appliqué.
  - Temps de réponse lent si le bloc récupère trop d’enregistrements ou manque d’index côté Tryton.

## Références
- `portal/apps/accounts/views.py` — Vues actuelles du tableau de bord à étendre.
- `portal/apps/accounts/templates/accounts/dashboard.html` — Bloc HTML cible pour l’insertion de la section « Factures ».

## Critères d'acceptation
- Le tableau de bord présente un bouton « Voir mes factures » menant à une page protégée qui liste uniquement les factures du `party` connecté.
- La page de liste affiche les factures par blocs de 20 (navigation suivante/précédente) avec numéro, dates, statut FR-CA et montant dû.
- Des tests automatisés couvrent le service (filtrage/pagination/traduction) ainsi que les vues (accès, état vide, pagination).

## Points de contact
- PO Facturation — Sarah L.
- Référent Tryton — Marc-Antoine B.

## Questions ouvertes / suivi
- Génération/lien PDF : fonctionnalité reportée, à revisiter une fois les factures visibles.
- Pas de bouton « Payer maintenant » pour cette itération; réévaluer après retours utilisateurs.
