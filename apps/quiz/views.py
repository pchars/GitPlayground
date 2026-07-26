from __future__ import annotations

import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.urls import reverse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.achievements.services import achievement_toast_payload, evaluate_achievements_for_user
from apps.quiz.models import QuizQuestion
from apps.quiz.services import (
    pick_question,
    quiz_home_context,
    record_quiz_answer,
    reset_quiz_progress,
    selected_difficulty,
)


def _redirect_quiz_play(difficulty: str) -> HttpResponse:
    valid = {value for value, _ in QuizQuestion.Difficulty.choices}
    if difficulty not in valid:
        difficulty = QuizQuestion.Difficulty.EASY
    allowlisted = {
        value: f"{reverse('quiz-play')}?difficulty={value}"
        for value, _ in QuizQuestion.Difficulty.choices
    }
    return redirect(allowlisted[difficulty])


def _push_achievement_messages(request: HttpRequest, awarded) -> None:
    for ua in awarded:
        payload = achievement_toast_payload(ua)
        messages.success(request, json.dumps(payload, ensure_ascii=False), extra_tags="achievement")


@login_required
def quiz_home(request: HttpRequest) -> HttpResponse:
    difficulty = selected_difficulty(request.session, request.GET.get("difficulty"))
    return render(request, "quiz/home.html", quiz_home_context(request.user, difficulty))


@login_required
@require_http_methods(["POST"])
def quiz_reset_progress(request: HttpRequest) -> HttpResponse:
    reset_quiz_progress(request.user, request.session)
    messages.success(request, "Прогресс квиза сброшен. Можно пройти вопросы заново.")
    return redirect("quiz-home")


@login_required
@require_http_methods(["GET", "POST"])
def quiz_play(request: HttpRequest) -> HttpResponse:
    selected = selected_difficulty(request.session, request.GET.get("difficulty"))
    count_q = QuizQuestion.objects.filter(difficulty=selected).count()
    if count_q == 0:
        messages.warning(request, "Для выбранной сложности пока нет вопросов.")
        return redirect("quiz-home")

    if request.method == "POST":
        qid = request.POST.get("question_id")
        choice = request.POST.get("choice")
        if not qid or choice is None or not str(choice).isdigit():
            messages.error(request, "Некорректный ответ.")
            return _redirect_quiz_play(selected)
        q = QuizQuestion.objects.filter(pk=int(qid)).first()
        if not q:
            messages.error(request, "Вопрос не найден.")
            return _redirect_quiz_play(selected)
        picked = int(choice)
        ok = record_quiz_answer(request.user, q, picked)
        selected = q.difficulty
        awarded = evaluate_achievements_for_user(request.user)
        _push_achievement_messages(request, awarded)
        choices = [
            (0, q.choice_0),
            (1, q.choice_1),
            (2, q.choice_2),
            (3, q.choice_3),
        ]
        feedback_text = "Верно" if ok else "Неверно."
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
                "selected_difficulty": selected,
                "difficulty_label": dict(QuizQuestion.Difficulty.choices).get(selected, ""),
            },
        )

    question = pick_question(request.user, request.session, selected)
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
            "selected_difficulty": selected,
            "difficulty_label": dict(QuizQuestion.Difficulty.choices).get(selected, ""),
        },
    )
