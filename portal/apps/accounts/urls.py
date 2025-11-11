from django.urls import path

from .views import (
    ClientDashboardView,
    ClientLoginView,
    ClientLogoutView,
    ClientProfileView,
    ClientSignupView,
)

app_name = "accounts"

urlpatterns = [
    path("", ClientLoginView.as_view(), name="login"),
    path("deconnexion/", ClientLogoutView.as_view(), name="logout"),
    path("tableau-de-bord/", ClientDashboardView.as_view(), name="dashboard"),
    path("profil/", ClientProfileView.as_view(), name="profile"),
    path("inscription/", ClientSignupView.as_view(), name="signup"),
]
