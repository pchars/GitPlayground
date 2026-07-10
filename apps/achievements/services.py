from django.contrib.auth.models import User
from django.db import transaction

from apps.achievements.models import Achievement, UserAchievement
from apps.progress.models import TaskCompletion
from apps.quiz.models import QuizQuestion, QuizQuestionProgress, QuizUserStats
from apps.tasks.models import Task
from apps.users.models import PointLedgerEntry, UserProfile

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


def bootstrap_default_achievements() -> None:
    total_tasks = max(1, Task.objects.count())
    total_quiz_questions = max(1, QuizQuestion.objects.count())
    easy_quiz_questions = max(1, QuizQuestion.objects.filter(difficulty=QuizQuestion.Difficulty.EASY).count())
    medium_quiz_questions = max(1, QuizQuestion.objects.filter(difficulty=QuizQuestion.Difficulty.MEDIUM).count())
    hard_quiz_questions = max(1, QuizQuestion.objects.filter(difficulty=QuizQuestion.Difficulty.HARD).count())
    K = Achievement.CriterionKind
    defaults = [
        {
            "slug": "first_commit",
            "title": "Первый коммит",
            "description": "Завершена первая задача.",
            "icon_path": "img/achievements/first_commit.svg",
            "points_bonus": 5,
            "threshold_tasks": 1,
            "criterion_kind": K.TASKS_COMPLETED,
            "criterion_target": 1,
        },
        {
            "slug": "first_steps_3",
            "title": "Три задачи",
            "description": "Завершено 3 задачи.",
            "icon_path": "img/achievements/journeyman_10.svg",
            "points_bonus": 8,
            "threshold_tasks": 3,
            "criterion_kind": K.TASKS_COMPLETED,
            "criterion_target": 3,
        },
        {
            "slug": "first_steps_5",
            "title": "Пять задач",
            "description": "Завершено 5 задач.",
            "icon_path": "img/achievements/journeyman_10.svg",
            "points_bonus": 10,
            "threshold_tasks": 5,
            "criterion_kind": K.TASKS_COMPLETED,
            "criterion_target": 5,
        },
        {
            "slug": "journeyman_10",
            "title": "Уверенный практик",
            "description": "Завершено 10 задач.",
            "icon_path": "img/achievements/journeyman_10.svg",
            "points_bonus": 15,
            "threshold_tasks": 10,
            "criterion_kind": K.TASKS_COMPLETED,
            "criterion_target": 10,
        },
        {
            "slug": "tasks_15",
            "title": "15 задач",
            "description": "Завершено 15 задач.",
            "icon_path": "img/achievements/journeyman_10.svg",
            "points_bonus": 12,
            "threshold_tasks": 15,
            "criterion_kind": K.TASKS_COMPLETED,
            "criterion_target": 15,
        },
        {
            "slug": "tasks_20",
            "title": "20 задач",
            "description": "Завершено 20 задач.",
            "icon_path": "img/achievements/journeyman_10.svg",
            "points_bonus": 14,
            "threshold_tasks": 20,
            "criterion_kind": K.TASKS_COMPLETED,
            "criterion_target": 20,
        },
        {
            "slug": "tasks_25",
            "title": "25 задач",
            "description": "Завершено 25 задач.",
            "icon_path": "img/achievements/journeyman_10.svg",
            "points_bonus": 16,
            "threshold_tasks": 25,
            "criterion_kind": K.TASKS_COMPLETED,
            "criterion_target": 25,
        },
        {
            "slug": "tasks_35",
            "title": "35 задач",
            "description": "Завершено 35 задач.",
            "icon_path": "img/achievements/journeyman_10.svg",
            "points_bonus": 18,
            "threshold_tasks": 35,
            "criterion_kind": K.TASKS_COMPLETED,
            "criterion_target": 35,
        },
        {
            "slug": "tasks_50",
            "title": "Полпути",
            "description": "Завершено 50 задач.",
            "icon_path": "img/achievements/journeyman_10.svg",
            "points_bonus": 22,
            "threshold_tasks": 50,
            "criterion_kind": K.TASKS_COMPLETED,
            "criterion_target": 50,
        },
        {
            "slug": "tasks_65",
            "title": "65 задач",
            "description": "Завершено 65 задач.",
            "icon_path": "img/achievements/journeyman_10.svg",
            "points_bonus": 28,
            "threshold_tasks": 65,
            "criterion_kind": K.TASKS_COMPLETED,
            "criterion_target": 65,
        },
        {
            "slug": "git_master",
            "title": "Git Master",
            "description": "Завершены все задачи курса.",
            "icon_path": "img/achievements/git_master.svg",
            "points_bonus": 50,
            "threshold_tasks": total_tasks,
            "criterion_kind": K.TASKS_COMPLETED,
            "criterion_target": total_tasks,
        },
        {
            "slug": "quiz_easy_complete",
            "title": "Легкий квиз закрыт",
            "description": "Решены все вопросы легкой сложности.",
            "icon_path": "img/achievements/quiz_easy_complete.svg",
            "points_bonus": 10,
            "threshold_tasks": easy_quiz_questions,
            "criterion_kind": K.QUIZ_EASY_SOLVED,
            "criterion_target": easy_quiz_questions,
        },
        {
            "slug": "quiz_medium_complete",
            "title": "Средний квиз закрыт",
            "description": "Решены все вопросы средней сложности.",
            "icon_path": "img/achievements/quiz_medium_complete.svg",
            "points_bonus": 15,
            "threshold_tasks": medium_quiz_questions,
            "criterion_kind": K.QUIZ_MEDIUM_SOLVED,
            "criterion_target": medium_quiz_questions,
        },
        {
            "slug": "quiz_hard_complete",
            "title": "Тяжелый квиз закрыт",
            "description": "Решены все вопросы тяжелой сложности.",
            "icon_path": "img/achievements/quiz_hard_complete.svg",
            "points_bonus": 20,
            "threshold_tasks": hard_quiz_questions,
            "criterion_kind": K.QUIZ_HARD_SOLVED,
            "criterion_target": hard_quiz_questions,
        },
        {
            "slug": "quiz_all_complete",
            "title": "Квиз-марафон",
            "description": "Решены все вопросы квиза.",
            "icon_path": "img/achievements/quiz_all_complete.svg",
            "points_bonus": 40,
            "threshold_tasks": total_quiz_questions,
            "criterion_kind": K.QUIZ_ALL_SOLVED,
            "criterion_target": total_quiz_questions,
        },
        {
            "slug": "quiz_25_solved",
            "title": "Квиз: 25",
            "description": "Правильно решено 25 вопросов квиза.",
            "icon_path": "img/achievements/quiz_easy_complete.svg",
            "points_bonus": 5,
            "threshold_tasks": 25,
            "criterion_kind": K.QUIZ_ALL_SOLVED,
            "criterion_target": 25,
        },
        {
            "slug": "quiz_50_solved",
            "title": "Квиз: 50",
            "description": "Правильно решено 50 вопросов квиза.",
            "icon_path": "img/achievements/quiz_easy_complete.svg",
            "points_bonus": 8,
            "threshold_tasks": 50,
            "criterion_kind": K.QUIZ_ALL_SOLVED,
            "criterion_target": 50,
        },
        {
            "slug": "quiz_100_solved",
            "title": "Квиз: 100",
            "description": "Правильно решено 100 вопросов квиза.",
            "icon_path": "img/achievements/quiz_medium_complete.svg",
            "points_bonus": 10,
            "threshold_tasks": 100,
            "criterion_kind": K.QUIZ_ALL_SOLVED,
            "criterion_target": 100,
        },
        {
            "slug": "quiz_200_solved",
            "title": "Квиз: 200",
            "description": "Правильно решено 200 вопросов квиза.",
            "icon_path": "img/achievements/quiz_medium_complete.svg",
            "points_bonus": 12,
            "threshold_tasks": 200,
            "criterion_kind": K.QUIZ_ALL_SOLVED,
            "criterion_target": 200,
        },
        {
            "slug": "quiz_350_solved",
            "title": "Квиз: 350",
            "description": "Правильно решено 350 вопросов квиза.",
            "icon_path": "img/achievements/quiz_hard_complete.svg",
            "points_bonus": 15,
            "threshold_tasks": 350,
            "criterion_kind": K.QUIZ_ALL_SOLVED,
            "criterion_target": 350,
        },
        {
            "slug": "quiz_500_solved",
            "title": "Квиз: 500",
            "description": "Правильно решено 500 вопросов квиза.",
            "icon_path": "img/achievements/quiz_hard_complete.svg",
            "points_bonus": 18,
            "threshold_tasks": 500,
            "criterion_kind": K.QUIZ_ALL_SOLVED,
            "criterion_target": 500,
        },
        {
            "slug": "streak_5",
            "title": "Серия 5",
            "description": "Серия из 5 правильных ответов подряд.",
            "icon_path": "img/achievements/streak_5.svg",
            "points_bonus": 5,
            "threshold_tasks": 5,
            "criterion_kind": K.STREAK_MIN,
            "criterion_target": 5,
        },
        {
            "slug": "streak_10",
            "title": "Серия 10",
            "description": "Серия из 10 правильных ответов подряд.",
            "icon_path": "img/achievements/streak_10.svg",
            "points_bonus": 10,
            "threshold_tasks": 10,
            "criterion_kind": K.STREAK_MIN,
            "criterion_target": 10,
        },
        {
            "slug": "streak_25",
            "title": "Серия 25",
            "description": "Серия из 25 правильных ответов подряд.",
            "icon_path": "img/achievements/streak_25.svg",
            "points_bonus": 15,
            "threshold_tasks": 25,
            "criterion_kind": K.STREAK_MIN,
            "criterion_target": 25,
        },
        {
            "slug": "streak_50",
            "title": "Серия 50",
            "description": "Серия из 50 правильных ответов подряд.",
            "icon_path": "img/achievements/streak_50.svg",
            "points_bonus": 20,
            "threshold_tasks": 50,
            "criterion_kind": K.STREAK_MIN,
            "criterion_target": 50,
        },
        {
            "slug": "streak_100",
            "title": "Серия 100",
            "description": "Серия из 100 правильных ответов подряд.",
            "icon_path": "img/achievements/streak_100.svg",
            "points_bonus": 25,
            "threshold_tasks": 100,
            "criterion_kind": K.STREAK_MIN,
            "criterion_target": 100,
        },
        {
            "slug": "streak_150",
            "title": "Серия 150",
            "description": "Серия из 150 правильных ответов подряд.",
            "icon_path": "img/achievements/streak_150.svg",
            "points_bonus": 30,
            "threshold_tasks": 150,
            "criterion_kind": K.STREAK_MIN,
            "criterion_target": 150,
        },
        {
            "slug": "streak_200",
            "title": "Серия 200",
            "description": "Серия из 200 правильных ответов подряд.",
            "icon_path": "img/achievements/streak_200.svg",
            "points_bonus": 35,
            "threshold_tasks": 200,
            "criterion_kind": K.STREAK_MIN,
            "criterion_target": 200,
        },
        {
            "slug": "streak_250",
            "title": "Серия 250",
            "description": "Серия из 250 правильных ответов подряд.",
            "icon_path": "img/achievements/streak_250.svg",
            "points_bonus": 40,
            "threshold_tasks": 250,
            "criterion_kind": K.STREAK_MIN,
            "criterion_target": 250,
        },
        {
            "slug": "streak_300",
            "title": "Серия 300",
            "description": "Серия из 300 правильных ответов подряд.",
            "icon_path": "img/achievements/streak_300.svg",
            "points_bonus": 50,
            "threshold_tasks": 300,
            "criterion_kind": K.STREAK_MIN,
            "criterion_target": 300,
        },
        {
            "slug": "streak_flawless",
            "title": "Безошибочный",
            "description": "Ответить правильно на все вопросы квиза без ошибок.",
            "icon_path": "img/achievements/streak_flawless.svg",
            "points_bonus": 60,
            "threshold_tasks": total_quiz_questions,
            "criterion_kind": K.STREAK_FLAWLESS,
            "criterion_target": total_quiz_questions,
        },
    ]
    for item in defaults:
        Achievement.objects.update_or_create(
            slug=item["slug"],
            defaults=item,
        )


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
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={"public_nickname": user.username},
    )
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
