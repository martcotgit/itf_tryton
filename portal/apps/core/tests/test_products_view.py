from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from apps.core.services import PublicProduct, PublicProductServiceError
from apps.core.views import ProductsView


class ProductsViewTest(TestCase):
    def test_products_page_renders_catalog(self) -> None:
        sample = PublicProduct(
            template_id=42,
            name="Palette 48x40",
            code="PAL-001",
            description="Palette standard",
            categories=("Palettes neuves",),
            quantity_available=Decimal("10"),
        )
        with patch.object(ProductsView, "service_class") as service_cls:
            service_cls.return_value.list_available_products.return_value = [sample]
            response = self.client.get(reverse("core:products"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Palette 48x40")
        self.assertContains(response, "PAL-001")
        self.assertContains(response, "Palette standard")
        self.assertIn("products_schema", response.context)
        products_page = response.context["products"]
        self.assertEqual(list(products_page), [sample])
        self.assertEqual(response.context["products_total"], 1)

    def test_handles_service_failure(self) -> None:
        with patch.object(ProductsView, "service_class") as service_cls:
            service_cls.return_value.list_available_products.side_effect = PublicProductServiceError("boom")
            response = self.client.get(reverse("core:products"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Aucun produit n'est présentement disponible", html=False)
        self.assertEqual(list(response.context["products"]), [])
        self.assertEqual(response.context["products_total"], 0)

    def test_products_paginated_by_twelve(self) -> None:
        products = [
            PublicProduct(
                template_id=index,
                name=f"Palette {index}",
                code=f"PAL-{index:03d}",
                description="Palette standard",
                categories=("Palettes neuves",),
                quantity_available=Decimal("5"),
            )
            for index in range(1, 16)
        ]
        with patch.object(ProductsView, "service_class") as service_cls:
            service_cls.return_value.list_available_products.return_value = products
            response_page1 = self.client.get(reverse("core:products"))
            response_page2 = self.client.get(reverse("core:products"), {"page": 2})

        page1 = response_page1.context["products"]
        page2 = response_page2.context["products"]

        self.assertEqual(response_page1.status_code, 200)
        self.assertEqual(response_page2.status_code, 200)
        self.assertEqual(len(page1), 12)
        self.assertEqual(len(page2), 3)
        self.assertEqual(response_page1.context["products_total"], 15)
        self.assertEqual(response_page2.context["products_total"], 15)
        self.assertContains(response_page2, "Palette 13")
        self.assertContains(response_page2, "Page 2 sur 2")
