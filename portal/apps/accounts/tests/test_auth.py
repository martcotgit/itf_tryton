from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.core.services import TrytonAuthError


class ClientAuthTests(TestCase):
    def setUp(self):
        self.login_url = reverse("accounts:login")
        self.dashboard_url = reverse("accounts:dashboard")
        self.UserModel = get_user_model()

    def test_login_page_renders_with_form(self):
        response = self.client.get(self.login_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/login.html")
        self.assertIn("form", response.context)

    @patch("apps.accounts.auth_backend.TrytonClient")
    def test_login_success_redirects_to_dashboard(self, mock_client_cls):
        mock_client = mock_client_cls.return_value
        mock_client.login.return_value = (42, "session-token")
        mock_client.get_session_context.return_value = {
            "user_id": 42,
            "session": "session-token",
            "username": "client@example.com",
            "database": "tryton",
            "auth_header": "Session token",
            "base_url": "http://tryton:8000/",
        }
        mock_client.call.return_value = [{"name": "Client Demo", "email": "client@example.com"}]

        response = self.client.post(
            self.login_url,
            data={"username": "client@example.com", "password": "Motdepasse!123"},
        )

        self.assertRedirects(response, self.dashboard_url)
        user = self.UserModel.objects.get(username="client@example.com")
        self.assertEqual(user.email, "client@example.com")
        session_payload = self.client.session.get("tryton_session")
        self.assertIsNotNone(session_payload)
        self.assertEqual(session_payload["session"], "session-token")
        mock_client.close.assert_called_once()

    @patch("apps.accounts.auth_backend.TrytonClient")
    def test_login_failure_shows_errors(self, mock_client_cls):
        mock_client = mock_client_cls.return_value
        mock_client.login.side_effect = TrytonAuthError("invalid credentials")

        response = self.client.post(
            self.login_url,
            data={"username": "client@example.com", "password": "bad-password"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertFalse(self.UserModel.objects.filter(username="client@example.com").exists())

    def test_dashboard_requires_authentication(self):
        response = self.client.get(self.dashboard_url)

        self.assertRedirects(
            response,
            f"{self.login_url}?next={self.dashboard_url}",
            fetch_redirect_response=False,
        )

    def test_authenticated_user_skips_login(self):
        user = self.UserModel.objects.create_user(username="client@example.com")
        self.client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")

        response = self.client.get(self.login_url)

        self.assertRedirects(response, self.dashboard_url)
