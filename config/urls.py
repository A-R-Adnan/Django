"""Root URL configuration: the admin site and the REST API."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # All API routes live under /api/ (see tasks/urls.py).
    path("api/", include("tasks.urls")),
]
