# 10 – Page produits du portail public

- **Date**: 2025-11-23
- **Auteur**: Codex
- **Statut**: En préparation
- **Liens utiles**: portal/apps/core/views.py; portal/apps/core/urls.py; portal/templates/partials/header.html; portal/templates/core/home.html; tryton/scripts/create_pallet_products.py

## Description succincte
Créer une page « Produits » dans le portail public présentant l’offre complète de palettes (neuves, usagées, consignation, formats spéciaux). Cette page doit être indexable par les moteurs de recherche, raconter clairement les bénéfices de chaque palette et pousser les visiteurs à passer un appel ou une demande de soumission.

## Contexte
Le site actuel se limite à une page d’accueil axée sur les services, ce qui nuit au référencement des requêtes liées aux types précis de palettes recherchées par nos clients (dimensions 48x40, palettes recyclées, palettes séchées, etc.). Les ventes reçoivent encore trop d’appels exploratoires, faute d’une page de référence décrivant clairement l’inventaire de palettes disponibles, leurs caractéristiques et les quantités minimales. Une page produit optimisée SEO servira aussi d’ancrage pour les campagnes Google Business et les fiches partenaires.

## Objectifs / résultats attendus
- Offrir une URL dédiée (ex. `/produits/palettes/`) listant chaque famille de palettes avec leurs descriptions, dimensions, capacités de charge et disponibilités (neuves / usagées / grade A/B / consignation).
- Ajouter une navigation et un fil d’Ariane cohérents (menu principal, footer, balisage schema.org `Product`/`Offer`) pour améliorer le référencement organique et les extraits enrichis.
- Inclure des appels à l’action clairs (« Demander une soumission », numéro de téléphone cliquable) et des sections différenciantes (service de récupération, personnalisation, délais de livraison) pour convertir les visiteurs.
- Préparer l’intégration future avec Tryton en décrivant le format attendu des données (liste de palettes avec SKU/code, dimensions, catégorie, niveau d’inventaire) même si la première version est statique.

## Travail à réaliser
- [ ] Cartographier les types de palettes prioritaires (48x40 standard, bleue CHEP, palettes spéciales export, palettes usagées grade A/B, palettes consignées) et rédiger pour chacune un bloc de contenu combinant bénéfices, specs et mentions environnementales.
- [ ] Définir l’architecture SEO : titre de page, balises meta description/keywords FR-CA, données structurées `Product`/`Offer`, URL canonique, et un texte d’introduction de ~150 mots optimisé pour « palettes neuves », « palettes usagées » et « récupération de palettes ».
- [ ] Étendre l’app core (`portal/apps/core/views.py` + `urls.py`) avec une vue/template `core/products.html`, incluant une section filtrable (catégorie) et des CTA menant vers `/#contact` ou un futur formulaire.
- [ ] Prévoir le contrat de données avec Tryton (service dédié ou placeholder) en documentant les champs requis, règles de tri (populaires, par format) et système de mise en avant (étiquette « Populaire », « Récupérées ») pour un futur branchement API.
- [ ] Ajouter les tests de rendu (status 200, métadonnées, présence des sections) dans `portal/apps/core/tests/` et mettre à jour la documentation (README core ou note de tache) sur la procédure d’édition des palettes.
- [ ] Planifier la création de fiches détaillées par produit (URL unique, metadata optimisée, FAQ ciblée) à partir des familles prioritaires pour maximiser le SEO longue traîne et les pages d’atterrissage marketing.

## Périmètre
- **Inclus** : Page publique Produits, SEO on-page, navigation mise à jour, contenu FR-CA, instrumentation future (contrat de données, placeholders).  
- **Exclus** : Tunnel de commande en ligne, synchronisation temps réel avec Tryton, calcul automatique d’inventaire ou de prix dynamiques.

## Hypothèses et contraintes
- Les personas ciblés sont des responsables logistiques au Saguenay–Lac-Saint-Jean recherchant un fournisseur local de palettes.  
- Les textes doivent respecter le ton professionnel et local (français canadien, références régionales).  
- Les ressources médias (photos) ne sont pas encore disponibles; prévoir une section modulable pour insérer des images plus tard.  
- Le site doit rester léger (pas de dépendances JS lourdes) et conserver l’accessibilité AA (contrastes, balises ARIA, navigation clavier).

## Dépendances et risques
- **Dépendances** : navigation partagée (`portal/templates/partials/header.html`), configuration SEO existante dans `portal/templates/core/home.html`, scripts Tryton de génération de palettes pour harmoniser les codes (voir `tryton/scripts/create_pallet_products.py`).  
- **Risques** : contenu dupliqué avec d’autres pages (pénalité SEO), mismatch entre les palettes annoncées et l’inventaire réel (doit être synchronisé régulièrement), surcharge de maintenance si le contenu reste statique trop longtemps.

## Références
- `portal/templates/core/home.html` — structure actuelle et tonalité marketing.  
- `tryton/scripts/create_pallet_products.py` — nomenclature des produits palettes et attributs disponibles.  
- `portal/apps/core/tests/` — exemples pour ajouter des tests de vue TemplateView.

## Critères d'acceptation
- La route `/produits/` (ou `/produits/palettes/`) retourne HTTP 200, est accessible depuis le menu principal/footer et expose balises meta optimisées + JSON-LD `Product` couvrant au moins trois offres.  
- Chaque type de palette listé présente nom, dimensions, capacité, avantages, disponibilité (neuve/usagée) et un CTA clair (courriel, téléphone ou formulaire).  
- Les tests unitaires valident le rendu, les balises critiques (title/meta) et l’accessibilité minimale (présence d’un `main`, `h1`, navigation).  
- La doc de tache référence comment mettre à jour le contenu et rappelle la future intégration Tryton.

## Points de contact
- PO Marketing — Julie N.  
- Responsable SEO — Étienne D.  
- Référent Tryton — Marc-Antoine B.

## Questions ouvertes / suivi
- Quelle source autoritaire pour les prix/quantités (fichier CSV, Tryton, saisie marketing)?  
- Souhaite-t-on une section de témoignages ou études de cas sur la même page pour renforcer l’engagement?  
- Faut-il prévoir une version anglaise courte pour les clients hors Québec?
