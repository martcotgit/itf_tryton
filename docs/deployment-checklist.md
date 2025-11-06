# Checklist déploiement – Portail client

Ce runbook couvre les opérations à exécuter pour livrer la nouvelle zone client basée sur l’authentification Tryton.

## Préparation (local ou CI)
- [ ] Vérifier que la branche est à jour avec `origin/master` et que les tests passent :  
      `docker compose run --rm portal python manage.py test apps.accounts`
- [ ] (Optionnel) Lancer les tests Tryton si des modules ont été modifiés :  
      `docker compose run --rm tryton trytond-admin -c /etc/tryton/trytond.conf --all`
- [ ] Construire les images pour anticiper les erreurs de build :  
      `docker compose build portal tryton`
- [ ] Confirmer que le script `tryton/scripts/setup_portal_group.py` est versionné.

## Déploiement (serveur)
1. **Mettre à jour le code**
   - `git pull --ff-only`
   - `docker compose build portal tryton`

2. **Appliquer les migrations / mises à jour**
   - Portail Django : `docker compose run --rm portal python manage.py migrate`  
     (aucune migration attendue, commande à but de vérification)
   - Tryton : si des modules ont évolué, lancer `docker compose run --rm tryton trytond-admin -c /etc/tryton/trytond.conf --update=all`

3. **Mettre en place le compte portail**
   - Exécuter le script qui crée/actualise le groupe et l’utilisateur de test :  
     ```
     docker compose run --rm tryton \
       PORTAL_LOGIN=portal.client \
       PORTAL_PASSWORD='Motdepasse!123' \
       python3 /opt/trytond/scripts/setup_portal_group.py
     ```
   - Adapter `PORTAL_LOGIN`/`PORTAL_PASSWORD` si un autre compte est requis.

4. **Redémarrer les services**
   - `docker compose up -d --remove-orphans`

## Vérifications post-déploiement
- [ ] Accéder à `https://portal…/client/` et tester la connexion avec le compte `portal.client`.
- [ ] Tenter un accès direct à `/client/tableau-de-bord/` non authentifié → redirection vers la page de login.
- [ ] Tester le logout (`Se déconnecter`) et le retour au site public.
- [ ] Surveiller les logs (`docker compose logs -f portal`) pour s’assurer qu’aucune erreur `Tryton RPC` ou `422` n’apparaît.
- [ ] Confirmer que les autres utilisateurs Tryton n’ont pas vu leurs groupes modifiés (script remplace uniquement le groupe du login ciblé).

## Points d’attention
- Le script d’initialisation remplace les groupes du compte ciblé : utiliser un login dédié au portail.
- Les identifiants Tryton utilisés par le portail (`TRYTON_USER`/`TRYTON_PASSWORD`) doivent rester valides ; un changement côté Tryton nécessite une mise à jour des variables d’environnement.
- Prévoir une session de smoke-test avec un vrai client avant d’ouvrir la fonctionnalité en production (vérifier factures/commandes dès que les vues seront disponibles).
