from django.contrib import admin

from .models import Achievement, UserAchievement


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "threshold_tasks", "points_bonus", "icon_path", "is_active")
    list_filter = ("is_active",)
    search_fields = ("title", "slug")


@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ("user", "achievement", "awarded_at")
    list_filter = ("achievement",)
    search_fields = ("user__username", "achievement__title")
    list_select_related = ("user", "achievement")
