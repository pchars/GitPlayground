from __future__ import annotations

import json
import random
from functools import lru_cache
from collections import deque

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.db import transaction
from django.db.utils import DatabaseError
from django.http import HttpRequest, HttpResponse
from django.urls import reverse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.achievements.services import evaluate_achievements_for_user
from .models import QuizQuestion, QuizQuestionProgress, QuizUserStats

SESSION_RECENT = "quiz_recent_ids"
SESSION_DIFFICULTY = "quiz_difficulty"
RECENT_MAX = 30


@lru_cache(maxsize=8)
def _quiz_has_difficulty_column() -> bool:
    try:
        with connection.cursor() as cursor:
            columns = connection.introspection.get_table_description(cursor, QuizQuestion._meta.db_table)
        return any(col.name == "difficulty" for col in columns)
    except DatabaseError:
        return False


def _recent_ids(request: HttpRequest) -> deque[int]:
    raw = request.session.get(SESSION_RECENT, [])
    return deque((int(x) for x in raw), maxlen=RECENT_MAX)


def _store_recent(request: HttpRequest, qid: int) -> None:
    d = _recent_ids(request)
    if qid in d:
        d.remove(qid)
    d.append(qid)
    request.session[SESSION_RECENT] = list(d)


def _selected_difficulty(request: HttpRequest) -> str:
    if not _quiz_has_difficulty_column():
        return QuizQuestion.Difficulty.EASY
    difficulty = request.GET.get("difficulty") or request.session.get(
        SESSION_DIFFICULTY,
        QuizQuestion.Difficulty.EASY,
    )
    valid = {value for value, _ in QuizQuestion.Difficulty.choices}
    if difficulty not in valid:
        difficulty = QuizQuestion.Difficulty.EASY
    request.session[SESSION_DIFFICULTY] = difficulty
    return difficulty


def _pick_question(request: HttpRequest, difficulty: str) -> QuizQuestion | None:
    if _quiz_has_difficulty_column():
        qs = QuizQuestion.objects.filter(difficulty=difficulty)
    else:
        qs = QuizQuestion.objects.all()
    if not qs.exists():
        return None
    solved_ids = QuizQuestionProgress.objects.filter(user=request.user, solved=True).values_list(
        "question_id",
        flat=True,
    )
    qs = qs.exclude(id__in=solved_ids)
    if not qs.exists():
        return None
    recent = set(_recent_ids(request))
    pool = list(qs.exclude(id__in=recent).values_list("id", flat=True))
    if not pool:
        pool = list(qs.values_list("id", flat=True))
    pk = random.choice(pool)
    q = QuizQuestion.objects.get(pk=pk)
    _store_recent(request, q.id)
    return q


def _get_or_create_stats(user) -> QuizUserStats:
    stats, _ = QuizUserStats.objects.get_or_create(user=user)
    return stats


def _push_achievement_messages(request: HttpRequest, awarded) -> None:
    for ua in awarded:
        payload = {
            "icon": ua.achievement.icon_path,
            "title": ua.achievement.title,
            "description": ua.achievement.description,
        }
        messages.success(request, json.dumps(payload, ensure_ascii=False), extra_tags="achievement")


@login_required
def quiz_home(request: HttpRequest) -> HttpResponse:
    total_q = QuizQuestion.objects.count()
    selected_difficulty = _selected_difficulty(request)
    stats = None
    if total_q:
        stats = _get_or_create_stats(request.user)
    unresolved_total = 0
    unresolved_by_difficulty: list[tuple[str, str, int]] = []
    if total_q:
        solved_ids = QuizQuestionProgress.objects.filter(user=request.user, solved=True).values_list(
            "question_id",
            flat=True,
        )
        unresolved_qs = QuizQuestion.objects.exclude(id__in=solved_ids)
        unresolved_total = unresolved_qs.count()
        unresolved_by_difficulty = (
            [
                (value, label, unresolved_qs.filter(difficulty=value).count())
                for value, label in QuizQuestion.Difficulty.choices
            ]
            if _quiz_has_difficulty_column()
            else [(QuizQuestion.Difficulty.EASY, "Легкий", unresolved_total)]
        )
    return render(
        request,
        "quiz/home.html",
        {
            "total_questions": total_q,
            "stats": stats,
            "selected_difficulty": selected_difficulty,
            "difficulty_choices": QuizQuestion.Difficulty.choices,
            "difficulty_with_counts": (
                [
                    (value, label, QuizQuestion.objects.filter(difficulty=value).count())
                    for value, label in QuizQuestion.Difficulty.choices
                ]
                if _quiz_has_difficulty_column()
                else [(QuizQuestion.Difficulty.EASY, "Легкий", total_q)]
            ),
            "unresolved_total": unresolved_total,
            "unresolved_by_difficulty": unresolved_by_difficulty,
        },
    )


