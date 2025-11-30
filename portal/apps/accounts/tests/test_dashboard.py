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

    def count_invoices(self, *args, **kwargs):
        return 0


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


class DashboardSummaryTests(TestCase):
    def setUp(self):
        self.view = ClientDashboardView()
        self.view.request = type("Request", (), {"user": type("User", (), {"username": "test"})()})()
        self.view.invoice_service = NoopInvoiceService()
        self.view.order_service = NoopOrderService()

    def test_build_summary_counts_waiting_payment_invoices(self):
        def mock_count_invoices(login, statuses):
            if "draft" in statuses:
                return 1
            if "posted" in statuses:
                return 2
            if "validated" in statuses:
                return 3
            if "waiting_payment" in statuses:
                return 5
            return 0

        self.view.invoice_service.count_invoices = mock_count_invoices
        # Also mock order counts to avoid errors
        self.view.order_service.list_orders = lambda **kwargs: PortalOrderListResult(
            orders=[], pagination=PortalOrderPagination(1, 1, 1, 0, False, False)
        )

        summary = self.view._build_summary(invoices_result=None, login="test")

        # Check breakdown
        breakdown = {item["label"]: item["count"] for item in summary["invoices_breakdown"]}
        self.assertEqual(breakdown.get("Brouillon"), 1)
        self.assertEqual(breakdown.get("Comptabilisées"), 2)
        self.assertEqual(breakdown.get("Validées"), 3)
        self.assertEqual(breakdown.get("En attente"), 5)

        # Check total due count (1 + 2 + 3 + 5 = 11)
        self.assertEqual(summary["invoices_due_count"], 11)

    def test_build_summary_counts_draft_orders(self):
        def mock_list_orders(login, statuses=None, **kwargs):
            total = 0
            if statuses:
                if "draft" in statuses:
                    total += 1
                if "quotation" in statuses:
                    total += 2
                if "confirmed" in statuses:
                    total += 3
                if "processing" in statuses or "sent" in statuses:
                    total += 4
            
            return PortalOrderListResult(
                orders=[],
                pagination=PortalOrderPagination(1, 1, 1, total, False, False)
            )

        self.view.order_service.list_orders = mock_list_orders
        
        summary = self.view._build_summary(invoices_result=None, login="test")

        # Check breakdown
        breakdown = {item["label"]: item["count"] for item in summary["orders_breakdown"]}
        self.assertEqual(breakdown.get("Brouillon"), 1)
        self.assertEqual(breakdown.get("Soumission"), 2)
        self.assertEqual(breakdown.get("Confirmées"), 3)
        self.assertEqual(breakdown.get("En traitement"), 4)

        # Check total active count (1 + 2 + 3 + 4 = 10)
        self.assertEqual(summary["orders_active_count"], 10)
