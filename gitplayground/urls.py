from django.contrib import admin
from django.urls import include, path

handler400 = "apps.core.views.errors.bad_request"
handler403 = "apps.core.views.errors.permission_denied"
handler404 = "apps.core.views.errors.page_not_found"
handler500 = "apps.core.views.errors.server_error"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls")),
]
