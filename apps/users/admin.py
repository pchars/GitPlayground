from django.contrib import admin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "pseudonym",
        "certificate_name",
        "user",
        "total_points",
        "marketing_opt_in",
        "updated_at",
    )
    search_fields = ("pseudonym", "certificate_name", "user__username", "user__email")
    list_filter = ("learning_goal", "knowledge_level", "marketing_opt_in")
