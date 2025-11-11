from __future__ import annotations

from unittest.mock import MagicMock, call, patch

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from django.core.exceptions import ValidationError

from apps.accounts.forms import ClientSignupForm
from apps.accounts.password_validators import ComplexitePortailValidator
from apps.accounts.services import (
    PortalAccountCreationResult,
    PortalAccountService,
    PortalAccountServiceError,
)
from apps.accounts.views import ClientSignupView
from apps.core.services import TrytonRPCError


class PortalAccountServiceTests(TestCase):
    def setUp(self):
        self.tryton_client = MagicMock()

    def test_login_exists_normalizes_login_and_queries_tryton(self):
        self.tryton_client.call.return_value = [5]
        service = PortalAccountService(client=self.tryton_client)
        service._user_has_party_field = True
        service._user_has_party_field = True
        service._user_has_party_field = True

        exists = service.login_exists("CLIENT@Example.com ")

        self.assertTrue(exists)
        self.tryton_client.call.assert_called_once_with(
            "model.res.user",
            "search",
            [[("login", "=", "client@example.com")], 0, 1, None, {}],
        )

    def test_login_exists_returns_false_on_rpc_failure(self):
        self.tryton_client.call.side_effect = TrytonRPCError("boom")
        service = PortalAccountService(client=self.tryton_client)

        exists = service.login_exists("client@example.com")

        self.assertFalse(exists)

    def test_create_client_account_creates_party_and_user(self):
        self.tryton_client.call.side_effect = [
            [],  # login_exists
            [3],  # _get_portal_group_id
            [11],  # _create_party
            [22],  # _create_user
        ]
        service = PortalAccountService(client=self.tryton_client)
        service._user_has_party_field = True

        result = service.create_client_account(
            company_name="ITF",
            first_name="Jean",
            last_name="Dupont",
            email="Client@example.com ",
            phone="0102030405",
            password="Motdepasse!123",
        )

        self.assertEqual(result.login, "client@example.com")
        self.assertEqual(result.party_id, 11)
        self.assertEqual(result.user_id, 22)
        expected_calls = [
            call("model.res.user", "search", [[("login", "=", "client@example.com")], 0, 1, None, {}]),
            call("model.res.group", "search", [[("name", "=", "Portail Clients")], 0, 1, None, {}]),
            call(
                "model.party.party",
                "create",
                [
                    [
                        {
                            "name": "ITF",
                            "contact_mechanisms": [
                                (
                                    "create",
                                    [
                                        {"type": "email", "value": "client@example.com"},
                                        {"type": "phone", "value": "0102030405"},
                                    ],
                                )
                            ],
                        }
                    ],
                    {},
                ],
            ),
            call(
                "model.res.user",
                "create",
                [
                    [
                        {
                            "name": "Jean Dupont",
                            "login": "client@example.com",
                            "password": "Motdepasse!123",
                            "email": "client@example.com",
                            "active": True,
                            "party": 11,
                            "groups": [("add", [3])],
                        }
                    ],
                    {},
                ],
            ),
        ]
        self.assertEqual(self.tryton_client.call.mock_calls, expected_calls)

    def test_get_portal_group_auto_creates_when_missing(self):
        self.tryton_client.call.side_effect = [
            [],  # search
            [5],  # create
        ]
        service = PortalAccountService(client=self.tryton_client, portal_group_name="Portail Clients")
        service._user_has_party_field = True
        service._user_has_party_field = True

        group_id = service._get_portal_group_id()

        self.assertEqual(group_id, 5)
        self.assertEqual(
            self.tryton_client.call.mock_calls,
            [
                call("model.res.group", "search", [[("name", "=", "Portail Clients")], 0, 1, None, {}]),
                call("model.res.group", "create", [[{"name": "Portail Clients"}], {}]),
            ],
        )

    def test_get_portal_group_raises_when_create_fails(self):
        self.tryton_client.call.side_effect = [
            [],  # search
            TrytonRPCError("boom"),  # create
        ]
        service = PortalAccountService(client=self.tryton_client, portal_group_name="Portail Clients")

        with self.assertRaises(PortalAccountServiceError):
            service._get_portal_group_id()

    def test_create_client_account_rolls_back_party_on_user_failure(self):
        self.tryton_client.call.side_effect = [
            [],  # login_exists
            [7],  # group search
            [15],  # party create
            TrytonRPCError("cannot create user"),  # user create
            None,  # rollback delete
        ]
        service = PortalAccountService(client=self.tryton_client)
        service._user_has_party_field = True

        with self.assertRaises(PortalAccountServiceError):
            service.create_client_account(
                company_name="ITF",
                first_name="Alice",
                last_name="Martin",
                email="alice@example.com",
                phone=None,
                password="Motdepasse!123",
            )

        self.assertEqual(
            self.tryton_client.call.mock_calls[-1],
            call("model.party.party", "delete", [[15], {}]),
        )

    def test_create_client_account_skips_party_field_when_missing(self):
        self.tryton_client.call.side_effect = [
            [],  # login_exists
            [3],  # portal group id
            [11],  # party create
            [22],  # user create
        ]
        service = PortalAccountService(client=self.tryton_client)
        service._user_has_party_field = False

        result = service.create_client_account(
            company_name="ITF",
            first_name="Jean",
            last_name="Dupont",
            email="client@example.com",
            phone=None,
            password="Motdepasse!123",
        )

        self.assertEqual(result.party_id, 11)
        self.assertIn(
            call(
                "model.res.user",
                "create",
                [
                    [
                        {
                            "name": "Jean Dupont",
                            "login": "client@example.com",
                            "password": "Motdepasse!123",
                            "email": "client@example.com",
                            "active": True,
                            "groups": [("add", [3])],
                        }
                    ],
                    {},
                ],
            ),
            self.tryton_client.call.mock_calls,
        )

    def test_extract_tryton_error_message_parses_html(self):
        service = PortalAccountService(client=self.tryton_client)
        exc = TrytonRPCError("boom")

        class DummyResponse:
            def __init__(self, text):
                self.text = text

        class DummyCause(Exception):
            def __init__(self, text):
                self.response = DummyResponse(text)

        exc.__cause__ = DummyCause("<html><body><p>Detailed message</p></body></html>")  # type: ignore[attr-defined]

        message = service._extract_tryton_error_message(exc, "fallback")

        self.assertEqual(message, "Detailed message")


