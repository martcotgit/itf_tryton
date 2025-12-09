from django.urls import path

from .views import ContactView, HealthCheckView, HomeView, ProductsView, ServicesView, TermsOfServiceView, PrivacyPolicyView

app_name = "core"

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("services/", ServicesView.as_view(), name="services"),
    path("produits/", ProductsView.as_view(), name="products"),
    path("health/", HealthCheckView.as_view(), name="health"),
    path("contact/", ContactView.as_view(), name="contact"),
    path("legal/cgu/", TermsOfServiceView.as_view(), name="terms_of_service"),
    path("legal/confidentialite/", PrivacyPolicyView.as_view(), name="privacy_policy"),
]
