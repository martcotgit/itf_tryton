from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.core.services import PublicProductService, PublicProductServiceError, TrytonRPCError


class PublicProductServiceTest(SimpleTestCase):
    def setUp(self) -> None:
        self.client = MagicMock()
        self.service = PublicProductService(client=self.client, cache_timeout=1)

    def test_list_available_products_filters_zero_quantity(self) -> None:
        with patch.object(PublicProductService, "_resolve_company_id", return_value=1):
            self._mock_template_calls()
            products = self.service.list_available_products(use_cache=False)
        self.assertEqual(len(products), 1)
        product = products[0]
        self.assertEqual(product.name, "Palette 48x40")
        self.assertEqual(product.code, "PAL-001")
        self.assertEqual(product.quantity_available, Decimal("12"))
        self.assertTupleEqual(product.categories, ("Palettes neuves",))

    def test_error_when_tryton_fails(self) -> None:
        with patch.object(PublicProductService, "_resolve_company_id", return_value=1):
            self.client.call.side_effect = TrytonRPCError("boom")
            with self.assertRaises(PublicProductServiceError):
                self.service.list_available_products(use_cache=False)

    def _mock_template_calls(self) -> None:
        def _call(service, method, params=None, **_kwargs):
            if service == "model.product.template":
                if method == "search":
                    return [11, 22]
                if method == "read":
                    return [
                        {
                            "id": 11,
                            "name": "Palette 48x40",
                            "code": "PAL-001",
                            "description": "Palette robuste pour centres de distribution",
                            "products": [101],
                            "categories": [(7, "Palettes neuves")],
                        },
                        {
                            "id": 22,
                            "name": "Palette CHEP",
                            "code": "PAL-002",
                            "description": "Retour consigné",
                            "products": [202],
                            "categories": [(8, "Consignation")],
                        },
                    ]
            if service == "model.product.product":
                return [
                    {"id": 101, "template": (11, "Palette 48x40"), "quantity": "12"},
                    {"id": 202, "template": (22, "Palette CHEP"), "quantity": "0"},
                ]
            if service == "model.company.company" and method == "search":
                return [5]
            return []

        self.client.call.side_effect = _call