class ComplexitePortailValidatorTests(TestCase):
    def setUp(self):
        self.validator = ComplexitePortailValidator(required_categories=3)

    def test_accepts_password_with_three_categories(self):
        try:
            self.validator("Motdepasse!123")
        except ValidationError as exc:
            self.fail(f"Le validateur ne devrait pas lever d'erreur: {exc}")

    def test_rejects_password_with_too_few_categories(self):
        with self.assertRaises(ValidationError):
            self.validator("motdepasse1")


class DummyService:
    def __init__(self, exists: bool = False):
        self.exists = exists
        self.created_payload = None

    def login_exists(self, login: str) -> bool:
        return self.exists

    def create_client_account(
        self,
        *,
        company_name,
        first_name,
        last_name,
        email,
        phone,
        password,
    ) -> PortalAccountCreationResult:
        self.created_payload = {
            "company_name": company_name,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone,
            "password": password,
        }
        return PortalAccountCreationResult(login=email, user_id=9, party_id=4)


class ClientSignupFormTests(TestCase):
    def test_duplicate_email_triggers_validation_error(self):
        form = ClientSignupForm(
            data={
                "company_name": "ITF",
                "first_name": "Laura",
                "last_name": "Martin",
                "email": "client@example.com",
                "phone": "",
                "password1": "Motdepasse!123",
                "password2": "Motdepasse!123",
                "accept_terms": "on",
            },
            account_service=DummyService(exists=True),
        )

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_password_without_enough_categories_triggers_error(self):
        form = ClientSignupForm(
            data={
                "company_name": "ITF",
                "first_name": "Laura",
                "last_name": "Martin",
                "email": "client@example.com",
                "phone": "",
                "password1": "motdepasse1",
                "password2": "motdepasse1",
                "accept_terms": "on",
            },
            account_service=DummyService(exists=False),
        )

        self.assertFalse(form.is_valid())
        self.assertIn("password1", form.errors)
        self.assertIn("catégories", form.errors["password1"][0])

    def test_save_delegates_to_service_with_cleaned_values(self):
        service = DummyService()
        form = ClientSignupForm(
            data={
                "company_name": "  ITF  ",
                "first_name": "  Marie ",
                "last_name": " Curie ",
                "email": "CLIENT@EXAMPLE.COM",
                "phone": " 0123456789 ",
                "password1": "Motdepasse!123",
                "password2": "Motdepasse!123",
                "accept_terms": "on",
            },
            account_service=service,
        )

        self.assertTrue(form.is_valid())
        result = form.save()

        self.assertEqual(result.login, "CLIENT@EXAMPLE.COM".lower())
        self.assertEqual(
            service.created_payload,
            {
                "company_name": "ITF",
                "first_name": "Marie",
                "last_name": "Curie",
                "email": "client@example.com",
                "phone": "0123456789",
                "password": "Motdepasse!123",
            },
        )


