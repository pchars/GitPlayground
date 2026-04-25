"""Профиль пользователя и связанная статистика обучения."""

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Avg, Max
from django.shortcuts import get_object_or_404, redirect, render

from apps.achievements.models import Achievement, UserAchievement

K = Achievement.CriterionKind
from apps.achievements.services import bootstrap_default_achievements
from apps.progress.models import TaskAttempt, TaskCompletion
from apps.quiz.models import QuizQuestion, QuizQuestionProgress, QuizUserStats
from apps.tasks.models import Level
from apps.users.models import UserProfile

from .helpers import _task_has_platform_column


def _profile_learning_stats(user: User) -> dict:
    bootstrap_default_achievements()
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={"public_nickname": user.username},
    )
    completions = (
        TaskCompletion.objects.filter(user=user)
        .select_related("task")
        .order_by("-completed_at")[:5]
    )
    completed_task_ids = set(
        TaskCompletion.objects.filter(user=user).values_list("task_id", flat=True)
    )
    if _task_has_platform_column():
        levels = Level.objects.prefetch_related("tasks").order_by("number")
    else:
        levels = Level.objects.order_by("number")
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
    all_achievements = Achievement.objects.filter(is_active=True).order_by("title")
    completed_tasks_count = TaskCompletion.objects.filter(user=user).count()
    next_achievement = (
        Achievement.objects.filter(is_active=True, threshold_tasks__gt=completed_tasks_count)
        .order_by("threshold_tasks")
        .first()
    )
    avg_attempts = (
        TaskAttempt.objects.filter(user=user)
        .values("task")
        .annotate(total=Max("attempt_no"))
        .aggregate(avg=Avg("total"))
        .get("avg")
        or 0
    )
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
    has_quiz_fail = QuizQuestionProgress.objects.filter(user=user, failed_attempts__gt=0).exists()
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
            status = "без ошибок" if not has_quiz_fail else "есть ошибки"
            progress_text = f"{solved_total}/{total_quiz} вопросов, статус: {status}"
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
        "completions": completions,
        "level_progress": level_progress,
        "total_tasks": total_tasks,
        "total_completed": total_completed,
        "progress_pct": progress_pct,
        "achievements": achievements,
        "available_achievements": available_achievements,
        "next_achievement": next_achievement,
        "completed_tasks_count": completed_tasks_count,
        "avg_attempts": avg_attempts,
        "theory_dropoff": theory_dropoff,
    }


def public_profile(request, username):
    user = get_object_or_404(User, username=username)
    stats = _profile_learning_stats(user)
    profile = stats["profile"]
    return render(
        request,
        "core/profile.html",
        {
            "profile_user": user,
            "profile": profile,
            **stats,
        },
    )


@login_required
def profile_self(request):
    return redirect("public-profile", username=request.user.username)
