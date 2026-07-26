from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
import logging

from apps.achievements.models import Achievement, UserAchievement
from apps.progress.models import TaskCompletion
from apps.quiz.models import QuizQuestion, QuizQuestionProgress, QuizUserStats
from apps.tasks.models import Task
from apps.users.models import PointLedgerEntry
from apps.users.services import ensure_user_profile

logger = logging.getLogger(__name__)

K = Achievement.CriterionKind

# Keep in sync with learn_ops.NON_BLOCKING_LEVEL_NUMBERS (avoid circular import).
_NON_BLOCKING_LEVEL_NUMBERS: frozenset[int] = frozenset({0})

# Gallery order: intro level → tasks → quiz → streaks.
ACHIEVEMENT_KIND_ORDER: dict[str, int] = {
    K.LEVEL_COMPLETED: 0,
    K.TASKS_COMPLETED: 1,
    K.QUIZ_EASY_SOLVED: 2,
    K.QUIZ_MEDIUM_SOLVED: 3,
    K.QUIZ_HARD_SOLVED: 4,
    K.QUIZ_ALL_SOLVED: 5,
    K.STREAK_MIN: 6,
    K.STREAK_FLAWLESS: 7,
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
    main_track_tasks = max(
        1,
        Task.objects.exclude(level__number__in=_NON_BLOCKING_LEVEL_NUMBERS).count(),
    )
    level0_tasks = Task.objects.filter(level__number=0).count()
    total_quiz_questions = max(1, QuizQuestion.objects.count())
    easy_quiz_questions = max(1, QuizQuestion.objects.filter(difficulty=QuizQuestion.Difficulty.EASY).count())
    medium_quiz_questions = max(1, QuizQuestion.objects.filter(difficulty=QuizQuestion.Difficulty.MEDIUM).count())
    hard_quiz_questions = max(1, QuizQuestion.objects.filter(difficulty=QuizQuestion.Difficulty.HARD).count())
    defaults = [
        {
            "slug": "terminal_ready",
            "title": "Терминал освоен",
            "description": "Пройден вводный уровень 0: терминал и знакомство с Git.",
            "icon_path": "img/achievements/terminal_ready.svg",
            "points_bonus": 3,
            "threshold_tasks": max(1, level0_tasks),
            "criterion_kind": K.LEVEL_COMPLETED,
            "criterion_target": 0,
            "is_active": True,
        },
        _task_achievement(
            "first_commit",
            "Первый коммит",
            "Завершена первая задача основного курса (с уровня 1).",
            "img/achievements/first_commit.svg",
            1,
            3,
        ),
        _task_achievement(
            "tasks_5",
            "В деле",
            "Завершено 5 задач основного курса.",
            "img/achievements/tasks_5.svg",
            5,
            4,
        ),
        _task_achievement(
            "tasks_10",
            "Десятка",
            "Завершено 10 задач основного курса.",
            "img/achievements/tasks_10.svg",
            10,
            6,
        ),
        _task_achievement(
            "tasks_20",
            "Двадцатка",
            "Завершено 20 задач основного курса.",
            "img/achievements/tasks_20.svg",
            20,
            8,
        ),
        _task_achievement(
            "tasks_40",
            "На полпути",
            "Завершено 40 задач основного курса.",
            "img/achievements/tasks_40.svg",
            40,
            11,
        ),
        _task_achievement(
            "tasks_60",
            "Финишная прямая",
            "Завершено 60 задач основного курса.",
            "img/achievements/tasks_60.svg",
            60,
            14,
        ),
        _task_achievement(
            "git_master",
            "Мастер Git",
            "Пройден весь основной курс практики (уровни 1+).",
            "img/achievements/git_master.svg",
            main_track_tasks,
            25,
        ),
        {
            "slug": "quiz_easy_complete",
            "title": "Зелёная зона",
            "description": "Решены все вопросы лёгкой сложности.",
            "icon_path": "img/achievements/quiz_easy_complete.svg",
            "points_bonus": 6,
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
            "points_bonus": 9,
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
            "points_bonus": 12,
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
            3,
        ),
        _quiz_solved_achievement(
            "quiz_100_solved",
            "Сотня знаний",
            "Правильно решено 100 вопросов квиза.",
            "img/achievements/quiz_100_solved.svg",
            100,
            5,
        ),
        _quiz_solved_achievement(
            "quiz_250_solved",
            "Четверть пути",
            "Правильно решено 250 вопросов квиза.",
            "img/achievements/quiz_250_solved.svg",
            250,
            7,
        ),
        _quiz_solved_achievement(
            "quiz_500_solved",
            "Полтысячи",
            "Правильно решено 500 вопросов квиза.",
            "img/achievements/quiz_500_solved.svg",
            500,
            9,
        ),
        _quiz_solved_achievement(
            "quiz_750_solved",
            "Почти всё",
            "Правильно решено 750 вопросов квиза.",
            "img/achievements/quiz_750_solved.svg",
            750,
            11,
        ),
        {
            "slug": "quiz_all_complete",
            "title": "Квиз-марафон",
            "description": "Решены все вопросы квиза.",
            "icon_path": "img/achievements/quiz_all_complete.svg",
            "points_bonus": 20,
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
            3,
        ),
        _streak_achievement(
            "streak_10",
            "На волне",
            "Серия из 10 правильных ответов подряд.",
            "img/achievements/streak_10.svg",
            10,
            5,
        ),
        _streak_achievement(
            "streak_25",
            "Неудержимый",
            "Серия из 25 правильных ответов подряд.",
            "img/achievements/streak_25.svg",
            25,
            8,
        ),
        _streak_achievement(
            "streak_50",
            "Снайпер",
            "Серия из 50 правильных ответов подряд.",
            "img/achievements/streak_50.svg",
            50,
            10,
        ),
        _streak_achievement(
            "streak_75",
            "Меткий стрелок",
            "Серия из 75 правильных ответов подряд.",
            "img/achievements/streak_75.svg",
            75,
            12,
        ),
        _streak_achievement(
            "streak_100",
            "Сто подряд",
            "Серия из 100 правильных ответов подряд.",
            "img/achievements/streak_100.svg",
            100,
            15,
        ),
        {
            "slug": "streak_flawless",
            "title": "Без единой ошибки",
            "description": "Ответить правильно на все вопросы квиза без единой ошибки.",
            "icon_path": "img/achievements/streak_flawless.svg",
            "points_bonus": 30,
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
    main_completed = (
        TaskCompletion.objects.filter(user=user)
        .exclude(task__level__number__in=_NON_BLOCKING_LEVEL_NUMBERS)
        .count()
    )
    completed_by_level: dict[int, tuple[int, int]] = {}
    for level_number in Task.objects.values_list("level__number", flat=True).distinct():
        total_on_level = Task.objects.filter(level__number=level_number).count()
        done_on_level = TaskCompletion.objects.filter(
            user=user, task__level__number=level_number
        ).count()
        completed_by_level[level_number] = (done_on_level, total_on_level)
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
    achievements = Achievement.objects.filter(is_active=True).filter(
        Q(criterion_target__gt=0) | Q(criterion_kind=K.LEVEL_COMPLETED)
    ).order_by("criterion_target", "slug")
    for achievement in achievements:
        kind = achievement.criterion_kind
        target = achievement.criterion_target
        should_award = False
        if kind == K.LEVEL_COMPLETED:
            done, total = completed_by_level.get(target, (0, 0))
            should_award = total > 0 and done >= total
        elif kind == K.TASKS_COMPLETED:
            should_award = main_completed >= target
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
    try:
        from apps.users.certificate_services import issue_completion_certificate

        issue_completion_certificate(user, send_email=True)
    except Exception:  # noqa: BLE001
        logger.exception("Certificate issue after achievements failed for user_id=%s", user.pk)
    return awarded
