from django.urls import path

from .views import ContactView, HealthCheckView, HomeView, ProductsView, ServicesView

app_name = "core"

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("services/", ServicesView.as_view(), name="services"),
    path("produits/", ProductsView.as_view(), name="products"),
    path("health/", HealthCheckView.as_view(), name="health"),
    path("contact/", ContactView.as_view(), name="contact"),
]
