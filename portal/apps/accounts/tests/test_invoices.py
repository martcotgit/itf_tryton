from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.accounts.services import (
    PortalClientAddress,
    PortalClientProfile,
    PortalInvoiceListResult,
    PortalInvoicePagination,
    PortalInvoiceService,
    PortalInvoiceServiceError,
    PortalInvoiceSummary,
)


class PortalInvoiceServiceTests(SimpleTestCase):
    def setUp(self):
        self.tryton_client = MagicMock()
        self.account_service = MagicMock()
        self.service = PortalInvoiceService(client=self.tryton_client, account_service=self.account_service)
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

    def test_list_invoices_returns_paginated_results(self):
        self.tryton_client.call.side_effect = [
            2,
            [11, 22],
            [
                {
                    "id": 11,
                    "number": "INV-001",
                    "invoice_date": "2025-11-01",
                    "payment_term_date": "2025-11-30",
                    "state": "posted",
                    "total_amount": "100.00",
                    "amount_to_pay": "25.00",
                    "currency": [5, "CAD"],
                },
                {
                    "id": 22,
                    "number": "INV-002",
                    "invoice_date": "2025-10-01",
                    "payment_term_date": None,
                    "state": "paid",
                    "total_amount": "50.00",
                    "amount_to_pay": None,
                    "currency": [5, "CAD"],
                },
            ],
        ]

        result = self.service.list_invoices(login="client@example.com", page=1, page_size=20)

        self.assertEqual(len(result.invoices), 2)
        self.assertEqual(result.pagination.total, 2)
        self.assertEqual(result.invoices[0].amount_due, Decimal("25.00"))
        self.assertEqual(result.invoices[1].amount_due, Decimal("50.00"))
        call_args = self.tryton_client.call.call_args_list[0]
        domain_payload = call_args.args[2][0]
        self.assertIn(("party", "=", 77), domain_payload)
        self.assertIn(("type", "=", "out"), domain_payload)

    def test_list_invoices_returns_empty_result_when_none(self):
        self.tryton_client.call.side_effect = [0]

        result = self.service.list_invoices(login="client@example.com", page=3, page_size=20)

        self.assertEqual(result.pagination.total, 0)
        self.assertEqual(result.pagination.page, 1)
        self.assertEqual(result.invoices, [])
        self.assertEqual(self.tryton_client.call.call_count, 1)


class InvoiceListViewTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.user = self.user_model.objects.create_user(username="client@example.com", password="demo")
        self.client.force_login(self.user)
        self.url = reverse("accounts:invoices-list")

    @patch("apps.accounts.views.InvoiceListView.service_class")
    def test_get_renders_invoices(self, service_cls):
        pagination = PortalInvoicePagination(
            page=1,
            pages=2,
            page_size=20,
            total=25,
            has_next=True,
            has_previous=False,
        )
        summary = PortalInvoiceSummary(
            id=11,
            number="INV-001",
            issue_date=date(2025, 11, 1),
            due_date=date(2025, 11, 30),
            state="posted",
            state_label="Comptabilisée",
            total_amount=Decimal("100.00"),
            amount_due=Decimal("25.00"),
            currency_label="CAD",
        )
        service = service_cls.return_value
        service.list_invoices.return_value = PortalInvoiceListResult(invoices=[summary], pagination=pagination)

        response = self.client.get(self.url, {"page": "2"})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/invoices_list.html")
        service.list_invoices.assert_called_once()
        kwargs = service.list_invoices.call_args.kwargs
        self.assertEqual(kwargs["page"], 2)
        self.assertEqual(kwargs["page_size"], PortalInvoiceService.DEFAULT_PAGE_SIZE)
        self.assertIn("invoices", response.context)
        self.assertIn("pagination", response.context)
        self.assertIn("summary", response.context)
        self.assertEqual(response.context["summary"]["count"], 1)
        self.assertEqual(response.context["summary"]["due_total"], Decimal("25.00"))

    @patch("apps.accounts.views.InvoiceListView.service_class")
    def test_get_handles_service_error(self, service_cls):
        service = service_cls.return_value
        service.list_invoices.side_effect = PortalInvoiceServiceError("Erreur Tryton")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Erreur Tryton" in msg.message for msg in messages))
