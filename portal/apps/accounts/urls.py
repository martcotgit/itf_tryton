from django.urls import path

from .views import (

    ClientLoginView,
    ClientLogoutView,
    ClientProfileView,
    ClientSignupView,
    InvoiceListView,
    InvoiceDetailView,
    OrderCatalogView,
    OrderCreateView,
    OrderDetailView,
    OrderListView,
    CustomOrderChoiceView,
    CustomOrderWizardView,
    CustomOrderConfirmationView,
)

app_name = "accounts"

urlpatterns = [
    path("", ClientLoginView.as_view(), name="login"),
    path("deconnexion/", ClientLogoutView.as_view(), name="logout"),

    path("profil/", ClientProfileView.as_view(), name="profile"),
    path("inscription/", ClientSignupView.as_view(), name="signup"),
    path("factures/", InvoiceListView.as_view(), name="invoices-list"),
    path("factures/<int:invoice_id>/", InvoiceDetailView.as_view(), name="invoices-detail"),
    path("commandes/", OrderListView.as_view(), name="orders-list"),
    path("commandes/<int:order_id>/", OrderDetailView.as_view(), name="orders-detail"),
    
    # New Flow
    path("commandes/nouvelle/", CustomOrderChoiceView.as_view(), name="orders-new"), # Choice
    path("commandes/creer/", OrderCreateView.as_view(), name="orders-create"), # Standard
    path("commandes/sur-mesure/", CustomOrderWizardView.as_view(), {"step": 1}, name="custom-order-start"),
    path("commandes/sur-mesure/<int:step>/", CustomOrderWizardView.as_view(), name="custom-order-wizard"),
    path("commandes/sur-mesure/confirmation/<int:order_id>/", CustomOrderConfirmationView.as_view(), name="custom-order-confirmation"),
    
    # Old Catalog (API)
    path("commandes/catalogue/", OrderCatalogView.as_view(), name="orders-catalog"),
]
