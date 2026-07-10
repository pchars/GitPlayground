"""User profile and related learning statistics."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from apps.achievements.models import Achievement, UserAchievement
from apps.achievements.services import achievement_gallery_sort_key, quiz_streak_flawless_status
from apps.core.forms import ProfileEditForm
from apps.progress.models import TaskCompletion
from apps.quiz.models import QuizQuestion, QuizQuestionProgress, QuizUserStats
from apps.tasks.models import Level
from apps.users.services import ensure_user_profile

K = Achievement.CriterionKind


def _profile_learning_stats(user) -> dict:
    profile = ensure_user_profile(user)
    completed_task_ids = set(
        TaskCompletion.objects.filter(user=user).values_list("task_id", flat=True)
    )
    levels = Level.objects.prefetch_related("tasks").order_by("number")
    level_progress = []
    total_tasks = 0
    total_completed = 0
    for level in levels:
        task_ids = [task.id for task in level.tasks.all()]
        completed = sum(1 for task_id in task_ids if task_id in completed_task_ids)
        level_total = len(task_ids)
        total_tasks += level_total
        total_completed += completed
        level_progress.append({"level": level, "completed": completed, "total": level_total})

    progress_pct = round((total_completed / total_tasks) * 100) if total_tasks else 0
    achievements = UserAchievement.objects.filter(user=user).select_related("achievement").order_by("-awarded_at")
    achievement_map = {ua.achievement_id: ua for ua in achievements}
    all_achievements = sorted(
        Achievement.objects.filter(is_active=True),
        key=achievement_gallery_sort_key,
    )
    completed_tasks_count = TaskCompletion.objects.filter(user=user).count()
    theory_dropoff = max(0, total_tasks - total_completed)
    quiz_stats, _ = QuizUserStats.objects.get_or_create(user=user)
    solved_progress = QuizQuestionProgress.objects.filter(user=user, solved=True).select_related("question")
    solved_total = solved_progress.count()
    solved_easy = solved_progress.filter(question__difficulty=QuizQuestion.Difficulty.EASY).count()
    solved_medium = solved_progress.filter(question__difficulty=QuizQuestion.Difficulty.MEDIUM).count()
    solved_hard = solved_progress.filter(question__difficulty=QuizQuestion.Difficulty.HARD).count()
    total_quiz = QuizQuestion.objects.count()
    total_easy = QuizQuestion.objects.filter(difficulty=QuizQuestion.Difficulty.EASY).count()
    total_medium = QuizQuestion.objects.filter(difficulty=QuizQuestion.Difficulty.MEDIUM).count()
    total_hard = QuizQuestion.objects.filter(difficulty=QuizQuestion.Difficulty.HARD).count()
    available_achievements = []
    for ach in all_achievements:
        unlocked = ach.id in achievement_map
        progress_text = ""
        if ach.criterion_kind == K.QUIZ_EASY_SOLVED:
            progress_text = f"{solved_easy}/{total_easy} вопросов легкого уровня"
        elif ach.criterion_kind == K.QUIZ_MEDIUM_SOLVED:
            progress_text = f"{solved_medium}/{total_medium} вопросов среднего уровня"
        elif ach.criterion_kind == K.QUIZ_HARD_SOLVED:
            progress_text = f"{solved_hard}/{total_hard} вопросов тяжелого уровня"
        elif ach.criterion_kind == K.QUIZ_ALL_SOLVED:
            progress_text = f"{solved_total}/{total_quiz} вопросов квиза"
        elif ach.criterion_kind == K.STREAK_FLAWLESS:
            progress_text = f"{solved_total}/{total_quiz} вопросов, статус: {quiz_streak_flawless_status(user)}"
        elif ach.criterion_kind == K.STREAK_MIN:
            progress_text = f"Лучшая серия: {quiz_stats.best_streak}/{ach.criterion_target}"
        else:
            progress_text = f"{completed_tasks_count}/{ach.criterion_target} задач"
        available_achievements.append(
            {
                "achievement": ach,
                "unlocked": unlocked,
                "progress_text": progress_text,
                "awarded_at": achievement_map.get(ach.id).awarded_at if unlocked else None,
            }
        )
    return {
        "profile": profile,
        "level_progress": level_progress,
        "total_tasks": total_tasks,
        "total_completed": total_completed,
        "progress_pct": progress_pct,
        "available_achievements": available_achievements,
        "completed_tasks_count": completed_tasks_count,
        "theory_dropoff": theory_dropoff,
        "quiz_stats": quiz_stats,
        "solved_total": solved_total,
        "total_quiz": total_quiz,
    }


def _render_profile(request: HttpRequest, user) -> HttpResponse:
    stats = _profile_learning_stats(user)
    return render(
        request,
        "core/profile.html",
        {
            "profile_user": user,
            **stats,
        },
    )


@login_required
def profile_self(request: HttpRequest) -> HttpResponse:
    return _render_profile(request, request.user)


def public_profile(request: HttpRequest, username: str) -> HttpResponse:
    """Legacy URL — профиль доступен только владельцу."""
    if not request.user.is_authenticated or request.user.username != username:
        raise Http404
    return _render_profile(request, request.user)


@login_required
def profile_edit(request: HttpRequest) -> HttpResponse:
    profile = ensure_user_profile(request.user)
    form = ProfileEditForm(request.POST or None, user=request.user, profile=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Профиль обновлён.")
        return redirect("profile-self")
    return render(request, "core/profile_edit.html", {"form": form, "profile": profile})
