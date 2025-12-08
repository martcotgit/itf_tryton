from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.accounts.forms import OrderDraftForm, OrderLineFormSet, ORDER_LINES_FORMSET_PREFIX
from apps.accounts.services import (
    PortalClientAddress,
    PortalClientProfile,
    PortalOrderAddress,
    PortalOrderListResult,
    PortalOrderPagination,
    PortalOrderLineInput,
    PortalOrderSummary,
    PortalOrderProduct,
    PortalOrderService,
    PortalOrderServiceError,
    PortalOrderSubmissionResult,
)


class OrderDraftFormTests(SimpleTestCase):
    def test_shipping_address_is_cast_to_int_and_notes_trimmed(self):
        form = OrderDraftForm(
            data={
                "client_reference": " PO-100 ",
                "shipping_date": "2025-11-20",
                "shipping_address": "42",
                "notes": "  Livraison arrière ",
            },
            address_choices=[(42, "Entrepôt principal")],
        )

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["shipping_address"], 42)
        self.assertEqual(form.cleaned_data["notes"], "Livraison arrière")
        self.assertEqual(form.cleaned_data["client_reference"], "PO-100")

    def test_line_formset_requires_at_least_one_filled_line(self):
        data = {
            f"{ORDER_LINES_FORMSET_PREFIX}-TOTAL_FORMS": "1",
            f"{ORDER_LINES_FORMSET_PREFIX}-INITIAL_FORMS": "0",
            f"{ORDER_LINES_FORMSET_PREFIX}-MIN_NUM_FORMS": "0",
            f"{ORDER_LINES_FORMSET_PREFIX}-MAX_NUM_FORMS": "10",
        }
        data[f"{ORDER_LINES_FORMSET_PREFIX}-0-product"] = ""
        data[f"{ORDER_LINES_FORMSET_PREFIX}-0-quantity"] = ""
        data[f"{ORDER_LINES_FORMSET_PREFIX}-0-notes"] = ""
        formset = OrderLineFormSet(
            data=data,
            prefix=ORDER_LINES_FORMSET_PREFIX,
            form_kwargs={"product_choices": [(1, "Produit test")]},
        )

        self.assertFalse(formset.is_valid())
        self.assertIn("Ajoutez au moins une ligne", " ".join(formset.non_form_errors()))

    def test_line_formset_skips_deleted_entries(self):
        data = {
            f"{ORDER_LINES_FORMSET_PREFIX}-TOTAL_FORMS": "2",
            f"{ORDER_LINES_FORMSET_PREFIX}-INITIAL_FORMS": "0",
            f"{ORDER_LINES_FORMSET_PREFIX}-MIN_NUM_FORMS": "0",
            f"{ORDER_LINES_FORMSET_PREFIX}-MAX_NUM_FORMS": "10",
            f"{ORDER_LINES_FORMSET_PREFIX}-0-product": "101",
            f"{ORDER_LINES_FORMSET_PREFIX}-0-quantity": "2",
            f"{ORDER_LINES_FORMSET_PREFIX}-0-notes": "",
            f"{ORDER_LINES_FORMSET_PREFIX}-1-product": "",
            f"{ORDER_LINES_FORMSET_PREFIX}-1-quantity": "",
            f"{ORDER_LINES_FORMSET_PREFIX}-1-notes": "",
            f"{ORDER_LINES_FORMSET_PREFIX}-1-DELETE": "on",
        }

        formset = OrderLineFormSet(
            data=data,
            prefix=ORDER_LINES_FORMSET_PREFIX,
            form_kwargs={"product_choices": [(101, "Palette 48x40")]},
        )

        self.assertTrue(formset.is_valid())


