from django.urls import path

from .views import (

    ClientLoginView,
    ClientLogoutView,
    ClientProfileView,
    ClientSignupView,
    InvoiceListView,
    OrderCatalogView,
    OrderCreateView,
    OrderDetailView,
    OrderListView,
)

app_name = "accounts"

urlpatterns = [
    path("", ClientLoginView.as_view(), name="login"),
    path("deconnexion/", ClientLogoutView.as_view(), name="logout"),

    path("profil/", ClientProfileView.as_view(), name="profile"),
    path("inscription/", ClientSignupView.as_view(), name="signup"),
    path("factures/", InvoiceListView.as_view(), name="invoices-list"),
    path("commandes/", OrderListView.as_view(), name="orders-list"),
    path("commandes/<int:order_id>/", OrderDetailView.as_view(), name="orders-detail"),
    path("commandes/nouvelle/", OrderCreateView.as_view(), name="orders-new"),
    path("commandes/catalogue/", OrderCatalogView.as_view(), name="orders-catalog"),
]
