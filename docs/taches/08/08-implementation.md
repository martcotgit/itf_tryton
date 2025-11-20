# Implémentation 08 – Liste des commandes client dans le portail

- **Analyse associée**: `docs/taches/08/08-analyse.md`
- **Date**: 2025-11-20
- **Auteur**: Codex

## Résumé des décisions
- Page dédiée « Voir mes commandes » avec pagination par défaut de 20 entrées, tri descendant sur la date de création.
- Colonnes et filtres retenus : numéro Tryton, référence client, statut (FR-CA), date prévue, total TTC + devise, date de création; filtres statut multi-choix, période 30/90/180 jours (défaut 90), recherche sur numéro/référence.

## Journal d'exécution
> Journal append-only : ajouter une ligne horodatée par action (`2024-05-16 14:02 | Action → Résultat`) en conservant les entrées existantes.
- 2025-11-20 06:40 | Initialisation du journal d’implémentation et rappel du scope (page dédiée, pagination 20, tri desc) → Succès
- 2025-11-20 06:40 | Alignement des colonnes/filtres (numéro, référence, statut FR-CA, dates, total TTC, recherche; filtres statut/période/recherche) selon brief/analyse → Succès
- 2025-11-20 06:55 | Implémentation du service `list_orders` (filtrage statut/période/recherche, pagination 20, mapping statuts FR-CA) → Succès
- 2025-11-20 07:05 | Création de la page dédiée « Voir mes commandes » (vue, URL, gabarit, CTA tableau de bord) et des tests unitaires associés (service + vue) → Succès
- 2025-11-20 07:10 | Exécution `docker compose run --rm portal python -m pytest apps/accounts/tests/test_orders_form.py` → Succès (16 tests passés)
- 2025-11-20 07:13 | Refonte UI de la page commandes (mise en page cartes, grilles filtres, badges statuts) + rerun pytest → Succès (16 tests passés)
- 2025-11-20 08:14 | Ajout du détail commande (service, vue, template, liens cliquables) + rerun pytest → Succès (16 tests passés)
- 2025-11-20 08:25 | Correction `int` non itérable pour les lignes Tryton (normalisation des IDs) + test de détail → Succès (17 tests passés)

## Modifications par fichier
| Fichier | Description succincte | Suivi PR / commit |
| --- | --- | --- |
| `docs/taches/08/08-implementation.md` | Journal d’implémentation mis à jour (décisions, actions, tentative de tests) | À venir |
| `docs/taches/08/08-analyse.md` | Ajustement du plan (pagination fixe 20) aligné sur les décisions | À venir |
| `docs/taches/08/brief.md` | Brief mis à jour (pagination 20, filtres/colonnes confirmés) | À venir |
| `portal/apps/accounts/services.py` | Ajout du service `list_orders` (filtres statut/période/recherche, pagination 20, mapping statuts, lecture des totaux) | À venir |
| `portal/apps/accounts/views.py` | Nouvelle `OrderListView` avec parsing des filtres, rendu de la page et coordination avec le service | À venir |
| `portal/apps/accounts/urls.py` | Ajout de la route `commandes/` pour la page « Voir mes commandes » | À venir |
| `portal/apps/accounts/templates/accounts/dashboard.html` | Ajout du lien « Voir mes commandes » en plus de « Nouvelle commande » | À venir |
| `portal/apps/accounts/templates/accounts/orders_list.html` | Nouveau gabarit de liste des commandes avec filtres, tableau et pagination | À venir |
| `portal/apps/accounts/templates/accounts/order_detail.html` | Page détail d’une commande (résumé, statuts, lignes) | À venir |
| `portal/apps/accounts/tests/test_orders_form.py` | Tests unitaires pour `list_orders`, `OrderListView` et détail commande (normalisation des lignes) | À venir |

## Tests manuels
- [ ] Affichage de la page « Voir mes commandes » avec pagination (20) et tri par date de création décroissante.
- [ ] Application des filtres (statut, période 90 jours par défaut, recherche numéro/référence) et cohérence des résultats.
- Notes: À exécuter après implémentation de la vue et du service de liste.

## Tests automatisés
- Commandes: `docker compose run --rm portal python -m pytest apps/accounts/tests/test_orders_form.py`
- Résultats: 17 tests passés (OK).

## Audits sécurité / qualité
- `npm audit`: Non lancé (non applicable dans cette itération documentaire).
- `composer audit`: Non lancé (non applicable).

## Points de suivi post-déploiement
- Valider la disponibilité du total TTC côté Tryton ou prévoir un fallback si le champ n’est pas exposé dans `sale.sale`.
- Surveiller la performance et la pertinence des filtres (statut, période, recherche) avec pagination 20; ajuster si volumétrie élevée.
