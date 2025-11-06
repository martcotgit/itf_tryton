from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "Portail - Noyau"

    _tryton_client = None

    def get_tryton_client(self):
        """
        Lazily instantiate and cache the Tryton client.

        Keeping the factory on the app config allows reuse across the codebase
        without resorting to module-level singletons, which eases testing.
        """
        if self._tryton_client is None:
            from .services.tryton_client import TrytonClient

            self._tryton_client = TrytonClient()
        return self._tryton_client

    def set_tryton_client(self, client):
        """Test helper to inject a preconfigured Tryton client."""
        self._tryton_client = client