class ClientSignupViewTests(TestCase):
    def setUp(self):
        self.signup_url = reverse("accounts:signup")
        self.dashboard_url = reverse("accounts:dashboard")
        self.login_url = reverse("accounts:login")
        self.original_service_class = ClientSignupView.service_class
        self.addCleanup(self._restore_service_class)

    def _restore_service_class(self):
        ClientSignupView.service_class = self.original_service_class

    def _valid_payload(self) -> dict[str, str]:
        return {
            "company_name": "ITF",
            "first_name": "Nina",
            "last_name": "Durand",
            "email": "client@example.com",
            "phone": "",
            "password1": "Motdepasse!123",
            "password2": "Motdepasse!123",
            "accept_terms": "on",
        }

    def test_successful_signup_authenticates_user_and_sets_session(self):
        class FakeService:
            instances = []

            def __init__(self):
                type(self).instances.append(self)
                self.created_payload = None

            def login_exists(self, login: str) -> bool:
                return False

            def create_client_account(
                self,
                *,
                company_name,
                first_name,
                last_name,
                email,
                phone,
                password,
            ):
                self.created_payload = {
                    "company_name": company_name,
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "phone": phone,
                    "password": password,
                }
                return PortalAccountCreationResult(login=email, user_id=7, party_id=3)

        ClientSignupView.service_class = FakeService
        FakeService.instances = []

        fake_user = get_user_model()(username="client@example.com")
        fake_user.backend = "apps.accounts.auth_backend.TrytonBackend"
        fake_user._tryton_session = {"session": "abc123"}

        with patch("apps.accounts.views.authenticate", return_value=fake_user) as mock_auth, patch(
            "apps.accounts.views.auth_login"
        ) as mock_login:
            response = self.client.post(self.signup_url, data=self._valid_payload(), follow=False)

        self.assertRedirects(response, self.dashboard_url, fetch_redirect_response=False)
        self.assertEqual(len(FakeService.instances), 1)
        self.assertEqual(
            FakeService.instances[0].created_payload,
            {
                "company_name": "ITF",
                "first_name": "Nina",
                "last_name": "Durand",
                "email": "client@example.com",
                "phone": "",
                "password": "Motdepasse!123",
            },
        )
        mock_auth.assert_called_once()
        self.assertEqual(mock_auth.call_args.kwargs["username"], "client@example.com")
        self.assertEqual(mock_auth.call_args.kwargs["password"], "Motdepasse!123")
        mock_login.assert_called_once()
        self.assertEqual(self.client.session.get("tryton_session"), {"session": "abc123"})

    def test_signup_falls_back_to_login_when_authentication_fails(self):
        class FakeService:
            def __init__(self):
                pass

            def login_exists(self, login: str) -> bool:
                return False

            def create_client_account(
                self,
                *,
                company_name,
                first_name,
                last_name,
                email,
                phone,
                password,
            ):
                return PortalAccountCreationResult(login=email, user_id=4, party_id=2)

        ClientSignupView.service_class = FakeService

        with patch("apps.accounts.views.authenticate", return_value=None) as mock_auth, patch(
            "apps.accounts.views.auth_login"
        ) as mock_login:
            response = self.client.post(self.signup_url, data=self._valid_payload(), follow=False)

        self.assertRedirects(response, self.login_url)
        mock_auth.assert_called_once()
        mock_login.assert_not_called()
        messages_list = list(get_messages(response.wsgi_request))
        self.assertTrue(messages_list)
        self.assertEqual(messages_list[0].level, messages.SUCCESS)

    def test_service_error_returns_form_with_non_field_error(self):
        class ErrorService:
            def login_exists(self, login: str) -> bool:
                return False

            def create_client_account(
                self,
                *,
                company_name,
                first_name,
                last_name,
                email,
                phone,
                password,
            ):
                raise PortalAccountServiceError("Tryton indisponible")

        ClientSignupView.service_class = ErrorService

        with patch("apps.accounts.views.authenticate") as mock_auth:
            response = self.client.post(self.signup_url, data=self._valid_payload(), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/signup.html")
        self.assertFormError(response, "form", None, "Tryton indisponible")
        mock_auth.assert_not_called()
