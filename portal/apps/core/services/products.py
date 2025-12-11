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
class PublicCategory:
    """Represents a product category with its cover image."""
    category_id: int
    name: str
    product_count: int
    image_data_uri: Optional[str] = None

    @property
    def slug(self) -> str:
        """Generate a URL-friendly slug from the category name."""
        import re
        slug = self.name.lower()
        slug = re.sub(r'[àâä]', 'a', slug)
        slug = re.sub(r'[éèêë]', 'e', slug)
        slug = re.sub(r'[îï]', 'i', slug)
        slug = re.sub(r'[ôö]', 'o', slug)
        slug = re.sub(r'[ùûü]', 'u', slug)
        slug = re.sub(r'[^a-z0-9]+', '-', slug)
        return slug.strip('-')


@dataclass(frozen=True)
class PublicProduct:
    template_id: int
    name: str
    code: Optional[str]
    description: Optional[str]
    quantity_available: Decimal
    image_url: Optional[str] = None
    categories: tuple[str, ...] = field(default_factory=tuple)
    category_ids: tuple[int, ...] = field(default_factory=tuple)

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

    def list_available_products(self, *, category_id: Optional[int] = None, use_cache: bool = True) -> list[PublicProduct]:
        """Return all salable Tryton templates that currently have a positive quantity.
        
        Args:
            category_id: If provided, filter products by this category ID
            use_cache: Whether to use cached results
        """
        cache_key = self.CATALOG_CACHE_KEY
        if category_id is not None:
            cache_key = f"{self.CATALOG_CACHE_KEY}.category.{category_id}"
        
        if use_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        
        products = self._fetch_catalog(category_id=category_id)
        cache.set(cache_key, products, self.cache_timeout)
        return products

    def list_categories(self, *, use_cache: bool = True) -> list[PublicCategory]:
        """Return all product categories that contain salable products with their cover images.
        
        Categories are fetched from Tryton and enriched with:
        - Product count
        - Cover image (from ir.attachment with name 'web_cover')
        """
        cache_key = "core.products.categories.v1"
        if use_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        
        categories = self._fetch_categories()
        cache.set(cache_key, categories, self.cache_timeout)
        return categories

    def invalidate_cache(self) -> None:
        """Invalidate all product and category caches."""
        cache.delete(self.CATALOG_CACHE_KEY)
        cache.delete("core.products.categories.v1")
        # Also clear category-specific caches
        cache.delete_pattern("core.products.catalog.v2.category.*")


    def _fetch_catalog(self, *, category_id: Optional[int] = None) -> list[PublicProduct]:
        """Fetch product catalog from Tryton, optionally filtered by category.
        
        Args:
            category_id: If provided, only return products in this category
        """
        context = self._rpc_context()
        variant_ids = self._search_variants(context)
        if not variant_ids:
            return []
        variant_records = self._read_variant_records(variant_ids, context)
        template_quantities = self._aggregate_template_quantities(variant_records)
        # On inclut tous les produits trouvés, même ceux avec stock 0 (affichés "Sur commande")
        positive_template_ids = sorted(
            tid for tid in template_quantities.keys()
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

        # Batch fetch images for all relevant templates
        images_map = self._fetch_product_images(positive_template_ids, context)

        catalog: list[PublicProduct] = []
        for record in templates:
            template_id = self._extract_id(record.get("id"))
            if template_id is None or template_id not in positive_set:
                continue
            
            # Extract category IDs for filtering
            category_ids_list = self._extract_category_ids(record.get("categories"))
            
            # Skip if filtering by category and this product doesn't match
            if category_id is not None and category_id not in category_ids_list:
                continue
            
            quantity = template_quantities.get(template_id, Decimal("0"))
            categories = self._extract_category_names(record.get("categories"))
            description = self._sanitize_description(record.get("description"))
            
            # Get image URL if available
            image_url = images_map.get(template_id)

            catalog.append(
                PublicProduct(
                    template_id=template_id,
                    name=str(record.get("name") or f"Produit #{template_id}"),
                    code=self._safe_str(record.get("code")),
                    description=description,
                    categories=tuple(categories),
                    category_ids=tuple(category_ids_list),
                    quantity_available=quantity,
                    image_url=image_url,
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
        
        # We fetch in batches for performance
        # We removed 'description' because it's not a standard field in Tryton product.template
        # and caused 500 errors.
        fields = ["name", "code", "categories"]
        
        for batch in self._chunked(ids_list, 40):
            try:
                result = self.client.call(
                    "model.product.template",
                    "read",
                    [batch, fields, context],
                ) or []
            except TrytonRPCError as exc:
                logger.warning("Impossible de lire les gabarits produits %s: %s", batch, exc)
                continue
            templates.extend(result)
        return templates

    def _fetch_product_images(self, template_ids: list[int], context: dict[str, Any]) -> dict[int, str]:
        """Fetch cover images for the given product templates."""
        if not template_ids:
            return {}

        resources = [f"product.template,{tid}" for tid in template_ids]
        
        # Search for all attachments linked to these templates
        # We prioritize 'web_image' but accept others as fallback
        domain = [("resource", "in", resources)]
        try:
            attachment_ids = self.client.call(
                "model.ir.attachment",
                "search",
                [domain, 0, None, [("name", "ASC")], context],  # sort by name to put web_image potentially first or predictable
            )
        except TrytonRPCError:
            logger.warning("Failed to search product images")
            return {}

        if not attachment_ids:
            return {}

        try:
            attachments = self.client.call(
                "model.ir.attachment",
                "read",
                [attachment_ids, ["resource", "data", "type", "name"], context],
            )
        except TrytonRPCError:
            logger.warning("Failed to read product images content")
            return {}

        import base64
        images: dict[int, str] = {}
        
        # Process attachments. 
        # Since we sorted by name ASC, strict 'web_image' matching logic:
        # 1. Fill map with any image found.
        # 2. If we find 'web_image', overwrite whatever is there (it takes precedence).
        
        for att in attachments:
            resource = att.get("resource")
            if not resource or "," not in resource:
                continue
            
            try:
                model, tid_str = resource.split(",")
                template_id = int(tid_str)
            except (ValueError, IndexError):
                continue
                
            data = att.get("data")
            if not data:
                continue
                
            # Construct Data URI
            file_type = att.get("type", "image/jpeg")
            if isinstance(data, bytes):
                data_b64 = base64.b64encode(data).decode("ascii")
            else:
                data_b64 = data
            
            data_uri = f"data:{file_type};base64,{data_b64}"
            
            # Logic: If we already have an image, only overwrite if current one IS 'web_image'
            # or if the current one is NOT 'web_image' and new one IS.
            
            is_web_image = att.get("name") == "web_image"
            
            if template_id not in images:
                images[template_id] = data_uri
            elif is_web_image:
                images[template_id] = data_uri

        return images

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
    def _extract_category_ids(value: Any) -> list[int]:
        """Extract category IDs from Tryton category field."""
        ids: list[int] = []
        if value is None:
            return ids
        entries = value if isinstance(value, (list, tuple)) else []
        for entry in entries:
            if isinstance(entry, (list, tuple)) and len(entry) > 0:
                cat_id = entry[0] if isinstance(entry[0], int) else None
                if cat_id:
                    ids.append(cat_id)
            elif isinstance(entry, dict) and entry.get("id"):
                cat_id = entry.get("id")
                if isinstance(cat_id, int):
                    ids.append(cat_id)
            elif isinstance(entry, int):
                ids.append(entry)
        return ids

    def _fetch_categories(self) -> list[PublicCategory]:
        """Fetch all product categories that contain salable products.
        
        Returns categories with:
        - Product count
        - Cover image (base64 data URI from ir.attachment)
        """
        context = self._rpc_context()
        
        # Get all products to count by category
        all_products = self._fetch_catalog()
        
        # Count products per category ID
        category_counts: dict[int, int] = {}
        for product in all_products:
            for cat_id in product.category_ids:
                category_counts[cat_id] = category_counts.get(cat_id, 0) + 1
        
        # Fetch all categories from Tryton
        try:
            category_ids = self.client.call(
                "model.product.category",
                "search",
                [[], 0, None, [("name", "ASC")], context],
            )
        except TrytonRPCError as exc:
            logger.exception("Failed to fetch product categories from Tryton")
            return []
        
        if not category_ids:
            return []
        
        # Read category details
        try:
            category_records = self.client.call(
                "model.product.category",
                "read",
                [category_ids, ["id", "name"], context],
            )
        except TrytonRPCError as exc:
            logger.exception("Failed to read category details")
            return []
        
        # Build final category list
        categories: list[PublicCategory] = []
        for record in category_records:
            cat_id = self._extract_id(record.get("id"))
            cat_name = record.get("name", "")
            
            if not cat_id or not cat_name:
                continue
            
            # Get count by ID
            count = category_counts.get(cat_id, 0)
            
            # Skip categories with no products
            if count == 0:
                continue
            
            # Fetch cover image
            image_data_uri = self._fetch_category_image(cat_id, context)
            
            categories.append(
                PublicCategory(
                    category_id=cat_id,
                    name=cat_name,
                    product_count=count,
                    image_data_uri=image_data_uri,
                )
            )
        
        return categories

    def _fetch_category_image(self, category_id: int, context: dict[str, Any]) -> Optional[str]:
        """Fetch category cover image from ir.attachment.
        
        Looks for an attachment with:
        - resource = 'product.category,{category_id}'
        - name = 'web_cover'
        
        Returns a base64 data URI or None.
        """
        resource_name = f"product.category,{category_id}"
        
        try:
            # Search for the attachment
            attachment_ids = self.client.call(
                "model.ir.attachment",
                "search",
                [
                    [
                        ("resource", "=", resource_name),
                        ("name", "=", "web_cover"),
                    ],
                    0,
                    1,
                    [],
                    context,
                ],
            )
        except TrytonRPCError as exc:
            logger.warning("Failed to search for category %s cover image: %s", category_id, exc)
            return None
        
        if not attachment_ids:
            return None
        
        attachment_id = self._extract_id(attachment_ids[0]) if attachment_ids else None
        if not attachment_id:
            return None
        
        try:
            # Read the attachment data
            attachments = self.client.call(
                "model.ir.attachment",
                "read",
                [[attachment_id], ["data", "type"], context],
            )
        except TrytonRPCError as exc:
            logger.warning("Failed to read attachment %s: %s", attachment_id, exc)
            return None
        
        if not attachments:
            return None
        
        attachment = attachments[0]
        data = attachment.get("data")
        file_type = attachment.get("type", "image/jpeg")
        
        if not data:
            return None
        
        # Data is already base64 encoded by Tryton
        # Create a data URI
        import base64
        if isinstance(data, bytes):
            data_b64 = base64.b64encode(data).decode("ascii")
        else:
            data_b64 = data
        
        return f"data:{file_type};base64,{data_b64}"

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
