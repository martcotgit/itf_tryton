from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch, Mock

from django.test import TestCase
from django.urls import reverse

from apps.core.services import PublicProduct, PublicProductServiceError
from apps.core.views import ProductsView


class ProductsViewTest(TestCase):
    def test_products_page_renders_catalog(self) -> None:
        """Test that the products page renders a list of products for a specific category."""
        sample = PublicProduct(
            template_id=42,
            name="Palette 48x40",
            code="PAL-001",
            description="Palette standard",
            categories=("Palettes neuves",),
            quantity_available=Decimal("10"),
        )
        # Mock category for the view's context
        mock_category = Mock(category_id=1, name="Palettes neuves")
        
        with patch.object(ProductsView, "service_class") as service_cls:
            service_cls.return_value.list_available_products.return_value = [sample]
            service_cls.return_value.list_categories.return_value = [mock_category]
            
            response = self.client.get(reverse("core:products_by_category", kwargs={"category_id": 1}))
            
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Palette 48x40")
        self.assertContains(response, "PAL-001")
        self.assertContains(response, "Palette standard")
        self.assertIn("products_schema", response.context)
        products_page = response.context["products"]
        self.assertEqual(list(products_page), [sample])
        self.assertEqual(response.context["products_total"], 1)

    def test_handles_category_service_failure(self) -> None:
        """Test that the main products page handles service failure gracefully."""
        with patch.object(ProductsView, "service_class") as service_cls:
            service_cls.return_value.list_categories.side_effect = PublicProductServiceError("boom")
            response = self.client.get(reverse("core:products"))
            
        self.assertEqual(response.status_code, 200)
        # Should show empty state for categories
        self.assertContains(response, "Aucune catégorie disponible")
        self.assertEqual(list(response.context["categories"]), [])

    def test_handles_product_service_failure(self) -> None:
        """Test that the category detail page handles service failure gracefully."""
        with patch.object(ProductsView, "service_class") as service_cls:
            service_cls.return_value.list_available_products.side_effect = PublicProductServiceError("boom")
            # list_categories might also fail or be empty, handled in view
            service_cls.return_value.list_categories.return_value = []
            
            response = self.client.get(reverse("core:products_by_category", kwargs={"category_id": 1}))
            
        self.assertEqual(response.status_code, 200)
        # Should show empty state for products
        self.assertContains(response, "Aucun produit dans cette catégorie")
        self.assertEqual(list(response.context["products"]), [])
        self.assertEqual(response.context["products_total"], 0)

    def test_products_paginated_by_twelve(self) -> None:
        """Test that products are paginated correctly."""
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
        mock_category = Mock(category_id=1, name="Palettes neuves")
        
        with patch.object(ProductsView, "service_class") as service_cls:
            service_cls.return_value.list_available_products.return_value = products
            service_cls.return_value.list_categories.return_value = [mock_category]
            
            url = reverse("core:products_by_category", kwargs={"category_id": 1})
            response_page1 = self.client.get(url)
            response_page2 = self.client.get(url, {"page": 2})

        page1 = response_page1.context["products"]
        page2 = response_page2.context["products"]

        self.assertEqual(response_page1.status_code, 200)
        self.assertEqual(response_page2.status_code, 200)
        self.assertEqual(len(page1), 12)
        self.assertEqual(len(page2), 3)
        self.assertEqual(response_page1.context["products_total"], 15)
        self.assertEqual(response_page2.context["products_total"], 15)
        self.assertContains(response_page2, "Palette 13")
