from django.contrib import admin

from .models import QuizQuestion, QuizUserStats


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "prompt_short", "correct_index", "created_at")
    list_filter = ("created_at",)
    search_fields = ("prompt",)

    @admin.display(description="Вопрос")
    def prompt_short(self, obj: QuizQuestion) -> str:
        return (obj.prompt[:60] + "…") if len(obj.prompt) > 60 else obj.prompt


@admin.register(QuizUserStats)
class QuizUserStatsAdmin(admin.ModelAdmin):
    list_display = ("user", "answered_total", "correct_total", "best_streak", "current_streak", "updated_at")
    search_fields = ("user__username",)
