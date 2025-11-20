# Implémentation 09 – Section Factures du tableau de bord

- **Analyse associée**: `docs/taches/09/09-analyse.md`
- **Date**: 2025-11-20
- **Auteur**: Codex

## Résumé des décisions
- Implémenter la récupération des factures via le modèle Tryton standard `account.invoice` avec pagination 20.
- Reporter les fonctionnalités de paiement et de téléchargement PDF à une itération ultérieure.

## Journal d'exécution
> Journal append-only : ajouter une ligne horodatée par action (`2024-05-16 14:02 | Action → Résultat`) en conservant les entrées existantes.
- 2025-11-20 10:05 | Initialisation du journal d'implémentation pour la tâche 09 → Succès
- 2025-11-20 11:10 | Ajout des dataclasses PortalInvoice* et du service Tryton paginé dans `services.py` → Succès
- 2025-11-20 11:25 | Création de la vue Django, du template `invoices_list.html`, du lien tableau de bord et du routing → Succès
- 2025-11-20 11:35 | Ajout des tests service/vue + exécution `docker compose run --rm portal python manage.py test apps.accounts.tests.test_invoices` → Succès
- 2025-11-20 12:30 | Script Proteus `create_invoice_from_order.py` pour générer une facture de test (commande -> facture) et exécution `docker compose run --rm tryton python3 /opt/trytond/scripts/create_invoice_from_order.py --email martcot@gmail.com` → Succès
- 2025-11-20 12:38 | Correction du champ due date (`payment_term_date`) dans `PortalInvoiceService` + relance des tests `apps.accounts.tests.test_invoices` → Succès
- 2025-11-20 13:16 | Amélioration de l’interface `invoices_list.html` (hero, résumé, badges) + mise à jour de la vue/tests → Succès

## Modifications par fichier
| Fichier | Description succincte | Suivi PR / commit |
| --- | --- | --- |
| `portal/apps/accounts/services.py` | Ajout des exceptions/dataclasses et du `PortalInvoiceService` (pagination Tryton). | À déterminer |
| `portal/apps/accounts/views.py` | Nouvelle `InvoiceListView` et import du service dans les vues existantes. | À déterminer |
| `portal/apps/accounts/urls.py` | Route `factures/` pointant vers la nouvelle vue. | À déterminer |
| `portal/apps/accounts/templates/accounts/dashboard.html` | Bouton « Voir mes factures » relié au tableau de bord. | À déterminer |
| `portal/apps/accounts/templates/accounts/invoices_list.html` | Nouveau template listant les factures et la pagination FR-CA. | À déterminer |
| `portal/apps/accounts/views.py` | Calcul du résumé (totaux) et support des décimales pour la page « Factures ». | À déterminer |
| `portal/apps/accounts/tests/test_invoices.py` | Nouveaux tests unitaires pour le service et la vue. | À déterminer |
| `tryton/scripts/create_invoice_from_order.py` | Script Proteus pour transformer une commande en facture de test (draft). | À déterminer |

## Tests manuels
- [ ] Vérifier l'affichage du bouton « Voir mes factures » sur le tableau de bord.
- [ ] Naviguer vers la page des factures et valider la pagination par 20 éléments.
- Notes: À exécuter après implémentation.

## Tests automatisés
- Commandes: `docker compose run --rm portal python manage.py test apps.accounts.tests.test_invoices`
- Résultats: Succès (4 tests, base de données temporaire détruite automatiquement).

## Audits sécurité / qualité
- `npm audit`: À exécuter si impact front.
- `composer audit`: Sans objet (pas de PHP).

## Points de suivi post-déploiement
- Surveiller les performances des appels Tryton (temps de réponse, pagination) lors des premières utilisations.
- Recueillir les retours utilisateurs sur la pertinence des colonnes et filtres pour ajuster si nécessaire.
