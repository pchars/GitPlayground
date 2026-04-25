from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from apps.quiz.models import QuizQuestion, QuizQuestionProgress, QuizUserStats
from apps.quiz.question_generator import iter_packed_questions, question_count


class QuizViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="quizzer", password="pass12345")
        self.q1 = QuizQuestion.objects.create(
            prompt="Тестовый вопрос?",
            choice_0="Неверно A",
            choice_1="Верно",
            choice_2="Неверно B",
            choice_3="Неверно C",
            explanation_0="Неверно. Этот вариант описывает другое действие. На самом деле команда делает другое.",
            explanation_1="Верно. Это корректный смысл команды.",
            explanation_2="Неверно. Этот вариант относится к другой команде.",
            explanation_3="Неверно. Это не то действие, которое делает команда.",
            correct_index=1,
            difficulty=QuizQuestion.Difficulty.EASY,
        )
        self.q2 = QuizQuestion.objects.create(
            prompt="Второй тестовый вопрос?",
            choice_0="Верно",
            choice_1="Неверно B",
            choice_2="Неверно C",
            choice_3="Неверно D",
            explanation_0="Верно. Это корректный смысл команды.",
            explanation_1="Неверно. Этот вариант относится к другой команде.",
            explanation_2="Неверно. Этот вариант относится к другой команде.",
            explanation_3="Неверно. Этот вариант относится к другой команде.",
            correct_index=0,
            difficulty=QuizQuestion.Difficulty.EASY,
        )

    def test_play_and_correct_answer_updates_stats(self):
        c = Client()
        self.assertTrue(c.login(username="quizzer", password="pass12345"))
        r = c.get(reverse("quiz-play"))
        self.assertEqual(r.status_code, 200)
        q = self.q1
        r2 = c.post(
            reverse("quiz-play"),
            {"question_id": str(q.id), "choice": "1"},
        )
        self.assertEqual(r2.status_code, 200)
        self.assertContains(r2, "Верно. Это корректный смысл команды.")
        stats = QuizUserStats.objects.get(user=self.user)
        self.assertEqual(stats.answered_total, 1)
        self.assertEqual(stats.correct_total, 1)
        self.assertEqual(stats.current_streak, 1)
        self.assertEqual(stats.best_streak, 1)

    def test_wrong_answer_resets_streak(self):
        QuizUserStats.objects.create(
            user=self.user, answered_total=1, correct_total=1, current_streak=3, best_streak=3
        )
        c = Client()
        self.assertTrue(c.login(username="quizzer", password="pass12345"))
        q = self.q1
        r = c.post(reverse("quiz-play"), {"question_id": str(q.id), "choice": "0"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Неверно. Этот вариант описывает другое действие.")
        stats = QuizUserStats.objects.get(user=self.user)
        self.assertEqual(stats.answered_total, 2)
        self.assertEqual(stats.correct_total, 1)
        self.assertEqual(stats.current_streak, 0)
        self.assertEqual(stats.best_streak, 3)

    def test_quiz_feedback_rendered_inline_not_toast(self):
        c = Client()
        self.assertTrue(c.login(username="quizzer", password="pass12345"))
        q = self.q1
        r = c.post(reverse("quiz-play"), {"question_id": str(q.id), "choice": "0"})
        self.assertEqual(r.status_code, 200)
        html = r.content.decode("utf-8")
        self.assertIn("quiz-inline-feedback", html)
        self.assertNotIn("Верно! Так держать.", html)

    def test_quiz_home_accepts_difficulty_filter(self):
        c = Client()
        self.assertTrue(c.login(username="quizzer", password="pass12345"))
        r = c.get(reverse("quiz-home"), {"difficulty": "easy"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Сложность")

    def test_quiz_home_does_not_show_manage_command_hint(self):
        QuizQuestion.objects.all().delete()
        c = Client()
        self.assertTrue(c.login(username="quizzer", password="pass12345"))
        r = c.get(reverse("quiz-home"))
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, "python manage.py")

    def test_generator_uses_human_friendly_command_prompts(self):
        prompts = [row["prompt"] for row in iter_packed_questions()]
        self.assertTrue(any("Что делает команда" in prompt for prompt in prompts))
        self.assertTrue(any("За что отвечает команда" in prompt for prompt in prompts))
        self.assertFalse(any("Что в основном делает команда" in prompt for prompt in prompts))

    def test_question_bank_contains_only_unique_prompts(self):
        prompts = [row["prompt"] for row in iter_packed_questions()]
        self.assertEqual(len(prompts), len(set(prompts)))
        self.assertGreaterEqual(question_count(), 300)

    def test_solved_question_does_not_repeat_and_failed_can_repeat(self):
        c = Client()
        self.assertTrue(c.login(username="quizzer", password="pass12345"))
        c.post(reverse("quiz-play"), {"question_id": str(self.q1.id), "choice": "1"})
        solved = QuizQuestionProgress.objects.get(user=self.user, question=self.q1)
        self.assertTrue(solved.solved)

        r = c.get(reverse("quiz-play"), {"difficulty": "easy"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["question"].id, self.q2.id)

        c.post(reverse("quiz-play"), {"question_id": str(self.q2.id), "choice": "1"})
        failed = QuizQuestionProgress.objects.get(user=self.user, question=self.q2)
        self.assertFalse(failed.solved)
        self.assertEqual(failed.failed_attempts, 1)

    def test_reset_progress_restores_all_questions(self):
        c = Client()
        self.assertTrue(c.login(username="quizzer", password="pass12345"))
        c.post(reverse("quiz-play"), {"question_id": str(self.q1.id), "choice": "1"})
        self.assertTrue(QuizQuestionProgress.objects.filter(user=self.user).exists())

        r = c.post(reverse("quiz-reset-progress"))
        self.assertEqual(r.status_code, 302)
        self.assertFalse(QuizQuestionProgress.objects.filter(user=self.user).exists())

        stats = QuizUserStats.objects.get(user=self.user)
        self.assertEqual(stats.answered_total, 0)
        self.assertEqual(stats.correct_total, 0)
