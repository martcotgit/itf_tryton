from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.accounts.services import PortalOrderDetail, PortalOrderLineDetail
from apps.accounts.views import OrderDetailView

class OrderDetailViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password"
        )
        self.client.force_login(self.user)
        self.url = reverse("accounts:orders-detail", kwargs={"order_id": 123})

    @patch("apps.accounts.views.OrderDetailView.service_class")
    def test_order_detail_view_renders_correctly(self, MockServiceClass):
        # Setup the mock service
        mock_service = MockServiceClass.return_value
        
        # Create a dummy order detail object
        order_detail = PortalOrderDetail(
            id=123,
            number="CMD-001",
            reference="REF-CLIENT-123",
            state="confirmed",
            state_label="Confirmée",
            shipping_date=date(2025, 12, 31),
            total_amount=Decimal("120.00"),
            untaxed_amount=Decimal("100.00"),
            currency_label="CAD",
            create_date=date(2025, 11, 29),
            lines=[
                PortalOrderLineDetail(
                    product="Product A",
                    quantity=Decimal("10"),
                    unit="pcs",
                    description="Description A",
                    unit_price=Decimal("10.00"),
                    total=Decimal("100.00")
                )
            ]
        )
        
        mock_service.get_order_detail.return_value = order_detail

        # perform request
        response = self.client.get(self.url)

        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/order_detail.html")
        
        # Check content
        self.assertContains(response, "CMD-001")
        self.assertContains(response, "REF-CLIENT-123")
        self.assertContains(response, "Confirmée")
        self.assertContains(response, "120,00")
        self.assertContains(response, "CAD")
        
        # Check if the lines are rendered
        self.assertContains(response, "Description A")
