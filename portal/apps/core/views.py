from django.http import JsonResponse
from django.views import View
from django.views.generic import TemplateView


class HealthCheckView(View):
    """Lightweight health endpoint for Docker/Traefik checks."""

    def get(self, request, *args, **kwargs):
        return JsonResponse({"status": "ok"})


class HomeView(TemplateView):
    template_name = "core/home.html"
