from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Iterable, Optional

from django.apps import apps
from django.conf import settings
from django.core.cache import cache
from django.utils.html import strip_tags

from .tryton_client import TrytonClient, TrytonRPCError

logger = logging.getLogger(__name__)


class PublicProductServiceError(RuntimeError):
    """Raised when the Tryton catalog cannot be loaded for the public site."""


@dataclass(frozen=True)
class PublicProduct:
    template_id: int
    name: str
    code: Optional[str]
    description: Optional[str]
    quantity_available: Decimal
    image_url: Optional[str] = None
    categories: tuple[str, ...] = field(default_factory=tuple)

    @property
    def display_description(self) -> str:
        """Texte prêt à afficher avec repli convivial."""
        return self.description or "Dimensions standard"

    def as_schema(self, position: int, canonical_url: str) -> dict[str, Any]:
        """Return a JSON-LD friendly structure for SEO."""
        description = (self.description or "").strip()
        payload: dict[str, Any] = {
            "@type": "Product",
            "name": self.name,
            "sku": self.code or f"TPL-{self.template_id}",
            "description": description or "Palette industrielle disponible chez Ilnu Transforme.",
            "category": list(self.categories) or ["Palettes"],
            "url": canonical_url,
        }
        if self.quantity_available > 0:
            payload["offers"] = {
                "@type": "Offer",
                "availability": "https://schema.org/InStock",
                "inventoryLevel": {
                    "@type": "QuantitativeValue",
                    "value": str(self.quantity_available),
                    "unitCode": "EA",
                },
            }
        return {
            "@type": "ListItem",
            "position": position,
            "item": payload,
        }


