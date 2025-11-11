# 04 – Gestion du profil client du portail

- **Date**: 2025-11-10
- **Auteur**: Codex
- **Statut**: Planifiée
- **Liens utiles**: docs/taches/03/brief.md, portal/apps/accounts/views.py, portal/apps/accounts/services.py

## Description succincte
Offrir aux clients connectés une page « Profil » dans le portail permettant de consulter, modifier et synchroniser leurs informations personnelles et d’entreprise avec Tryton sans devoir passer par le support.

## Contexte
La tâche 02 a livré l’accès client (authentification, tableau de bord minimal) et la tâche 03 a préparé l’inscription libre-service. Il manque maintenant un écran centré sur l’autonomie du client pour maintenir ses coordonnées (contact principal, entreprise, adresses, préférences de communication). Le portail Django dispose déjà d’un service `PortalAccountService` pour piloter Tryton; on doit l’étendre pour la lecture/écriture du profil tout en respectant les validations métier existantes côté ERP.

## Objectifs / résultats attendus
- Afficher un écran « Profil » pré-rempli avec les données du compte Tryton lié à l’utilisateur authentifié.
- Permettre la mise à jour des champs principaux (prénom, nom, entreprise, téléphone, préférences d’avis) avec validation front/back cohérente.
- Offrir un flux complet de changement de mot de passe incluant validations locales, contraintes Tryton et confirmation utilisateur.
- Propager chaque modification côté Tryton (party + contact mechanisms + mot de passe) et enregistrer un historique succinct pour les audits de support.

## Travail à réaliser
- [ ] Ajouter la route, la vue Django et le gabarit `accounts/profile.html` avec navigation depuis le tableau de bord.
- [ ] Implémenter la collecte et la sauvegarde des données via un nouveau service/fonctions dans `PortalAccountService` (lecture, patch, gestion d’erreurs Tryton).
- [ ] Ajouter un sous-formulaire ou un composant dédié au changement de mot de passe (validation actuelle + confirmée) et sécuriser les appels Tryton.
- [ ] Couvrir l’affichage, la mise à jour des données et le changement de mot de passe par des tests Django (vue, formulaire, appels Tryton simulés) et documenter le flux dans le journal de tâche.

## Périmètre
- **Inclus**:
  - Consultation/édition des champs d’identité du client (prenom, nom, entreprise) et des coordonnées principales (courriel non éditable, téléphone, adresse postale simple).
  - Messages de confirmation/erreur localisés et retraçage minimal (journalisation, message dans `messages.success` / `messages.error`).
  - Gestion complète du changement de mot de passe (formulaire dédié, validation côté portail, propagation côté Tryton).
- **Exclus**:
  - Gestion des multi-contacts associés à une entreprise.
  - Synchronisation d’attributs avancés (préférences marketing, identifiants fiscaux multiples) ou import/export de documents.

## Hypothèses et contraintes
- Chaque utilisateur Django est déjà lié à un `party` Tryton via les travaux antérieurs; l’ID partie sera accessible en session ou via Lookup RPC.
- Les appels RPC à Tryton doivent demeurer synchrone (pas de file d’attente) et respecter les restrictions du pare-feu (pas de réseau public).
- L’interface doit rester en français canadien, responsive et cohérente avec `portal/static/css/style.css` sans introduire de dépendances front complexes.
- Le flux de changement de mot de passe doit respecter les validateurs existants (`portal/apps/accounts/password_validators.py`) et informer clairement l’utilisateur en cas d’échec Tryton.

## Dépendances et risques
- **Dépendances**:
  - Authentification du portail (`accounts:login`, `ClientDashboardView`) qui redirige vers la nouvelle page Profil.
  - Connectivité Tryton via `apps.core.services.get_tryton_client` et configuration `TRYTON_PORTAL_GROUP`.
- **Risques**:
  - Désynchronisation des données si une erreur Tryton n’est pas surfacée clairement (perte de confiance du client).
  - Exposition involontaire de champs sensibles si la sérialisation du profil n’est pas filtrée (confidentialité).

## Références
- `portal/apps/accounts/views.py` — Point d’entrée pour ajouter `ProfileView`, la logique de redirection et les messages utilisateur.
- `portal/apps/accounts/services.py` — Service Tryton existant à étendre pour récupérer et mettre à jour les `party`/`contact_mechanisms`.
- `portal/apps/accounts/password_validators.py` — Contraintes à respecter pour le changement de mot de passe.

## Critères d'acceptation
- Le lien « Profil » apparaît pour tout client connecté et la page affiche les données actuelles provenant de Tryton.
- Une modification valide se sauvegarde côté Tryton, affiche un message de succès et met à jour l’UI sans rechargements incohérents.
- Les tests automatisés couvrent au minimum un scénario heureux, un champ manquant et une erreur Tryton simulée (avec gestion utilisateur).

## Points de contact
- Responsable produit portail — Martin (PO Portail)
- Tech lead intégration Tryton — Codex (support technique)

## Questions ouvertes / suivi
- Confirmer si l’adresse postale doit être éditable par les clients ou uniquement visible (impact sur facturation).
- Documenter dans `docs/taches/04/04-implementation.md` les mappings de champs Tryton ↔ portail dès qu’ils seront figés.