class PortalOrderServiceTests(SimpleTestCase):
    def setUp(self):
        self.tryton_client = MagicMock()
        self.account_service = MagicMock()
        self.service = PortalOrderService(client=self.tryton_client, account_service=self.account_service)
        self.profile = PortalClientProfile(
            user_id=1,
            party_id=77,
            login="client@example.com",
            email="client@example.com",
            first_name="Client",
            last_name="Démo",
            company_name="ITF",
            phone=None,
            address=PortalClientAddress(),
        )
        self.account_service.fetch_client_profile.return_value = self.profile
        self.account_service._get_address_postal_field = MagicMock(return_value="postal_code")
        self.service._company_id = 42
        self.service._company_currency_id = 5
        self.service._resolve_company_id = MagicMock(return_value=42)
        self.service._resolve_currency_id = MagicMock(return_value=5)

    def test_list_orderable_products_returns_catalog(self):
        self.tryton_client.call.side_effect = [
            [11, 22],
            [
                {
                    "id": 11,
                    "name": "Palette standard",
                    "code": "PAL-STD",
                    "default_uom": [5, "palette"],
                    "list_price": "10.00",
                    "template": [101, "Palette standard"],
                },
                {
                    "id": 22,
                    "name": "Bois recyclé",
                    "code": None,
                    "default_uom": [6, "lb"],
                    "list_price": "12.50",
                    "template": [102, "Bois recyclé"],
                },
            ],
        ]

        products = self.service.list_orderable_products(force_refresh=True)

        self.assertEqual(len(products), 2)
        self.assertEqual(products[0].choice_label, "Palette standard (PAL-STD) — palette")
        self.assertEqual(products[1].choice_label, "Bois recyclé — lb")
        self.assertEqual(products[0].unit_price, Decimal("10.00"))

    def test_list_orderable_products_falls_back_to_template_price(self):
        self.tryton_client.call.side_effect = [
            [11],
            [
                {
                    "id": 11,
                    "name": "Palette standard",
                    "code": "PAL-STD",
                    "default_uom": [5, "palette"],
                    "list_price": None,
                    "template": [101, "Palette standard"],
                }
            ],
            [
                {
                    "id": 101,
                    "list_price": "19.99",
                }
            ],
        ]

        products = self.service.list_orderable_products(force_refresh=True)

        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].unit_price, Decimal("19.99"))

    def test_create_draft_order_builds_payload_and_returns_result(self):
        self.service._fetch_party_addresses = MagicMock(
            return_value=[PortalOrderAddress(id=12, label="Entrepôt principal")]
        )
        product = PortalOrderProduct(
            id=101,
            name="Palette 48x40",
            code="PAL-4840",
            unit_id=5,
            unit_name="palette",
            unit_price=Decimal("25.00"),
        )
        self.service._read_products = MagicMock(return_value={101: product})
        self.service._read_order_number = MagicMock(return_value="SO0009")
        self.tryton_client.call.return_value = [310]

        result = self.service.create_draft_order(
            login="client@example.com",
            client_reference="PO-005",
            shipping_date=date(2025, 11, 15),
            shipping_address_id=12,
            lines=[PortalOrderLineInput(product_id=101, quantity=Decimal("5.00"), notes="Urgent")],
            instructions="Livraison avant midi",
        )

        called_args = self.tryton_client.call.call_args
        self.assertIsNotNone(called_args)
        payload = called_args.args[2][0][0]
        self.assertEqual(payload["party"], 77)
        self.assertEqual(payload["shipment_address"], 12)
        self.assertEqual(payload["reference"], "PO-005")
        self.assertEqual(payload["comment"], "Livraison avant midi")
        self.assertEqual(payload["shipping_date"], "2025-11-15")
        self.assertEqual(payload["company"], 42)
        self.assertEqual(payload["currency"], 5)
        self.assertEqual(payload["lines"][0][0], "create")
        self.assertEqual(payload["lines"][0][1][0]["product"], 101)
        self.assertEqual(payload["lines"][0][1][0]["unit"], 5)
        self.assertEqual(payload["lines"][0][1][0]["unit_price"], 25.0)
        self.assertEqual(result.order_id, 310)
        self.assertEqual(result.number, "SO0009")
        self.assertEqual(result.portal_reference, "PO-005")

    def test_list_shipment_addresses_uses_stable_order(self):
        self.tryton_client.call.side_effect = [
            [12],
            [
                {
                    "id": 12,
                    "rec_name": "Entrepôt principal",
                    "street": "1269 rang 6",
                    "city": "Saint-Prime",
                    "postal_code": "G8K 2C3",
                }
            ],
        ]

        party_id, addresses = self.service.list_shipment_addresses(login="client@example.com")

        self.assertEqual(party_id, 77)
        self.assertEqual(len(addresses), 1)
        self.assertEqual(addresses[0].id, 12)
        search_call = self.tryton_client.call.call_args_list[0]
        args = search_call.args
        self.assertEqual(args[0], "model.party.address")
        self.assertEqual(args[2][3], [("id", "ASC")])
        read_call = self.tryton_client.call.call_args_list[1]
        address_fields = read_call.args[2][1]
        self.assertIn("rec_name", address_fields)
        self.assertIn("postal_code", address_fields)

    def test_get_order_detail_handles_single_line_id(self):
        self.tryton_client.call.side_effect = [
            [
                {
                    "id": 5,
                    "number": "SO001",
                    "reference": "PO-1",
                    "state": "done",
                    "shipping_date": "2025-11-25",
                    "total_amount": "125.00",
                    "untaxed_amount": "100.00",
                    "currency": [5, "CAD"],
                    "create_date": "2025-11-20",
                    "party": self.profile.party_id,
                    "lines": 501,
                }
            ],
            [
                {
                    "id": 501,
                    "description": "Palette",
                    "quantity": "5",
                    "unit": [6, "palette"],
                    "unit_price": "20.00",
                    "amount": "100.00",
                }
            ],
        ]

        detail = self.service.get_order_detail(login="client@example.com", order_id=5)

        self.assertEqual(detail.id, 5)
        self.assertEqual(detail.state_label, "Terminée")
        self.assertEqual(len(detail.lines), 1)
        self.assertEqual(detail.lines[0].unit, "palette")
        self.assertEqual(detail.lines[0].quantity, Decimal("5"))

    def test_list_orders_returns_paginated_results(self):
        self.tryton_client.call.side_effect = [
            2,  # search_count
            [310, 311],  # search with pagination
            [
                {
                    "id": 310,
                    "number": "SO0001",
                    "reference": "PO-88",
                    "state": "processing",
                    "shipping_date": "2025-11-25",
                    "total_amount": {"__class__": "Decimal", "decimal": "100.00"},
                    "currency": [5, "CAD"],
                    "create_date": "2025-11-10",
                },
                {
                    "id": 311,
                    "number": "SO0002",
                    "reference": "PO-90",
                    "state": "done",
                    "shipping_date": None,
                    "total_amount": "150.50",
                    "currency": [5, "CAD"],
                    "create_date": "2025-11-11",
                },
            ],
        ]

        result = self.service.list_orders(
            login="client@example.com",
            statuses=["processing"],
            period_days=90,
            search="SO",
            page=1,
            page_size=20,
        )

        self.assertEqual(result.pagination.total, 2)
        self.assertEqual(result.pagination.page_size, 20)
        self.assertEqual(len(result.orders), 2)
        self.assertEqual(result.orders[0].state_label, "En traitement")
        self.assertEqual(result.orders[0].total_amount, Decimal("100.00"))
        self.assertEqual(result.orders[0].currency_label, "CAD")
        call_args = self.tryton_client.call.call_args_list[1]
        domain = call_args.args[2][0]
        self.assertIn(("state", "in", ["processing"]), domain)
        self.assertIn(("party", "=", 77), domain)
        self.assertTrue(any(isinstance(item, list) and item[0] == "OR" for item in domain))


class OrderCreateViewTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.user = self.user_model.objects.create_user(username="client@example.com", password="demo")
        self.client.force_login(self.user)
        self.url = reverse("accounts:orders-new")
        self.dashboard_url = reverse("core:home")

    @patch("apps.accounts.views.OrderCreateView.service_class")
    def test_get_renders_form_with_products_and_addresses(self, service_cls):
        service = service_cls.return_value
        service.list_orderable_products.return_value = [
            PortalOrderProduct(id=101, name="Palette 48x40", code="PAL-4840", unit_id=5, unit_name="palette")
        ]
        service.list_shipment_addresses.return_value = (
            77,
            [PortalOrderAddress(id=12, label="Entrepôt principal")],
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/orders_form.html")
        self.assertIn("form", response.context)
        self.assertIn("line_formset", response.context)
        service.list_orderable_products.assert_called_once()
        service.list_shipment_addresses.assert_called_once()

    @patch("apps.accounts.views.OrderCreateView.service_class")
    def test_post_valid_data_creates_order_and_redirects(self, service_cls):
        service = service_cls.return_value
        service.list_orderable_products.return_value = [
            PortalOrderProduct(id=101, name="Palette 48x40", code="PAL-4840", unit_id=5, unit_name="palette")
        ]
        service.list_shipment_addresses.return_value = (
            77,
            [PortalOrderAddress(id=12, label="Entrepôt principal")],
        )
        service.create_draft_order.return_value = PortalOrderSubmissionResult(
            order_id=501,
            number="SO0001",
            portal_reference="PO-88",
        )

        data = {
            "client_reference": "PO-88",
            "shipping_date": "2025-11-20",
            "shipping_address": "12",
            "notes": "Livraison arrière",
            f"{ORDER_LINES_FORMSET_PREFIX}-TOTAL_FORMS": "1",
            f"{ORDER_LINES_FORMSET_PREFIX}-INITIAL_FORMS": "0",
            f"{ORDER_LINES_FORMSET_PREFIX}-MIN_NUM_FORMS": "0",
            f"{ORDER_LINES_FORMSET_PREFIX}-MAX_NUM_FORMS": "10",
            f"{ORDER_LINES_FORMSET_PREFIX}-0-product": "101",
            f"{ORDER_LINES_FORMSET_PREFIX}-0-quantity": "3",
            f"{ORDER_LINES_FORMSET_PREFIX}-0-notes": "Palette rouge",
        }

        response = self.client.post(self.url, data=data)

        self.assertRedirects(response, self.dashboard_url, fetch_redirect_response=False)
        service.create_draft_order.assert_called_once()
        kwargs = service.create_draft_order.call_args.kwargs
        self.assertEqual(kwargs["client_reference"], "PO-88")
        self.assertEqual(kwargs["shipping_address_id"], 12)
        self.assertEqual(kwargs["shipping_date"].isoformat(), "2025-11-20")
        self.assertEqual(len(kwargs["lines"]), 1)
        self.assertIsInstance(kwargs["lines"][0], PortalOrderLineInput)
        self.assertEqual(kwargs["lines"][0].product_id, 101)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Votre commande a été transmise" in msg.message for msg in messages))

    @patch("apps.accounts.views.OrderCreateView.service_class")
    def test_post_ignores_deleted_lines(self, service_cls):
        service = service_cls.return_value
        service.list_orderable_products.return_value = [
            PortalOrderProduct(id=101, name="Palette 48x40", code="PAL-4840", unit_id=5, unit_name="palette")
        ]
        service.list_shipment_addresses.return_value = (
            77,
            [PortalOrderAddress(id=12, label="Entrepôt principal")],
        )
        service.create_draft_order.return_value = PortalOrderSubmissionResult(
            order_id=502,
            number="SO0002",
            portal_reference="PO-90",
        )

        data = {
            "client_reference": "PO-90",
            "shipping_date": "2025-11-22",
            "shipping_address": "12",
            f"{ORDER_LINES_FORMSET_PREFIX}-TOTAL_FORMS": "2",
            f"{ORDER_LINES_FORMSET_PREFIX}-INITIAL_FORMS": "0",
            f"{ORDER_LINES_FORMSET_PREFIX}-MIN_NUM_FORMS": "0",
            f"{ORDER_LINES_FORMSET_PREFIX}-MAX_NUM_FORMS": "10",
            f"{ORDER_LINES_FORMSET_PREFIX}-0-product": "101",
            f"{ORDER_LINES_FORMSET_PREFIX}-0-quantity": "4",
            f"{ORDER_LINES_FORMSET_PREFIX}-0-notes": "",
            f"{ORDER_LINES_FORMSET_PREFIX}-1-product": "101",
            f"{ORDER_LINES_FORMSET_PREFIX}-1-quantity": "2",
            f"{ORDER_LINES_FORMSET_PREFIX}-1-notes": "Supprimer",
            f"{ORDER_LINES_FORMSET_PREFIX}-1-DELETE": "on",
        }

        response = self.client.post(self.url, data=data)

        self.assertRedirects(response, self.dashboard_url, fetch_redirect_response=False)
        kwargs = service.create_draft_order.call_args.kwargs
        self.assertEqual(len(kwargs["lines"]), 1)
        self.assertEqual(kwargs["lines"][0].quantity, Decimal("4"))


class OrderListViewTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.user = self.user_model.objects.create_user(username="client@example.com", password="demo")
        self.client.force_login(self.user)
        self.url = reverse("accounts:orders-list")

    @patch("apps.accounts.views.OrderListView.service_class")
    def test_get_renders_orders_with_filters(self, service_cls):
        pagination = PortalOrderPagination(page=1, pages=1, page_size=20, total=1, has_next=False, has_previous=False)
        summary = PortalOrderSummary(
            id=310,
            number="SO0001",
            reference="PO-88",
            state="processing",
            state_label="En traitement",
            shipping_date=date(2025, 11, 25),
            total_amount=Decimal("100.00"),
            currency_id=5,
            currency_label="CAD",
            create_date=date(2025, 11, 10),
        )
        service = service_cls.return_value
        service.list_orders.return_value = PortalOrderListResult(orders=[summary], pagination=pagination)

        response = self.client.get(
            self.url,
            {"statut": ["processing"], "periode": "30", "recherche": "SO"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/orders_list.html")
        service.list_orders.assert_called_once()
        kwargs = service.list_orders.call_args.kwargs
        self.assertEqual(kwargs["statuses"], ["processing"])
        self.assertEqual(kwargs["period_days"], 30)
        self.assertEqual(kwargs["search"], "SO")
        self.assertEqual(kwargs["page"], 1)
        self.assertEqual(kwargs["page_size"], PortalOrderService.DEFAULT_PAGE_SIZE)
        self.assertIn("orders", response.context)
        self.assertIn("pagination", response.context)

    @patch("apps.accounts.views.OrderListView.service_class")
    def test_get_handles_service_error(self, service_cls):
        service = service_cls.return_value
        service.list_orders.side_effect = PortalOrderServiceError("Erreur Tryton")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Erreur Tryton" in msg.message for msg in messages))


class OrderCatalogViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="catalog@example.com", password="demo")
        self.client.force_login(self.user)
        self.url = reverse("accounts:orders-catalog")

    @patch("apps.accounts.views.OrderCatalogView.service_class")
    def test_returns_paginated_results(self, service_cls):
        service = service_cls.return_value
        service.list_orderable_products.return_value = [
            PortalOrderProduct(id=101, name="Palette A", code="PAL-A", unit_id=5, unit_name="palette"),
            PortalOrderProduct(id=202, name="Planche B", code="PL-B", unit_id=7, unit_name="pied"),
            PortalOrderProduct(id=303, name="Granule C", code="GR-C", unit_id=None, unit_name=None),
        ]

        response = self.client.get(self.url, {"page": "2", "page_size": "1"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["pagination"]["page"], 2)
        self.assertEqual(payload["pagination"]["total"], 3)
        self.assertEqual(len(payload["results"]), 1)
        self.assertEqual(payload["results"][0]["id"], 202)
        self.assertIn("filters", payload)
        service.list_orderable_products.assert_called_once()

    @patch("apps.accounts.views.OrderCatalogView.service_class")
    def test_filters_by_query_and_unit(self, service_cls):
        service = service_cls.return_value
        service.list_orderable_products.return_value = [
            PortalOrderProduct(id=101, name="Palette standard", code="PAL-STD", unit_id=5, unit_name="palette"),
            PortalOrderProduct(id=202, name="Palette bleue", code="PAL-BLUE", unit_id=5, unit_name="palette"),
            PortalOrderProduct(id=303, name="Bois recyclé", code="WOOD", unit_id=7, unit_name="lb"),
        ]

        response = self.client.get(self.url, {"q": "palette", "unit": "5"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["pagination"]["total"], 2)
        self.assertTrue(all("Palette" in item["name"] for item in payload["results"]))

    @patch("apps.accounts.views.OrderCatalogView.service_class")
    def test_returns_error_when_service_fails(self, service_cls):
        service = service_cls.return_value
        service.list_orderable_products.side_effect = PortalOrderServiceError("Erreur Tryton")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 503)
        payload = response.json()
        self.assertIn("error", payload)
