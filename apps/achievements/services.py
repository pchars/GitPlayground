from django.contrib.auth.models import User
from django.db import transaction

from apps.achievements.models import Achievement, UserAchievement
from apps.progress.models import TaskCompletion
from apps.quiz.models import QuizQuestion, QuizQuestionProgress, QuizUserStats
from apps.tasks.models import Task
from apps.users.models import PointLedgerEntry
from apps.users.services import ensure_user_profile
from apps.users.services import ensure_user_profile

K = Achievement.CriterionKind

# Gallery order: tasks → quiz (easy→hard→milestones) → streaks.
ACHIEVEMENT_KIND_ORDER: dict[str, int] = {
    K.TASKS_COMPLETED: 0,
    K.QUIZ_EASY_SOLVED: 1,
    K.QUIZ_MEDIUM_SOLVED: 2,
    K.QUIZ_HARD_SOLVED: 3,
    K.QUIZ_ALL_SOLVED: 4,
    K.STREAK_MIN: 5,
    K.STREAK_FLAWLESS: 6,
}


def achievement_gallery_sort_key(achievement: Achievement) -> tuple[int, int, str]:
    """Sort achievements for profile: simple first, then rising difficulty/targets."""
    return (
        ACHIEVEMENT_KIND_ORDER.get(achievement.criterion_kind, 99),
        achievement.criterion_target,
        achievement.slug,
    )


def _task_achievement(
    slug: str,
    title: str,
    description: str,
    icon_path: str,
    target: int,
    points_bonus: int,
) -> dict:
    return {
        "slug": slug,
        "title": title,
        "description": description,
        "icon_path": icon_path,
        "points_bonus": points_bonus,
        "threshold_tasks": target,
        "criterion_kind": K.TASKS_COMPLETED,
        "criterion_target": target,
        "is_active": True,
    }


def _quiz_solved_achievement(
    slug: str,
    title: str,
    description: str,
    icon_path: str,
    target: int,
    points_bonus: int,
) -> dict:
    return {
        "slug": slug,
        "title": title,
        "description": description,
        "icon_path": icon_path,
        "points_bonus": points_bonus,
        "threshold_tasks": target,
        "criterion_kind": K.QUIZ_ALL_SOLVED,
        "criterion_target": target,
        "is_active": True,
    }


def _streak_achievement(
    slug: str,
    title: str,
    description: str,
    icon_path: str,
    target: int,
    points_bonus: int,
) -> dict:
    return {
        "slug": slug,
        "title": title,
        "description": description,
        "icon_path": icon_path,
        "points_bonus": points_bonus,
        "threshold_tasks": target,
        "criterion_kind": K.STREAK_MIN,
        "criterion_target": target,
        "is_active": True,
    }


