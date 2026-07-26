"""Quiz question selection, progress, and answer recording."""

from __future__ import annotations

import random
from collections import deque

from django.contrib.auth.models import User
from django.db import transaction

from apps.quiz.models import QuizQuestion, QuizQuestionProgress, QuizUserStats

SESSION_RECENT = "quiz_recent_ids"
SESSION_DIFFICULTY = "quiz_difficulty"
RECENT_MAX = 30


def recent_ids(session: dict) -> deque[int]:
    raw = session.get(SESSION_RECENT, [])
    return deque((int(x) for x in raw), maxlen=RECENT_MAX)


def store_recent(session: dict, qid: int) -> None:
    d = recent_ids(session)
    if qid in d:
        d.remove(qid)
    d.append(qid)
    session[SESSION_RECENT] = list(d)


def selected_difficulty(session: dict, get_difficulty: str | None) -> str:
    difficulty = get_difficulty or session.get(
        SESSION_DIFFICULTY,
        QuizQuestion.Difficulty.EASY,
    )
    valid = {value for value, _ in QuizQuestion.Difficulty.choices}
    if difficulty not in valid:
        difficulty = QuizQuestion.Difficulty.EASY
    session[SESSION_DIFFICULTY] = difficulty
    return difficulty


def pick_question(user: User, session: dict, difficulty: str) -> QuizQuestion | None:
    qs = QuizQuestion.objects.filter(difficulty=difficulty)
    if not qs.exists():
        return None
    solved_ids = QuizQuestionProgress.objects.filter(user=user, solved=True).values_list(
        "question_id",
        flat=True,
    )
    qs = qs.exclude(id__in=solved_ids)
    if not qs.exists():
        return None
    recent = set(recent_ids(session))
    pool = list(qs.exclude(id__in=recent).values_list("id", flat=True))
    if not pool:
        pool = list(qs.values_list("id", flat=True))
    pk = random.choice(pool)
    q = QuizQuestion.objects.get(pk=pk)
    store_recent(session, q.id)
    return q


def get_or_create_stats(user: User) -> QuizUserStats:
    stats, _ = QuizUserStats.objects.get_or_create(user=user)
    return stats


def quiz_home_context(user: User, difficulty: str) -> dict:
    total_q = QuizQuestion.objects.count()
    stats = get_or_create_stats(user) if total_q else None
    unresolved_total = 0
    unresolved_by_difficulty: list[tuple[str, str, int]] = []
    if total_q:
        solved_ids = QuizQuestionProgress.objects.filter(user=user, solved=True).values_list(
            "question_id",
            flat=True,
        )
        unresolved_qs = QuizQuestion.objects.exclude(id__in=solved_ids)
        unresolved_total = unresolved_qs.count()
        unresolved_by_difficulty = [
            (value, label, unresolved_qs.filter(difficulty=value).count())
            for value, label in QuizQuestion.Difficulty.choices
        ]
    return {
        "total_questions": total_q,
        "stats": stats,
        "selected_difficulty": difficulty,
        "difficulty_choices": QuizQuestion.Difficulty.choices,
        "difficulty_with_counts": [
            (value, label, QuizQuestion.objects.filter(difficulty=value).count())
            for value, label in QuizQuestion.Difficulty.choices
        ],
        "unresolved_total": unresolved_total,
        "unresolved_by_difficulty": unresolved_by_difficulty,
    }


def reset_quiz_progress(user: User, session: dict) -> None:
    QuizQuestionProgress.objects.filter(user=user).delete()
    QuizUserStats.objects.filter(user=user).update(
        answered_total=0,
        correct_total=0,
        current_streak=0,
        best_streak=0,
    )
    session[SESSION_RECENT] = []


def record_quiz_answer(user: User, question: QuizQuestion, picked: int) -> bool:
    """Update stats/progress for one answer. Returns whether the choice was correct."""
    ok = picked == question.correct_index
    with transaction.atomic():
        if not QuizUserStats.objects.filter(user=user).exists():
            QuizUserStats.objects.create(user=user)
        stats = QuizUserStats.objects.select_for_update().get(user=user)
        q_progress, _ = QuizQuestionProgress.objects.select_for_update().get_or_create(
            user=user,
            question=question,
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
    return ok
