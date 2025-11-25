from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.accounts.services import (
    PortalInvoiceSummary,
    PortalInvoiceListResult,
    PortalInvoicePagination,
    PortalOrderSummary,
    PortalOrderListResult,
    PortalOrderPagination,
)
from apps.accounts.views import ClientDashboardView


class NoopInvoiceService:
    def __init__(self, *args, **kwargs):
        pass

    def list_invoices(self, *args, **kwargs):
        pagination = PortalInvoicePagination(page=1, pages=1, page_size=5, total=0, has_next=False, has_previous=False)
        return PortalInvoiceListResult(invoices=[], pagination=pagination)


class NoopOrderService:
    def __init__(self, *args, **kwargs):
        pass

    def list_orders(self, *args, **kwargs):
        page_size = kwargs.get("page_size", 1)
        pagination = PortalOrderPagination(page=1, pages=1, page_size=page_size, total=0, has_next=False, has_previous=False)
        return PortalOrderListResult(orders=[], pagination=pagination)


class DashboardGreetingTests(TestCase):
    def setUp(self):
        self.url = reverse("accounts:dashboard")
        self.UserModel = get_user_model()

    @patch.object(ClientDashboardView, "order_service_class", NoopOrderService)
    @patch.object(ClientDashboardView, "invoice_service_class", NoopInvoiceService)
    def test_greeting_fallbacks_to_email_when_first_name_is_placeholder(self, *_):
        user = self.UserModel.objects.create_user(
            username="client@example.com",
            email="client@example.com",
            first_name="{{ request.user.first_name }}",
        )
        self.client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")

        response = self.client.get(self.url)

        self.assertContains(response, "Re-bienvenue, client@example.com")
        self.assertNotContains(response, "{{ request.user.first_name }}")

    @patch.object(ClientDashboardView, "order_service_class", NoopOrderService)
    @patch.object(ClientDashboardView, "invoice_service_class", NoopInvoiceService)
    def test_greeting_uses_first_name_when_available(self, *_):
        user = self.UserModel.objects.create_user(
            username="client@example.com",
            email="client@example.com",
            first_name="Chantal",
        )
        self.client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")

        response = self.client.get(self.url)

        self.assertContains(response, "Re-bienvenue, Chantal")

    def test_status_label_placeholder_falls_back_to_inconnu(self):
        view = ClientDashboardView()
        invoice = PortalInvoiceSummary(
            id=1,
            number="INV-1",
            issue_date=None,
            due_date=None,
            state="{{ item.status_label }}",
            state_label="{{ item.status_label }}",
            total_amount=None,
            amount_due=None,
            currency_label=None,
        )
        order = PortalOrderSummary(
            id=2,
            number="SO-1",
            reference=None,
            state="{{ item.status_label }}",
            state_label="{{ item.status_label }}",
            shipping_date=None,
            total_amount=None,
            currency_id=None,
            currency_label=None,
            create_date=None,
        )

        items = view._build_activity_feed(invoices=[invoice], orders=[order])

        self.assertTrue(all(item["status_label"] == "Inconnu" for item in items))

    def test_status_label_uses_state_mapping_when_label_missing(self):
        view = ClientDashboardView()
        invoice = PortalInvoiceSummary(
            id=1,
            number="INV-2",
            issue_date=None,
            due_date=None,
            state="waiting_payment",
            state_label="",
            total_amount=None,
            amount_due=None,
            currency_label=None,
        )
        order = PortalOrderSummary(
            id=2,
            number="SO-2",
            reference=None,
            state="draft",
            state_label=None,
            shipping_date=None,
            total_amount=None,
            currency_id=None,
            currency_label=None,
            create_date=None,
        )

        items = view._build_activity_feed(invoices=[invoice], orders=[order])

        self.assertEqual(items[0]["status_label"], "En attente")
        self.assertEqual(items[1]["status_label"], "Brouillon")

    def test_status_label_html_placeholder_is_ignored(self):
        view = ClientDashboardView()
        invoice = PortalInvoiceSummary(
            id=3,
            number="INV-3",
            issue_date=None,
            due_date=None,
            state="waiting_payment",
            state_label="&#123;&#123; item.status_label &#125;&#125;",
            total_amount=None,
            amount_due=None,
            currency_label=None,
        )
        order = PortalOrderSummary(
            id=4,
            number="SO-3",
            reference=None,
            state="confirmed",
            state_label="&#123;&#123; item.status_label &#125;&#125;",
            shipping_date=None,
            total_amount=None,
            currency_id=None,
            currency_label=None,
            create_date=None,
        )

        items = view._build_activity_feed(invoices=[invoice], orders=[order])

        self.assertEqual(items[0]["status_label"], "En attente")
        self.assertEqual(items[1]["status_label"], "Confirmée")
