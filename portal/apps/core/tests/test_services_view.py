from __future__ import annotations

from django.test import TestCase
from django.urls import reverse


class ServicesViewTest(TestCase):
    def test_services_page_renders_with_metadata(self) -> None:
        url = reverse("core:services")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Récupération, tri, consignation")
        self.assertEqual(response.context["canonical_url"], f"http://testserver{url}")
        self.assertIn("page_description", response.context)
        self.assertIn("page_keywords", response.context)
