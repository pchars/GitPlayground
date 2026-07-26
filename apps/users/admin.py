from django.contrib import admin

from .models import CompletionCertificate, UserProfile


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


@admin.register(CompletionCertificate)
class CompletionCertificateAdmin(admin.ModelAdmin):
    list_display = ("verification_code", "display_name", "user", "issued_at", "email_sent_at")
    search_fields = ("verification_code", "display_name", "user__email")
    readonly_fields = ("verification_code", "issued_at")
