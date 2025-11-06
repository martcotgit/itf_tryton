from django.urls import path

from .views import (
    ClientDashboardView,
    ClientLoginView,
    ClientLogoutView,
    ClientSignupPlaceholderView,
)

app_name = "accounts"

urlpatterns = [
    path("", ClientLoginView.as_view(), name="login"),
    path("deconnexion/", ClientLogoutView.as_view(), name="logout"),
    path("tableau-de-bord/", ClientDashboardView.as_view(), name="dashboard"),
    path("inscription/", ClientSignupPlaceholderView.as_view(), name="signup"),
]
