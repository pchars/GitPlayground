from django.contrib import admin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("public_nickname", "user", "total_points", "updated_at")
    search_fields = ("public_nickname", "user__username", "user__email")
    list_filter = ("created_at", "updated_at")
