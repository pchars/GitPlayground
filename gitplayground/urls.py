from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

handler400 = "apps.core.views.errors.bad_request"
handler403 = "apps.core.views.errors.permission_denied"
handler404 = "apps.core.views.errors.page_not_found"
handler500 = "apps.core.views.errors.server_error"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
