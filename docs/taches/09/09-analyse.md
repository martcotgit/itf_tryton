# Analyse 09 – Section Factures du tableau de bord

- **Fiche mission**: `docs/taches/09/brief.md`
- **Date**: 2025-11-20
- **Auteur**: Codex

## Contexte et objectifs
- Le tableau de bord du portail client ne contient pas encore d’entrée permettant de consulter les factures; les utilisateurs doivent solliciter le support pour suivre leurs paiements.
- Objectifs principaux : ajouter un bouton « Voir mes factures » et une vue paginée (20 par page) filtrée sur le `party` Tryton pour exposer numéro, dates clé, statut FR-CA et montant dû des factures `account.invoice`.

## État actuel / inventaire
- **Commandes à lancer**: `docker compose run --rm tryton python -m unittest discover -s /opt/trytond/modules/itf_portal_invoice/tests`
- **Fichiers / dossiers clefs**:
  - `portal/apps/accounts/views.py` — Vues Django du tableau de bord; point d’entrée pour ajouter le bouton et la nouvelle route.
  - `portal/apps/accounts/services.py` — Contient les services Tryton utilisés par le portail (ex. commandes); à étendre pour exposer les factures.
- **Dépendances critiques**:
  - trytond `account_invoice` — version actuelle 7.6 / cible 7.6 (aucun changement requis, mais confirmer API RPC disponible).
  - portal Django (packages internes) — version actuelle n/a / cible n/a (réutilisation des patterns existants pour les services/pagination).

## Risques et compatibilités
- Latence ou surcharge si la requête facture n’est pas paginée correctement côté Tryton.
- Erreurs de permission si le filtrage par `party` n’est pas strict, pouvant exposer des factures d’autres clients.
- Incohérences d’interface si les statuts Tryton ne sont pas traduits en français canadien avant affichage.

## Plan d'implémentation
1. Cartographier la structure `account.invoice` (champs requis, filtres, tri) et définir le contrat de sortie du service (pagination 20, mapping statuts, montant dû).
2. Étendre le service portail (nouvelle méthode ou classe dédiée) pour requêter Tryton via RPC, sécuriser par `party`, implémenter pagination/tri et tests unitaires.
3. Ajouter le bouton « Voir mes factures » au tableau de bord, créer la nouvelle vue/template paginée, traduire les messages FR-CA et couvrir avec tests d’intégration (vue, contexte, état vide).

## Questions ouvertes / décisions
- Format exact des montants (devise et précision) à afficher; clarifier si le montant dû doit inclure les taxes ou le reste à payer.
- Décision : pas de bouton « Payer maintenant » ni de lien PDF pour cette itération; revoir ces besoins une fois la liste en place.

## Journal (à compléter pendant l'exécution)
- **Commandes lancées**:
  - `…` — À renseigner lors de l’exécution.
- **Tests exécutés**:
  - `…` — À renseigner lors de l’exécution.
- **Notes libres**: À compléter.
