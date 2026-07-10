from django.contrib.auth.models import User
from django.test import Client, TestCase

from apps.tasks.models import Level, Task, TaskAsset, TheoryBlock
from apps.users.models import UserProfile
from apps.quiz.models import QuizQuestion


class PagesRegressionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="Mikhail", password="password123", email="mikhail@example.com")
        UserProfile.objects.create(user=self.user, public_nickname="Mikhail", total_points=10)
        self.level = Level.objects.create(number=1, title="Основы", slug="osnovy", description="d")
        TheoryBlock.objects.create(level=self.level, title="Теория", content_md="## Раздел\nТекст", diagram_mermaid="")
        self.task = Task.objects.create(
            external_id="gh-1.1",
            slug="github_repo_init",
            title="GitHub Repo Init",
            description="desc",
            level=self.level,
            platform=Task.Platform.GITHUB,
            order=1,
            points=5,
        )
        TaskAsset.objects.create(
            task=self.task,
            asset_type=TaskAsset.AssetType.HINT,
            path="hints/hint1.txt",
            sort_order=1,
            content="Hint",
        )
        QuizQuestion.objects.create(
            prompt="Q?",
            choice_0="A",
            choice_1="B",
            choice_2="C",
            choice_3="D",
            correct_index=0,
            difficulty=QuizQuestion.Difficulty.EASY,
        )

    def test_public_pages_do_not_error(self):
        for url in ("/", "/login/", "/signup/", "/healthz/", "/admin/login/?next=/admin/"):
            response = self.client.get(url)
            self.assertNotEqual(response.status_code, 500, url)

    def test_landing_contains_git_learning_sections_and_stats(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertIn("landing-hero-full", html)
        self.assertIn("Что такое Git", html)
        self.assertIn("Почему важно учить Git", html)
        self.assertIn("Где используется Git", html)
        self.assertIn("вопросов для закрепления", html)
        self.assertNotIn("учеников уже решили хотя бы одну задачу", html)
        self.assertNotIn("пользователей на платформе", html)
        self.assertNotIn("landing-stats", html)
        self.assertIn("Готов прокачать Git на практике?", html)
        self.assertIn("learning-slider", html)
        self.assertIn("landing_slider.js", html)
        self.assertNotIn("Текущий трек включает", html)

    def test_authenticated_pages_do_not_error(self):
        self.client.force_login(self.user)
        urls = (
            "/profile/",
            "/tasks/",
            "/theory/1/",
            "/quiz/",
            "/quiz/play/?difficulty=easy",
            "/leaderboard/",
            f"/profile/{self.user.username}/",
            "/playground/gh-1_1/",
        )
        for url in urls:
            response = self.client.get(url)
            self.assertNotEqual(response.status_code, 500, url)
            self.assertNotIn("manage.py", response.content.decode("utf-8"))

    def test_profile_self_redirects_to_public_profile(self):
        self.client.force_login(self.user)
        response = self.client.get("/profile/")
        self.assertEqual(response.status_code, 302)
        self.assertIn(f"/profile/{self.user.username}/", response["Location"])

    def test_header_uses_my_profile_and_sidebar_has_no_profile_link(self):
        self.client.force_login(self.user)
        response = self.client.get("/tasks/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertIn("Мой профиль", html)
        self.assertIn(">Теория</a>", html)
        self.assertIn(">Задачи</a>", html)
        self.assertIn(">Квиз</a>", html)
        self.assertIn(">Таблица лидеров</a>", html)
        self.assertNotIn("sidebar-nav", html)
        self.assertNotIn("theme-toggle", html)

    def test_profile_contains_learning_sections_without_top10(self):
        self.client.force_login(self.user)
        response = self.client.get(f"/profile/{self.user.username}/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertIn("Информация о пользователе", html)
        self.assertIn("Прогресс по обучению", html)
        self.assertIn("profile-level-list", html)
        self.assertIn("Достижения", html)
        self.assertIn("Login", html)
        self.assertIn("Баллы", html)
        self.assertNotIn("Ср. попыток", html)
        self.assertNotIn("<h3>Профиль</h3>", html)
        self.assertNotIn("Учебная аналитика", html)
        self.assertNotIn("Последние действия", html)
        self.assertNotIn("Топ-10", html)

    def test_theory_page_prefers_database_content_over_builtin_fallback(self):
        self.client.force_login(self.user)
        response = self.client.get("/theory/1/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertIn("Раздел", html)
        self.assertIn("theory-hero-inner", html)
        self.assertIn("scroll-top-btn", html)
        self.assertIn("scroll_top.js", html)
        self.assertNotIn("theory-pager-level", html)
        self.assertNotIn("theory.js", html)
        self.assertNotIn("Углубленная теория перед практикой", html)

    def test_playground_page_has_no_internal_subtitle_or_validator_copy(self):
        self.client.force_login(self.user)
        response = self.client.get("/playground/gh-1_1/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertNotIn("Режим обучения", html)
        self.assertNotIn("validator.py", html)
        self.assertNotIn("terminal-log-data", html)
        self.assertIn("terminal_paste.js", html)