def bootstrap_default_achievements() -> None:
    total_tasks = max(1, Task.objects.count())
    total_quiz_questions = max(1, QuizQuestion.objects.count())
    easy_quiz_questions = max(1, QuizQuestion.objects.filter(difficulty=QuizQuestion.Difficulty.EASY).count())
    medium_quiz_questions = max(1, QuizQuestion.objects.filter(difficulty=QuizQuestion.Difficulty.MEDIUM).count())
    hard_quiz_questions = max(1, QuizQuestion.objects.filter(difficulty=QuizQuestion.Difficulty.HARD).count())
    defaults = [
        _task_achievement(
            "first_commit",
            "Первый коммит",
            "Завершена первая практическая задача.",
            "img/achievements/first_commit.svg",
            1,
            5,
        ),
        _task_achievement(
            "tasks_5",
            "В деле",
            "Завершено 5 практических задач.",
            "img/achievements/tasks_5.svg",
            5,
            8,
        ),
        _task_achievement(
            "tasks_10",
            "Десятка",
            "Завершено 10 практических задач.",
            "img/achievements/tasks_10.svg",
            10,
            12,
        ),
        _task_achievement(
            "tasks_20",
            "Двадцатка",
            "Завершено 20 практических задач.",
            "img/achievements/tasks_20.svg",
            20,
            16,
        ),
        _task_achievement(
            "tasks_40",
            "На полпути",
            "Завершено 40 практических задач.",
            "img/achievements/tasks_40.svg",
            40,
            22,
        ),
        _task_achievement(
            "tasks_60",
            "Финишная прямая",
            "Завершено 60 практических задач.",
            "img/achievements/tasks_60.svg",
            60,
            28,
        ),
        _task_achievement(
            "git_master",
            "Мастер Git",
            "Пройден весь курс практики.",
            "img/achievements/git_master.svg",
            total_tasks,
            50,
        ),
        {
            "slug": "quiz_easy_complete",
            "title": "Зелёная зона",
            "description": "Решены все вопросы лёгкой сложности.",
            "icon_path": "img/achievements/quiz_easy_complete.svg",
            "points_bonus": 12,
            "threshold_tasks": easy_quiz_questions,
            "criterion_kind": K.QUIZ_EASY_SOLVED,
            "criterion_target": easy_quiz_questions,
            "is_active": True,
        },
        {
            "slug": "quiz_medium_complete",
            "title": "Середина сложности",
            "description": "Решены все вопросы средней сложности.",
            "icon_path": "img/achievements/quiz_medium_complete.svg",
            "points_bonus": 18,
            "threshold_tasks": medium_quiz_questions,
            "criterion_kind": K.QUIZ_MEDIUM_SOLVED,
            "criterion_target": medium_quiz_questions,
            "is_active": True,
        },
        {
            "slug": "quiz_hard_complete",
            "title": "Тяжёлый класс",
            "description": "Решены все вопросы высокой сложности.",
            "icon_path": "img/achievements/quiz_hard_complete.svg",
            "points_bonus": 25,
            "threshold_tasks": hard_quiz_questions,
            "criterion_kind": K.QUIZ_HARD_SOLVED,
            "criterion_target": hard_quiz_questions,
            "is_active": True,
        },
        _quiz_solved_achievement(
            "quiz_50_solved",
            "Квиз-новичок",
            "Правильно решено 50 вопросов квиза.",
            "img/achievements/quiz_50_solved.svg",
            50,
            6,
        ),
        _quiz_solved_achievement(
            "quiz_100_solved",
            "Сотня знаний",
            "Правильно решено 100 вопросов квиза.",
            "img/achievements/quiz_100_solved.svg",
            100,
            10,
        ),
        _quiz_solved_achievement(
            "quiz_250_solved",
            "Четверть пути",
            "Правильно решено 250 вопросов квиза.",
            "img/achievements/quiz_250_solved.svg",
            250,
            14,
        ),
        _quiz_solved_achievement(
            "quiz_500_solved",
            "Полтысячи",
            "Правильно решено 500 вопросов квиза.",
            "img/achievements/quiz_500_solved.svg",
            500,
            18,
        ),
        _quiz_solved_achievement(
            "quiz_750_solved",
            "Почти всё",
            "Правильно решено 750 вопросов квиза.",
            "img/achievements/quiz_750_solved.svg",
            750,
            22,
        ),
        {
            "slug": "quiz_all_complete",
            "title": "Квиз-марафон",
            "description": "Решены все вопросы квиза.",
            "icon_path": "img/achievements/quiz_all_complete.svg",
            "points_bonus": 40,
            "threshold_tasks": total_quiz_questions,
            "criterion_kind": K.QUIZ_ALL_SOLVED,
            "criterion_target": total_quiz_questions,
            "is_active": True,
        },
        _streak_achievement(
            "streak_5",
            "Горячая серия",
            "Серия из 5 правильных ответов подряд.",
            "img/achievements/streak_5.svg",
            5,
            5,
        ),
        _streak_achievement(
            "streak_10",
            "На волне",
            "Серия из 10 правильных ответов подряд.",
            "img/achievements/streak_10.svg",
            10,
            10,
        ),
        _streak_achievement(
            "streak_25",
            "Неудержимый",
            "Серия из 25 правильных ответов подряд.",
            "img/achievements/streak_25.svg",
            25,
            15,
        ),
        _streak_achievement(
            "streak_50",
            "Снайпер",
            "Серия из 50 правильных ответов подряд.",
            "img/achievements/streak_50.svg",
            50,
            20,
        ),
        _streak_achievement(
            "streak_75",
            "Меткий стрелок",
            "Серия из 75 правильных ответов подряд.",
            "img/achievements/streak_75.svg",
            75,
            25,
        ),
        _streak_achievement(
            "streak_100",
            "Сто подряд",
            "Серия из 100 правильных ответов подряд.",
            "img/achievements/streak_100.svg",
            100,
            30,
        ),
        {
            "slug": "streak_flawless",
            "title": "Без единой ошибки",
            "description": "Ответить правильно на все вопросы квиза без единой ошибки.",
            "icon_path": "img/achievements/streak_flawless.svg",
            "points_bonus": 60,
            "threshold_tasks": total_quiz_questions,
            "criterion_kind": K.STREAK_FLAWLESS,
            "criterion_target": total_quiz_questions,
            "is_active": True,
        },
    ]
    active_slugs = {item["slug"] for item in defaults}
    for item in defaults:
        Achievement.objects.update_or_create(
            slug=item["slug"],
            defaults=item,
        )
    Achievement.objects.exclude(slug__in=active_slugs).update(is_active=False)