@login_required
@require_http_methods(["POST"])
def quiz_reset_progress(request: HttpRequest) -> HttpResponse:
    QuizQuestionProgress.objects.filter(user=request.user).delete()
    QuizUserStats.objects.filter(user=request.user).update(
        answered_total=0,
        correct_total=0,
        current_streak=0,
        best_streak=0,
    )
    request.session[SESSION_RECENT] = []
    messages.success(request, "Прогресс квиза сброшен. Можно пройти вопросы заново.")
    return redirect("quiz-home")


@login_required
@require_http_methods(["GET", "POST"])
def quiz_play(request: HttpRequest) -> HttpResponse:
    selected_difficulty = _selected_difficulty(request)
    count_q = (
        QuizQuestion.objects.filter(difficulty=selected_difficulty).count()
        if _quiz_has_difficulty_column()
        else QuizQuestion.objects.count()
    )
    if count_q == 0:
        messages.warning(
            request,
            "Для выбранной сложности пока нет вопросов.",
        )
        return redirect("quiz-home")

    if request.method == "POST":
        qid = request.POST.get("question_id")
        choice = request.POST.get("choice")
        if not qid or choice is None or not str(choice).isdigit():
            messages.error(request, "Некорректный ответ.")
            return redirect(f"{reverse('quiz-play')}?difficulty={selected_difficulty}")
        q = QuizQuestion.objects.filter(pk=int(qid)).first()
        if not q:
            messages.error(request, "Вопрос не найден.")
            return redirect(f"{reverse('quiz-play')}?difficulty={selected_difficulty}")
        picked = int(choice)
        ok = picked == q.correct_index
        selected_difficulty = q.difficulty if _quiz_has_difficulty_column() else selected_difficulty
        with transaction.atomic():
            if not QuizUserStats.objects.filter(user=request.user).exists():
                QuizUserStats.objects.create(user=request.user)
            stats = QuizUserStats.objects.select_for_update().get(user=request.user)
            q_progress, _ = QuizQuestionProgress.objects.select_for_update().get_or_create(
                user=request.user,
                question=q,
            )
            stats.answered_total += 1
            q_progress.attempts_total += 1
            if ok:
                stats.correct_total += 1
                stats.current_streak += 1
                if stats.current_streak > stats.best_streak:
                    stats.best_streak = stats.current_streak
                q_progress.solved = True
            else:
                stats.current_streak = 0
                q_progress.failed_attempts += 1
            q_progress.save(update_fields=["attempts_total", "failed_attempts", "solved", "updated_at"])
            stats.save(
                update_fields=[
                    "answered_total",
                    "correct_total",
                    "current_streak",
                    "best_streak",
                    "updated_at",
                ]
            )
        awarded = evaluate_achievements_for_user(request.user)
        _push_achievement_messages(request, awarded)
        choices = [
            (0, q.choice_0),
            (1, q.choice_1),
            (2, q.choice_2),
            (3, q.choice_3),
        ]
        picked_explanation = getattr(q, f"explanation_{picked}", "") or ""
        correct_label = [q.choice_0, q.choice_1, q.choice_2, q.choice_3][q.correct_index]
        fallback = (
            "Верно, это корректный вариант."
            if ok
            else f"Неверно, потому что правильный вариант: {correct_label}."
        )
        feedback_text = picked_explanation or fallback
        return render(
            request,
            "quiz/play.html",
            {
                "question": q,
                "choices": choices,
                "selected_choice": picked,
                "submitted": True,
                "is_correct": ok,
                "feedback_text": feedback_text,
                "correct_label": correct_label,
                "selected_difficulty": selected_difficulty,
                "difficulty_label": dict(QuizQuestion.Difficulty.choices).get(selected_difficulty, ""),
            },
        )

    question = _pick_question(request, selected_difficulty)
    if not question:
        messages.success(request, "Вы завершили все вопросы на этой сложности.")
        return redirect("quiz-home")
    choices = [
        (0, question.choice_0),
        (1, question.choice_1),
        (2, question.choice_2),
        (3, question.choice_3),
    ]
    return render(
        request,
        "quiz/play.html",
        {
            "question": question,
            "choices": choices,
            "selected_difficulty": selected_difficulty,
            "difficulty_label": dict(QuizQuestion.Difficulty.choices).get(selected_difficulty, ""),
        },
    )