class PublicProductService:
    """Expose Tryton pallet products for the public marketing site."""

    CATALOG_CACHE_KEY = "core.products.catalog.v2"
    CATALOG_TTL_SECONDS = 15 * 60

    def __init__(
        self,
        *,
        client: Optional[TrytonClient] = None,
        cache_timeout: Optional[int] = None,
    ) -> None:
        self.client = client or self._default_client()
        self.cache_timeout = cache_timeout if cache_timeout is not None else self.CATALOG_TTL_SECONDS
        self._company_id: Optional[int] = None
        language = getattr(settings, "LANGUAGE_CODE", "fr")
        self._base_context: dict[str, Any] = {"language": language}

    def list_available_products(self, *, use_cache: bool = True) -> list[PublicProduct]:
        """Return all salable Tryton templates that currently have a positive quantity."""
        if use_cache:
            cached = cache.get(self.CATALOG_CACHE_KEY)
            if cached is not None:
                return cached
        products = self._fetch_catalog()
        cache.set(self.CATALOG_CACHE_KEY, products, self.cache_timeout)
        return products

    def invalidate_cache(self) -> None:
        cache.delete(self.CATALOG_CACHE_KEY)

    def _fetch_catalog(self) -> list[PublicProduct]:
        context = self._rpc_context()
        variant_ids = self._search_variants(context)
        if not variant_ids:
            return []
        variant_records = self._read_variant_records(variant_ids, context)
        template_quantities = self._aggregate_template_quantities(variant_records)
        positive_template_ids = sorted(
            tid for tid, qty in template_quantities.items() if qty is not None and qty > 0
        )
        if not positive_template_ids:
            logger.warning(
                "Aucun stock positif détecté dans Tryton - retour à la liste des gabarits salables."
            )
            positive_template_ids = self._fallback_template_ids(context)
        if not positive_template_ids:
            return []
        templates = self._read_templates(positive_template_ids, context)
        positive_set = set(positive_template_ids)

        catalog: list[PublicProduct] = []
        for record in templates:
            template_id = self._extract_id(record.get("id"))
            if template_id is None or template_id not in positive_set:
                continue
            quantity = template_quantities.get(template_id, Decimal("0"))
            categories = self._extract_category_names(record.get("categories"))
            description = self._sanitize_description(record.get("description"))
            catalog.append(
                PublicProduct(
                    template_id=template_id,
                    name=str(record.get("name") or f"Produit #{template_id}"),
                    code=self._safe_str(record.get("code")),
                    description=description,
                    categories=tuple(categories),
                    quantity_available=quantity,
                )
            )
        return catalog

    def _search_variants(self, context: dict[str, Any]) -> list[int]:
        domain = [
            ("salable", "=", True),
            ("active", "=", True),
        ]
        try:
            variant_ids = self.client.call(
                "model.product.product",
                "search",
                [domain, 0, None, [("create_date", "DESC")], context],
            )
        except TrytonRPCError as exc:
            logger.exception("Impossible de lister les variantes produits Tryton pour le portail public.")
            raise PublicProductServiceError("Catalogue Tryton inaccessible. Réessayez plus tard.") from exc
        return self._normalize_ids(variant_ids)

    def _read_variant_records(self, variant_ids: Iterable[int], context: dict[str, Any]) -> list[dict[str, Any]]:
        ids_list = sorted({vid for vid in variant_ids if vid is not None})
        records: list[dict[str, Any]] = []
        for batch in self._chunked(ids_list, 40):
            try:
                result = self.client.call(
                    "model.product.product",
                    "read",
                    [batch, ["id", "template", "quantity"], context],
                ) or []
            except TrytonRPCError as exc:
                logger.exception("Impossible de lire les variantes produits %s.", batch)
                raise PublicProductServiceError("Lecture du stock Tryton impossible.") from exc
            records.extend(result)
        return records

    def _aggregate_template_quantities(self, records: list[dict[str, Any]]) -> dict[int, Decimal]:
        aggregates: dict[int, Decimal] = {}
        for record in records:
            template_id = self._extract_id(record.get("template"))
            if template_id is None:
                continue
            quantity = self._to_decimal(record.get("quantity")) or Decimal("0")
            aggregates[template_id] = aggregates.get(template_id, Decimal("0")) + quantity
        return aggregates

    def _read_templates(self, template_ids: Iterable[int], context: dict[str, Any]) -> list[dict[str, Any]]:
        ids_list = [tid for tid in template_ids if tid is not None]
        templates: list[dict[str, Any]] = []
        for template_id in ids_list:
            try:
                result = self.client.call(
                    "model.product.template",
                    "read",
                    [[template_id], ["name", "code", "categories"], context],
                ) or []
            except TrytonRPCError as exc:
                logger.warning("Gabarit produit %s illisible, il sera ignoré (erreur: %s)", template_id, exc)
                continue
            templates.extend(result)
        return templates

    def _fallback_template_ids(self, context: dict[str, Any]) -> list[int]:
        domain = [
            ("salable", "=", True),
            ("active", "=", True),
        ]
        try:
            template_ids = self.client.call(
                "model.product.template",
                "search",
                [domain, 0, 60, [("name", "ASC")], context],
            )
        except TrytonRPCError as exc:
            logger.exception("Impossible de récupérer les gabarits produits en mode secours.")
            return []
        return self._normalize_ids(template_ids)

    def _resolve_company_id(self) -> int:
        if self._company_id is not None:
            return self._company_id
        context = self._rpc_context(include_company=False)
        try:
            company_ids = self.client.call(
                "model.company.company",
                "search",
                [[], 0, 1, [("id", "ASC")], context],
            )
        except TrytonRPCError as exc:
            logger.exception("Impossible de déterminer l'entreprise par défaut pour le portail public.")
            raise PublicProductServiceError("Aucune entreprise Tryton disponible pour le portail.") from exc
        company_id = self._extract_id(company_ids[0] if company_ids else None)
        if company_id is None:
            raise PublicProductServiceError("Tryton n'a pas retourné d'entreprise valide.")
        self._company_id = company_id
        self._base_context.setdefault("company", company_id)
        return company_id

    def _rpc_context(self, *, include_company: bool = True) -> dict[str, Any]:
        context = dict(self._base_context)
        if include_company:
            company = self._base_context.get("company")
            if company is None:
                company = self._resolve_company_id()
            context["company"] = company
        return context

    @staticmethod
    def _normalize_ids(value: Any) -> list[int]:
        if value is None:
            return []
        if isinstance(value, int):
            return [value]
        if isinstance(value, (list, tuple)):
            normalized: list[int] = []
            for item in value:
                if isinstance(item, int):
                    normalized.append(item)
                elif isinstance(item, (list, tuple)) and item:
                    maybe_id = item[0]
                    if isinstance(maybe_id, int):
                        normalized.append(maybe_id)
                elif isinstance(item, dict) and "id" in item:
                    maybe_id = item.get("id")
                    if isinstance(maybe_id, int):
                        normalized.append(maybe_id)
            return normalized
        return []

    @staticmethod
    def _extract_id(value: Any) -> Optional[int]:
        if value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, (list, tuple)) and value:
            first = value[0]
            return int(first) if isinstance(first, int) else None
        if isinstance(value, dict):
            maybe_id = value.get("id") or value.get("value")
            if isinstance(maybe_id, int):
                return maybe_id
        return None

    @staticmethod
    def _safe_str(value: Any) -> Optional[str]:
        if value in (None, ""):
            return None
        return str(value)

    @staticmethod
    def _sanitize_description(value: Any) -> Optional[str]:
        if value in (None, ""):
            return None
        text = strip_tags(str(value))
        return text.strip() or None

    @staticmethod
    def _extract_category_names(value: Any) -> list[str]:
        names: list[str] = []
        if value is None:
            return names
        entries = value if isinstance(value, (list, tuple)) else []
        for entry in entries:
            if isinstance(entry, (list, tuple)):
                label = entry[1] if len(entry) > 1 else None
                if label:
                    names.append(str(label))
            elif isinstance(entry, dict) and entry.get("rec_name"):
                names.append(str(entry["rec_name"]))
            elif isinstance(entry, str):
                names.append(entry)
        return names

    @staticmethod
    def _to_decimal(value: Any) -> Optional[Decimal]:
        if value in (None, ""):
            return None
        if isinstance(value, Decimal):
            return value
        if isinstance(value, dict) and value.get("__class__") == "Decimal":
            raw = value.get("decimal")
            if raw is not None:
                return PublicProductService._to_decimal(raw)
        try:
            return Decimal(str(value))
        except (ArithmeticError, ValueError, TypeError):
            return None

    @staticmethod
    def _chunked(values: Iterable[int], size: int) -> Iterable[list[int]]:
        batch: list[int] = []
        for value in values:
            batch.append(value)
            if len(batch) >= size:
                yield batch
                batch = []
        if batch:
            yield batch

    @staticmethod
    def _default_client() -> TrytonClient:
        config = apps.get_app_config("core")
        factory = getattr(config, "get_tryton_client", None)
        if callable(factory):
            return factory()
        return TrytonClient()


def build_products_schema(products: list[PublicProduct], canonical_url: str) -> str:
    """Serialize the product catalog as JSON-LD for SEO."""
    items = [product.as_schema(index + 1, canonical_url) for index, product in enumerate(products[:20])]
    payload = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "Catalogue de palettes disponibles",
        "itemListElement": items,
    }
    return json.dumps(payload, ensure_ascii=False)
