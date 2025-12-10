"""
Service layer exports for Tryton integration.

Provides a lazy factory so callers can reuse the singleton managed by
the `CoreConfig` application configuration.
"""

from django.apps import apps

from .products import PublicCategory, PublicProduct, PublicProductService, PublicProductServiceError, build_products_schema
from .tryton_client import TrytonAuthError, TrytonClient, TrytonRPCError


def get_tryton_client() -> TrytonClient:
    """Return the shared Tryton client instance configured for the portal."""
    config = apps.get_app_config("core")
    if hasattr(config, "get_tryton_client"):
        return config.get_tryton_client()
    # Fallback in unlikely case CoreConfig does not expose helper.
    return TrytonClient()


__all__ = [
    "PublicCategory",
    "PublicProduct",
    "PublicProductService",
    "PublicProductServiceError",
    "TrytonAuthError",
    "TrytonClient",
    "TrytonRPCError",
    "build_products_schema",
    "get_tryton_client",
]
