from __future__ import annotations

from unittest.mock import MagicMock, patch, call

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.accounts.services import (
    PortalAccountService,
    PortalAccountServiceError,
    PortalClientAddress,
    PortalClientProfile,
)
from apps.accounts.views import ClientProfileView
from apps.core.services import TrytonRPCError


class PortalAccountServiceProfileTests(TestCase):
    def setUp(self):
        self.tryton_client = MagicMock()
        self.service = PortalAccountService(client=self.tryton_client)
        self.service._user_has_party_field = True
        self.service._address_postal_field = "zip"

    def test_fetch_client_profile_returns_dataclass_snapshot(self):
        self.tryton_client.call.side_effect = [
            [42],  # res.user search
            [
                {
                    "id": 42,
                    "name": "Alice Tremblay",
                    "email": "client@example.com",
                    "party": 77,
                }
            ],  # res.user read
            [
                {
                    "id": 77,
                    "name": "ITF",
                }
            ],  # party read
            [91],  # contact search
            [
                {
                    "value": "4185551234",
                }
            ],  # contact read
            [18],  # address search
            [
                {
                    "street": "123 rue Principale",
                    "city": "Mashteuiatsh",
                    "zip": "G0W 2H0",
                }
            ],  # address read
        ]

        profile = self.service.fetch_client_profile(login="client@example.com")

        self.assertIsInstance(profile, PortalClientProfile)
        self.assertEqual(profile.first_name, "Alice")
        self.assertEqual(profile.last_name, "Tremblay")
        self.assertEqual(profile.company_name, "ITF")
        self.assertEqual(profile.phone, "4185551234")
        self.assertEqual(profile.address.street, "123 rue Principale")
        self.assertEqual(profile.address.city, "Mashteuiatsh")
        self.assertEqual(profile.address.postal_code, "G0W 2H0")

    def test_update_client_profile_updates_user_party_phone_and_address(self):
        self.tryton_client.call.side_effect = [
            [42],  # res.user search
            [
                {
                    "id": 42,
                    "name": "Alice Tremblay",
                    "email": "client@example.com",
                    "party": 77,
                }
            ],  # res.user read
            None,  # res.user write
            None,  # party write
            [91],  # contact search
            None,  # contact write
            [18],  # address search
            None,  # address write
        ]
        refreshed = PortalClientProfile(
            user_id=42,
            party_id=77,
            login="client@example.com",
            email="client@example.com",
            first_name="Alice",
            last_name="Tremblay",
            company_name="ITF",
            phone="4185551234",
            address=PortalClientAddress(
                street="123 rue Principale",
                city="Mashteuiatsh",
                postal_code="G0W 2H0",
            ),
        )
        with patch.object(self.service, "fetch_client_profile", return_value=refreshed):
            profile = self.service.update_client_profile(
                login="client@example.com",
                company_name="ITF",
                first_name="Alice",
                last_name="Tremblay",
                phone="4185551234",
                address="123 rue Principale",
                city="Mashteuiatsh",
                postal_code="G0W 2H0",
            )

        self.assertEqual(profile, refreshed)
        self.assertGreaterEqual(self.tryton_client.call.call_count, 8)

    def test_update_client_profile_removes_phone_when_empty(self):
        self.tryton_client.call.side_effect = [
            [42],  # res.user search
            [
                {
                    "id": 42,
                    "name": "Alice Tremblay",
                    "email": "client@example.com",
                    "party": 77,
                }
            ],  # res.user read
            None,  # res.user write
            None,  # party write
            [91],  # contact search
            None,  # contact delete
            [],  # address search
            [18],  # address create
        ]
        refreshed = PortalClientProfile(
            user_id=42,
            party_id=77,
            login="client@example.com",
            email="client@example.com",
            first_name="Alice",
            last_name="Tremblay",
            company_name="ITF",
            phone=None,
            address=PortalClientAddress(
                street="123 rue Principale",
                city="Mashteuiatsh",
                postal_code="G0W 2H0",
            ),
        )
        with patch.object(self.service, "fetch_client_profile", return_value=refreshed):
            profile = self.service.update_client_profile(
                login="client@example.com",
                company_name="ITF",
                first_name="Alice",
                last_name="Tremblay",
                phone="",
                address="123 rue Principale",
                city="Mashteuiatsh",
                postal_code="G0W 2H0",
            )

        self.assertEqual(profile, refreshed)
        self.assertIn(
            call(
                "model.party.contact_mechanism",
                "delete",
                [[91], {}],
            ),
            self.tryton_client.call.mock_calls,
        )

    def test_update_client_profile_creates_phone_when_missing(self):
        self.tryton_client.call.side_effect = [
            [42],  # res.user search
            [
                {
                    "id": 42,
                    "name": "Alice Tremblay",
                    "email": "client@example.com",
                    "party": 77,
                }
            ],  # res.user read
            None,  # res.user write
            None,  # party write
            [],  # contact search
            None,  # party write with contact_mechanisms create
            [],  # address search
            [18],  # address create
        ]
        refreshed = PortalClientProfile(
            user_id=42,
            party_id=77,
            login="client@example.com",
            email="client@example.com",
            first_name="Alice",
            last_name="Tremblay",
            company_name="ITF",
            phone="4185551234",
            address=PortalClientAddress(
                street="123 rue Principale",
                city="Mashteuiatsh",
                postal_code="G0W 2H0",
            ),
        )
        with patch.object(self.service, "fetch_client_profile", return_value=refreshed):
            profile = self.service.update_client_profile(
                login="client@example.com",
                company_name="ITF",
                first_name="Alice",
                last_name="Tremblay",
                phone="4185551234",
                address="123 rue Principale",
                city="Mashteuiatsh",
                postal_code="G0W 2H0",
            )

        self.assertEqual(profile, refreshed)
        self.assertIn(
            call(
                "model.party.party",
                "write",
                [
                    [77],
                    {"contact_mechanisms": [("create", [{"type": "phone", "value": "4185551234"}])]},
                    {},
                ],
            ),
            self.tryton_client.call.mock_calls,
        )

    def test_change_password_requires_valid_current_password(self):
        self.tryton_client.call.side_effect = [
            [42],  # res.user search
            [
                {
                    "id": 42,
                    "name": "Alice Tremblay",
                    "email": "client@example.com",
                    "party": 77,
                }
            ],  # res.user read
            None,  # res.user write
        ]
        with patch.object(self.service, "validate_credentials", return_value=True) as validate_mock:
            self.service.change_password(
                login="client@example.com",
                current_password="Ancien123!",
                new_password="Nouveau123!",
            )
        validate_mock.assert_called_once()

    def test_change_password_raises_when_tryton_write_fails(self):
        self.tryton_client.call.side_effect = [
            [42],
            [
                {
                    "id": 42,
                    "name": "Alice Tremblay",
                    "email": "client@example.com",
                    "party": 77,
                }
            ],
            TrytonRPCError("boom"),  # type: ignore[name-defined]
        ]
        with patch.object(self.service, "validate_credentials", return_value=True):
            with self.assertRaises(PortalAccountServiceError):
                self.service.change_password(
                    login="client@example.com",
                    current_password="Ancien123!",
                    new_password="Nouveau123!",
                )

    def test_fetch_client_profile_errors_when_party_field_missing(self):
        self.service._user_has_party_field = False
        self.tryton_client.call.side_effect = [
            [42],
            [
                {
                    "id": 42,
                    "name": "Alice Tremblay",
                    "email": "client@example.com",
                }
            ],
            [],
        ]

        with self.assertRaises(PortalAccountServiceError):
            self.service.fetch_client_profile(login="client@example.com")

        self.assertEqual(
            self.tryton_client.call.mock_calls[2],
            call(
                "model.party.contact_mechanism",
                "search",
                [[("type", "=", "email"), ("value", "=", "client@example.com")], 0, 1, None, {}],
            ),
        )

    def test_fetch_client_profile_uses_contact_mechanism_when_party_field_missing(self):
        self.service._user_has_party_field = False
        self.tryton_client.call.side_effect = [
            [42],  # user search
            [
                {
                    "id": 42,
                    "name": "Alice Tremblay",
                    "email": "client@example.com",
                }
            ],
            [91],  # contact search
            [
                {
                    "party": 77,
                }
            ],  # contact read
            [
                {
                    "id": 77,
                    "name": "ITF",
                }
            ],  # party read
            [],  # phone search (aucun contact)
            [18],  # address search
            [
                {
                    "street": "123 rue Principale",
                    "city": "Mashteuiatsh",
                    "zip": "G0W 2H0",
                }
            ],
        ]

        profile = self.service.fetch_client_profile(login="client@example.com")

        self.assertEqual(profile.party_id, 77)
        self.assertEqual(profile.address.city, "Mashteuiatsh")


class ClientProfileViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="client@example.com",
            email="client@example.com",
            password="irrelevant",
        )
        self.profile = PortalClientProfile(
            user_id=42,
            party_id=77,
            login="client@example.com",
            email="client@example.com",
            first_name="Alice",
            last_name="Tremblay",
            company_name="ITF",
            phone="4185551234",
            address=PortalClientAddress(
                street="123 rue Principale",
                city="Mashteuiatsh",
                postal_code="G0W 2H0",
            ),
        )

    def test_get_renders_profile_page(self):
        service_instance = MagicMock()
        service_instance.fetch_client_profile.return_value = self.profile
        with patch.object(ClientProfileView, "service_class", return_value=service_instance):
            self.client.force_login(self.user)
            response = self.client.get(reverse("accounts:profile"))

            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, "accounts/profile.html")
            form = response.context["profile_form"]
            self.assertEqual(form.initial["first_name"], "Alice")

    def test_post_profile_updates_information_and_redirects(self):
        service_instance = MagicMock()
        service_instance.fetch_client_profile.return_value = self.profile
        service_instance.update_client_profile.return_value = self.profile
        with patch.object(ClientProfileView, "service_class", return_value=service_instance):
            self.client.force_login(self.user)
            response = self.client.post(
                reverse("accounts:profile"),
                data={
                    "form_name": "profile",
                    "company_name": "ITF",
                    "first_name": "Alice",
                    "last_name": "Tremblay",
                    "email": "client@example.com",
                    "phone": "4185551234",
                    "address": "123 rue Principale",
                    "city": "Mashteuiatsh",
                    "postal_code": "G0W 2H0",
                },
            )

            self.assertRedirects(response, reverse("accounts:profile"))
            service_instance.update_client_profile.assert_called_once()

    def test_post_password_updates_password_and_redirects(self):
        service_instance = MagicMock()
        service_instance.fetch_client_profile.return_value = self.profile
        service_instance.validate_credentials.return_value = True
        with patch.object(ClientProfileView, "service_class", return_value=service_instance):
            self.client.force_login(self.user)
            response = self.client.post(
                reverse("accounts:profile"),
                data={
                    "form_name": "password",
                    "current_password": "Ancien123!",
                    "new_password1": "Nouveau123!",
                    "new_password2": "Nouveau123!",
                },
            )

            self.assertRedirects(response, reverse("accounts:profile"))
            service_instance.change_password.assert_called_once_with(
                login="client@example.com",
                current_password="Ancien123!",
                new_password="Nouveau123!",
            )
