from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include(("apps.core.urls", "core"), namespace="core")),
    path("client/", include(("apps.accounts.urls", "accounts"), namespace="accounts")),
]
