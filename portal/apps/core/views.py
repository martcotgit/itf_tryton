import logging

from django.http import JsonResponse
from django.core.paginator import Paginator
from django.views import View
from django.views.generic import TemplateView

from apps.core.services import PublicProductService, PublicProductServiceError, build_products_schema
from apps.accounts.services import PortalOrderService


logger = logging.getLogger(__name__)


class HealthCheckView(View):
    """Lightweight health endpoint for Docker/Traefik checks."""

    def get(self, request, *args, **kwargs):
        return JsonResponse({"status": "ok"})


class HomeView(TemplateView):
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            try:
                service = PortalOrderService()
                result = service.list_orders(login=self.request.user.email, page_size=5)
                context["recent_orders"] = result.orders
            except Exception as e:
                logger.error("Error fetching orders for home dashboard: %s", e)
                context["recent_orders"] = []
        return context



class ServicesView(TemplateView):
    template_name = "core/services.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        canonical_url = self.request.build_absolute_uri(self.request.path)
        context.update(
            {
                "canonical_url": canonical_url,
                "page_description": (
                    "Services intégrés de récupération, tri et logistique de palettes au Saguenay–Lac-Saint-Jean. "
                    "Interventions rapides, consignation et réparations certifiées."
                ),
                "page_keywords": (
                    "récupération de palettes, consignation palettes, réparation palettes, logistique palettes, "
                    "Saguenay Lac Saint Jean"
                ),
            }
        )
        return context


class ProductsView(TemplateView):
    template_name = "core/products.html"
    service_class = PublicProductService
    per_page = 12

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = self.service_class()
        try:
            products = service.list_available_products()
        except PublicProductServiceError as exc:
            logger.warning("Catalogue Tryton indisponible pour la page Produits: %s", exc)
            products = []
        paginator = Paginator(products, self.per_page)
        page_obj = paginator.get_page(self.request.GET.get("page"))
        canonical_url = self.request.build_absolute_uri(self.request.path)
        context.update(
            {
                "products": page_obj,
                "page_obj": page_obj,
                "paginator": paginator,
                "products_total": paginator.count,
                "category_facets": self._build_category_facets(products),
                "canonical_url": canonical_url,
                "products_schema": build_products_schema(list(page_obj), canonical_url) if products else None,
                "page_description": (
                    "Catalogue complet de palettes neuves, recyclées et consignées disponibles au Saguenay–Lac-Saint-Jean."
                ),
                "page_keywords": "palettes neuves, palettes usagées, palettes consignées, récupération de palettes",
            }
        )
        return context

    @staticmethod
    def _build_category_facets(products):
        counts: dict[str, int] = {}
        for product in products:
            categories = product.categories or ("Palettes",)
            for category in categories:
                counts[category] = counts.get(category, 0) + 1
        facets = [
            {"name": name, "count": counts[name]} for name in sorted(counts.keys(), key=str.lower)
        ]
        return facets
