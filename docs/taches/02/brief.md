Tryton Client Service

  - Structure: créer portal/apps/core/services/tryton_client.py + init (portal/apps/core/services/__init__.py). Ce module vivra dans l’app core pour réutilisation
    transverse (auth, commandes, factures).
  - Dependencies: utiliser requests ou httpx (choisir selon politique – httpx offre async et retry facile). Redis déjà dispo via django-redis. Prévoir import
    django.core.cache (cache).
  - Config: lire dans settings :
      - TRYTON_RPC_URL
      - TRYTON_USER et TRYTON_PASSWORD (à ajouter dans .env / settings)
      - Optionnel: TRYTON_SESSION_TTL (durée cache)
      - Timeout (ex: 10s) et retry.
  - Classe principale: TrytonClient. Responsabilités (SRP/SOLID):
      - gérer la session JSON-RPC (auth → login, conserver session_id)
      - envoyer les requêtes RPC (call(method, params))
      - gérer un cache Redis pour certains appels (ex: ping, métadonnées) via décorateur ou méthode cached_call.
  - Composants:
      - TrytonAuthError, TrytonRPCError exceptions custom.
      - _authenticate() interne qui appelle common.db.login.
      - _request(payload) : enveloppe JSON-RPC ({"jsonrpc": "2.0", "method": ..., "params": ..., "id": uuid})
      - call(service, method, params) combinant service+method (Tryton convention: model.method), avec re-login si session expirée.
      - ping() (health).
      - cache_key(method, params) util.
  - Redis: utiliser cache.get / cache.set (Cache default: redis via settings). Offrir API cached_call(method, params, ttl=60).
  - Thread safety: stocker session info par instance. Si besoin d’injection, proposer singleton via django.apps.registry.apps.get_app_config("core").tryton_client.
  - Test hooks: injection session_id initial, support TESTING=True pour bypass.
  - Logging: logger = logging.getLogger(__name__) pour erreurs/timeouts. Masquer credentials.
  - Usage prévu:
      - client = TrytonClient() (prob via helper get_client()).
      - client.call("model", "execute", {...}) etc.
      - client.cached_call("model.method", params, ttl=300).
  - Next work: une fois ce module créé, on écrira un test de fumée (pytest) qui instancie le client et appelle ping() en utilisant la stack docker.