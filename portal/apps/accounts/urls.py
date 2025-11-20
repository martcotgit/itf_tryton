from django.urls import path

from .views import (
    ClientDashboardView,
    ClientLoginView,
    ClientLogoutView,
    ClientProfileView,
    ClientSignupView,
    OrderCatalogView,
    OrderCreateView,
)

app_name = "accounts"

urlpatterns = [
    path("", ClientLoginView.as_view(), name="login"),
    path("deconnexion/", ClientLogoutView.as_view(), name="logout"),
    path("tableau-de-bord/", ClientDashboardView.as_view(), name="dashboard"),
    path("profil/", ClientProfileView.as_view(), name="profile"),
    path("inscription/", ClientSignupView.as_view(), name="signup"),
    path("commandes/nouvelle/", OrderCreateView.as_view(), name="orders-new"),
    path("commandes/catalogue/", OrderCatalogView.as_view(), name="orders-catalog"),
]
