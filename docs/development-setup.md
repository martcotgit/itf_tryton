# Mise en route du portail client (dev)

## Prérequis
- Docker Desktop ou Docker Engine 24+
- Make (facultatif, simplifie les commandes)
- Accès au dépôt `tryton-itf`

## Initialisation
1. Copier `.env.example` vers `.env` dans `portal/` puis ajuster les secrets :
   ```bash
   cp portal/.env.example portal/.env
   ```
2. Lancer la stack locale (Traefik, Tryton, Django, Redis) :
   ```bash
   make portal-up
   ```
   - Tryton disponible sur http://tryton.localhost (via Traefik)
   - Portail Django disponible sur http://portal.localhost

3. Pour appliquer les migrations et créer un superuser :
   ```bash
   docker compose exec portal python manage.py migrate
   docker compose exec portal python manage.py createsuperuser
   ```

## Commandes utiles
- Arrêter les services :
  ```bash
  make portal-down
  ```
- Ouvrir un shell Django :
  ```bash
  make portal-shell
  ```
- Ouvrir un shell Tryton :
  ```bash
  make tryton-shell
  ```
- Rebuild complet :
  ```bash
  make build
  ```

## Notes
- Redis est utilisé comme cache partagé (configuration par défaut `redis://redis:6379/0`).
- Le service Django charge `itf_portal.settings.local` ; modifier `portal/.env` pour tester d’autres configurations.
- Par défaut, `PORTAL_ALLOW_ALL_HOSTS=1` autorise l'accès depuis n'importe quelle adresse IP sur le réseau local; mettez-le à `0` si vous devez restreindre les hôtes et ajustez ensuite `PORTAL_ALLOWED_HOSTS` et `CSRF_TRUSTED_ORIGINS` en conséquence.
