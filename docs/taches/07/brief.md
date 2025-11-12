# 07 – Formulaire de commandes (phase initiale)

- **Date**: 2025-11-12
- **Auteur**: Codex
- **Statut**: En préparation
- **Liens utiles**: docs/taches/05/brief.md, portal/apps/accounts/forms.py, portal/apps/accounts/views.py, portal/apps/accounts/templates/accounts/dashboard.html, portal/apps/core/services/tryton_client.py

## Description succincte
Livrer la première itération du formulaire de commandes dans le portail client afin que les organisations puissent soumettre une demande d’achat structurée (produits, quantités, notes) qui se traduit immédiatement par un brouillon `sale.sale` dans Tryton. Cette tâche se concentre sur l’ossature du formulaire (champs, validations, navigation) et établit les services nécessaires pour créer une commande à partir du portail.

## Contexte
La tâche 05 a défini la vision globale « Commandes client dans le portail », mais aucune interface n’existe encore pour initier une commande. Les équipes de service continuent donc de saisir manuellement les demandes reçues par courriel. Nous devons amorcer le formulaire de commandes côté portail pour accélérer la collecte d’information, respecter la terminologie en français canadien et préparer les itérations suivantes (ajout multi-lignes avancées, annexes, annulation). La base de code actuelle dispose d’un client JSON-RPC Tryton (`portal/apps/core/services/tryton_client.py`) et de vues authentifiées (`portal/apps/accounts/views.py`), ce qui permet de bâtir rapidement un flux dédié.

## Objectifs / résultats attendus
- Ajouter un point d’entrée « Nouvelle commande » sur le tableau de bord client qui dirige vers un gabarit dédié au formulaire de commandes.
- Modéliser un `OrderDraftForm` (métadonnées + lignes avec formset) qui applique les validations métier (quantités positives, produits permis, dates requises) et affiche les messages en français canadien.
- Orchestrer la création d’un brouillon de commande Tryton via un nouveau service spécialisé tout en journalisant les erreurs et en retournant une confirmation claire au client.

## Travail à réaliser
- [ ] Définir la structure exacte du formulaire de commandes (champs requis, formset pour 1 à 5 lignes, aide contextuelle) et l’ajouter à `portal/apps/accounts/forms.py` avec un service injecté pour valider les produits autorisés.
- [ ] Créer la vue `OrderCreateView` + URL sécurisée (`accounts/orders/new/`) + gabarits (`accounts/orders_form.html`, bloc partiel pour les lignes) et arrimer le CTA « Nouvelle commande » sur `accounts/dashboard.html`.
- [ ] Implémenter un `PortalOrderService` (dans `portal/apps/accounts/services.py` ou un module dédié) qui prépare la charge utile Tryton (`sale.sale`, `sale.line`), effectue les appels RPC via `get_tryton_client()` et gère les exceptions métier.
- [ ] Couvrir le formulaire, la vue et le service par des tests Django (`portal/apps/accounts/tests/test_orders_form.py`) exécutés avec `docker compose run --rm portal python -m pytest portal/apps/accounts/tests/test_orders_form.py`, puis documenter la commande dans le journal de tâche.

## Périmètre
- **Inclus**:
  - Affichage et validation d’un formulaire de commandes simple (champ référence client, date souhaitée, adresse de livraison sélectionnée, 1-5 lignes produit/quantité/unité) avec messages en français canadien.
  - Conversion d’une soumission valide en commande Tryton à l’état « Draft » associée au client authentifié, avec enregistrement d’une note interne contenant la référence portail.
  - Gestion d’erreurs utilisateur (champ manquant, produit non autorisé) et techniques (erreur RPC) via messages en haut du formulaire.
- **Exclus**:
  - Gestion avancée des remises, taxes personnalisées ou configurations multi-devises.
  - Téléversement de fichiers ou ajout de commentaires riches à la commande.
  - Liste et suivi des commandes (déjà couverts par la portée globale de la tâche 05, livrable ultérieur).

## Hypothèses et contraintes
- Les clients disposent d’au moins une adresse de livraison synchronisée; la vue charge ces options via Tryton et en sélectionne une par défaut.
- Les produits commandables sont restreints à un sous-ensemble (champ `can_be_sold` + groupe portail) retourné par Tryton; le formulaire doit empêcher toute valeur hors liste.
- Les quantités sont exprimées dans l’unité de mesure par défaut du produit (pas de conversion côté portail pour cette phase).
- L’interface doit rester entièrement en français canadien, responsive, sans dépendance front additionnelle; réutiliser les classes `form-input` existantes.
- En cas d’échec Tryton, aucune commande partielle ne doit être laissée; la transaction doit être annulée et une entrée de log doit être créée pour le support.

## Dépendances et risques
- **Dépendances**:
  - `portal/apps/core/services/tryton_client.py` pour initier les appels JSON-RPC vers `sale.sale`.
  - `portal/apps/accounts/services.py` (et futures extensions) pour récupérer le `party` lié à l’utilisateur et ses adresses.
  - Données Tryton (`product.product`, `sale.sale`, `sale.line`, `party.address`) disponibles sur l’environnement de développement via `docker compose`.
- **Risques**:
  - Temps de réponse lent lors du chargement des produits si aucun cache n’est utilisé; pourrait nécessiter un préchargement ou une API interne.
  - Incohérences dans les taxes/montants si le portail tente de recalculer des totaux au lieu de laisser Tryton le faire.
  - Conflits de validation (ex. références client dupliquées) si les règles Tryton ne sont pas reproduites dans le formulaire.

## Références
- `docs/taches/05/brief.md` — vision globale des commandes portail.
- `portal/apps/accounts/templates/accounts/dashboard.html` — point d’ancrage pour le bouton « Nouvelle commande ».
- `portal/apps/accounts/forms.py` — formulaires existants à étendre pour héberger `OrderDraftForm`.
- `portal/apps/accounts/views.py` — contiendra la vue `OrderCreateView`.
- `portal/apps/core/services/tryton_client.py` — client Tryton réutilisé par le nouveau `PortalOrderService`.

## Critères d'acceptation
- Le tableau de bord affiche un CTA « Nouvelle commande » menant à un formulaire dédié accessible uniquement aux clients authentifiés.
- Une soumission valide crée un brouillon `sale.sale` lié au client dans Tryton, puis redirige l’utilisateur vers une page de confirmation avec message de succès en français canadien.
- Les validations empêchent les lignes vides ou invalides et affichent des messages clairs; toute erreur technique est tracée et communiquée à l’utilisateur sans fuite de détails sensibles.

## Points de contact
- PO Portail client — Amélie G.
- Référent Tryton (ventes) — Marc-Antoine B.
- Support applicatif / QA — Codex

## Questions ouvertes / suivi
- Faut-il limiter le formulaire de commandes à certains groupes (clients corporatifs vs. PME) dès cette première phase?
- Quel libellé afficher pour les produits issus de Tryton (nom court, nom complet, SKU)? Besoin d’un attribut personnalisé?
- Devons-nous afficher un récapitulatif taxes/montant dès la soumission ou attendre une itération ultérieure lorsque la grille tarifaire sera figée?
