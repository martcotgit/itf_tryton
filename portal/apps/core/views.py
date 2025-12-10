import logging

from django.http import JsonResponse
from django.core.paginator import Paginator
from django.views import View
from django.views.generic import TemplateView

from apps.core.services import PublicProductService, PublicProductServiceError, build_products_schema
from apps.accounts.services import PortalOrderService
from apps.core.forms import ContactForm
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.views.generic import FormView



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
    """Display either category list or products filtered by category."""
    template_name = "core/products.html"
    service_class = PublicProductService
    per_page = 12

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = self.service_class()
        category_id = kwargs.get('category_id')
        
        # Determine view mode
        if category_id is None:
            # Category list view
            context['view_mode'] = 'categories'
            try:
                categories = service.list_categories()
            except PublicProductServiceError as exc:
                logger.warning("Catalogue Tryton indisponible pour la page Produits: %s", exc)
                categories = []
            
            canonical_url = self.request.build_absolute_uri(self.request.path)
            context.update({
                'categories': categories,
                'canonical_url': canonical_url,
                'page_title': 'Nos Familles de Produits',
                'page_description': (
                    'Découvrez notre gamme complète de palettes neuves, recyclées et consignées '
                    'disponibles au Saguenay–Lac-Saint-Jean.'
                ),
                'page_keywords': 'palettes neuves, palettes usagées, palettes consignées, catégories palettes',
            })
        else:
            # Product list view (filtered by category)
            context['view_mode'] = 'products'
            try:
                products = service.list_available_products(category_id=category_id)
                # Get category name for display
                categories = service.list_categories()
                current_category = next((c for c in categories if c.category_id == category_id), None)
            except PublicProductServiceError as exc:
                logger.warning("Catalogue Tryton indisponible pour la page Produits: %s", exc)
                products = []
                current_category = None
            
            paginator = Paginator(products, self.per_page)
            page_obj = paginator.get_page(self.request.GET.get("page"))
            canonical_url = self.request.build_absolute_uri(self.request.path)
            
            category_name = current_category.name if current_category else "Produits"
            
            context.update({
                'products': page_obj,
                'page_obj': page_obj,
                'paginator': paginator,
                'products_total': paginator.count,
                'current_category': current_category,
                'category_id': category_id,
                'canonical_url': canonical_url,
                'products_schema': build_products_schema(list(page_obj), canonical_url) if products else None,
                'page_title': f'{category_name} | Catalogue Ilnu Transforme',
                'page_description': (
                    f'{paginator.count} produit(s) disponible(s) dans la catégorie {category_name} '
                    f'au Saguenay–Lac-Saint-Jean.'
                ),
                'page_keywords': f'{category_name}, palettes, Saguenay Lac Saint Jean',
            })
        
        return context

    @staticmethod
    def _build_category_facets(products):
        """Legacy method - kept for backward compatibility but not used in new design."""
        counts: dict[str, int] = {}
        for product in products:
            categories = product.categories or ("Palettes",)
            for category in categories:
                counts[category] = counts.get(category, 0) + 1
        facets = [
            {"name": name, "count": counts[name]} for name in sorted(counts.keys(), key=str.lower)
        ]
        return facets


class ContactView(FormView):
    template_name = "core/contact.html"
    form_class = ContactForm
    success_url = "/contact/?sent=True"

    def form_valid(self, form):
        # Send email
        subject = f"[Contact Web] {form.cleaned_data['subject']}"
        message = (
            f"Message de : {form.cleaned_data['name']} <{form.cleaned_data['email']}>\n\n"
            f"{form.cleaned_data['message']}"
        )
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [settings.DEFAULT_FROM_EMAIL],  # Send to admin/self for now
                fail_silently=False,
            )
        except Exception as e:
            logger.error(f"Error sending contact email: {e}")
            messages.error(self.request, "Une erreur est survenue lors de l'envoi du message. Veuillez réessayer plus tard.")
            return self.form_invalid(form)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.GET.get("sent"):
            context["success"] = True
        
        # SEO Metadata
        canonical_url = self.request.build_absolute_uri(self.request.path)
        context.update({
            "canonical_url": canonical_url,
            "page_title": "Contactez Ilnu Transforme | Palettes et Recyclage",
            "page_description": "Contactez notre équipe pour vos besoins en palettes neuves, usagées ou pour nos services de récupération au Saguenay–Lac-Saint-Jean. Réponse sous 24h.",
        })
        return context

class TermsOfServiceView(TemplateView):
    template_name = "core/legal/terms_of_service.html"

class PrivacyPolicyView(TemplateView):
    template_name = "core/legal/privacy_policy.html"
