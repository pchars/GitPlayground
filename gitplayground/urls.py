from django.contrib import admin
from django.urls import include, path

from apps.tasks.admin_views import upload_task_zip_view

urlpatterns = [
    path("admin/tasks/upload/", upload_task_zip_view, name="admin-task-upload"),
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls")),
]