def achievement_toast_payload(user_achievement: UserAchievement) -> dict:
    achievement = user_achievement.achievement
    return {
        "icon": achievement.icon_path,
        "title": achievement.title,
        "description": achievement.description,
    }


def achievement_toast_payloads_since(user: User, before_achievement_ids: set[int]) -> list[dict]:
    rows = (
        UserAchievement.objects.filter(user=user)
        .exclude(achievement_id__in=before_achievement_ids)
        .select_related("achievement")
        .order_by("-awarded_at")
    )
    return [achievement_toast_payload(item) for item in rows]


def quiz_streak_flawless_status(user: User) -> str:
    """STREAK_FLAWLESS status — must match evaluate_achievements_for_user."""
    has_any_quiz_fail = QuizQuestionProgress.objects.filter(user=user, failed_attempts__gt=0).exists()
    quiz_stats, _ = QuizUserStats.objects.get_or_create(user=user)
    flawless = (
        not has_any_quiz_fail
        and quiz_stats.answered_total > 0
        and quiz_stats.answered_total == quiz_stats.correct_total
    )
    return "без ошибок" if flawless else "есть ошибки"


@transaction.atomic
def evaluate_achievements_for_user(user: User) -> list[UserAchievement]:
    bootstrap_default_achievements()
    completed_count = TaskCompletion.objects.filter(user=user).count()
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
    has_any_quiz_fail = QuizQuestionProgress.objects.filter(user=user, failed_attempts__gt=0).exists()
    awarded: list[UserAchievement] = []
    profile = ensure_user_profile(user)
    achievements = Achievement.objects.filter(is_active=True, criterion_target__gt=0).order_by(
        "criterion_target", "slug"
    )
    K = Achievement.CriterionKind
    for achievement in achievements:
        kind = achievement.criterion_kind
        target = achievement.criterion_target
        should_award = False
        if kind == K.TASKS_COMPLETED:
            should_award = completed_count >= target
        elif kind == K.QUIZ_EASY_SOLVED:
            should_award = total_easy > 0 and solved_easy >= target
        elif kind == K.QUIZ_MEDIUM_SOLVED:
            should_award = total_medium > 0 and solved_medium >= target
        elif kind == K.QUIZ_HARD_SOLVED:
            should_award = total_hard > 0 and solved_hard >= target
        elif kind == K.QUIZ_ALL_SOLVED:
            should_award = total_quiz > 0 and solved_total >= target
        elif kind == K.STREAK_FLAWLESS:
            should_award = (
                total_quiz > 0
                and solved_total >= target
                and not has_any_quiz_fail
                and quiz_stats.answered_total > 0
                and quiz_stats.answered_total == quiz_stats.correct_total
            )
        elif kind == K.STREAK_MIN:
            should_award = quiz_stats.best_streak >= target
        if not should_award:
            continue
        user_achievement, created = UserAchievement.objects.get_or_create(
            user=user,
            achievement=achievement,
        )
        if created:
            profile.total_points += achievement.points_bonus
            awarded.append(user_achievement)
            PointLedgerEntry.objects.get_or_create(
                user=user,
                source=PointLedgerEntry.Source.ACHIEVEMENT,
                ref_key=f"achievement:{achievement.slug}",
                defaults={"delta": achievement.points_bonus},
            )
    if awarded:
        profile.save(update_fields=["total_points", "updated_at"])
    return awarded
