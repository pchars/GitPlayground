import unittest.mock
from django.test import Client, TestCase, override_settings

from apps.core.tests.helpers import make_user
from apps.tasks.models import Level, Task, TaskAsset, TheoryBlock
from apps.quiz.models import QuizQuestion


class PagesRegressionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user(
            username="page_owner",
            password="password123",
            certificate_name="Page Owner Example",
            pseudonym="page_owner",
            points=10,
        )
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
        for url in ("/", "/login/", "/signup/", "/healthz/", "/admin/login/?next=/admin/", "/legal/privacy/", "/support/donate/"):
            response = self.client.get(url)
            self.assertNotEqual(response.status_code, 500, url)

    def test_landing_contains_git_learning_sections_and_stats(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertIn("landing-hero-full", html)
        self.assertNotIn("Что такое Git", html)
        self.assertIn("Git в реальной работе", html)
        self.assertIn("Командная работа", html)
        self.assertIn("Infrastructure as Code", html)
        self.assertNotIn("Четыре шага от теории", html)
        self.assertNotIn("data-learning-prev", html)
        self.assertIn("learning-flow", html)
        self.assertIn('role="tablist"', html)
        self.assertNotIn("learning-slider-dot", html)
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
            "/profile/edit/",
            "/tasks/",
            "/theory/1/",
            "/quiz/",
            "/quiz/play/?difficulty=easy",
            "/leaderboard/",
            "/playground/gh-1_1/",
        )
        for url in urls:
            response = self.client.get(url)
            self.assertNotEqual(response.status_code, 500, url)
            self.assertNotIn("manage.py", response.content.decode("utf-8"))

    def test_profile_is_private_for_guests_and_other_users(self):
        response = self.client.get("/profile/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

        other = make_user(username="other_user", pseudonym="other")
        self.client.force_login(other)
        response = self.client.get(f"/profile/{self.user.username}/")
        self.assertEqual(response.status_code, 404)

    def test_profile_self_renders_for_owner(self):
        self.client.force_login(self.user)
        response = self.client.get("/profile/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertIn("Информация о пользователе", html)
        self.assertIn("Page Owner Example", html)
        self.assertIn("page_owner@example.com", html)

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
        response = self.client.get("/profile/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertIn("Информация о пользователе", html)
        self.assertIn("Прогресс по обучению", html)
        self.assertIn("profile-level-list", html)
        self.assertIn("Достижения", html)
        self.assertIn("Редактировать профиль", html)
        self.assertNotIn("Ср. попыток", html)
        self.assertNotIn("<h3>Профиль</h3>", html)
        self.assertNotIn("Учебная аналитика", html)
        self.assertNotIn("Последние действия", html)
        self.assertNotIn("Топ-10", html)

    def test_theory_index_shows_book_toc(self):
        self.client.force_login(self.user)
        response = self.client.get("/theory/1/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertIn("theory-book", html)
        self.assertIn("Оглавление", html)
        self.assertIn("Обзор уровня", html)
        self.assertIn("/theory/1/overview/", html)
        self.assertNotIn("theory-content-card", html)

    def test_theory_article_page_renders_overview(self):
        self.client.force_login(self.user)
        response = self.client.get("/theory/1/overview/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertIn("theory-article", html)
        self.assertIn("Обзор уровня", html)
        self.assertIn("← Оглавление", html)
        self.assertIn("theory-text", html)

    def test_tasks_page_collapses_all_levels_by_default(self):
        import re

        self.client.force_login(self.user)
        response = self.client.get("/tasks/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertIn("tasks-levels-hint", html)
        self.assertIn("task-card-index", html)
        self.assertIn("level-theory-link", html)
        self.assertNotIn("level-summary-theory-link", html)
        self.assertIsNone(re.search(r"<details[^>]*\bopen\b", html))

    def test_tasks_by_level_page_opens_selected_level(self):
        import re

        self.client.force_login(self.user)
        response = self.client.get("/tasks/level/1/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        details_tag = re.search(r"<details\s[^>]*task-level-accordion[^>]*>", html, re.DOTALL)
        self.assertIsNotNone(details_tag)
        self.assertIn("open", details_tag.group(0))

    def test_playground_page_has_no_internal_subtitle_or_validator_copy(self):
        self.client.force_login(self.user)
        response = self.client.get("/playground/gh-1_1/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertNotIn("Режим обучения", html)
        self.assertNotIn("validator.py", html)
        self.assertNotIn("terminal-log-data", html)
        self.assertNotIn("Подсказок доступно", html)
        self.assertNotIn("баллов</p>", html)
        self.assertIn("terminal_paste.js", html)
        self.assertIn("playground-workspace", html)

    def test_footer_contains_privacy_policy_link(self):
        response = self.client.get("/")
        html = response.content.decode("utf-8")
        self.assertIn("Политика конфиденциальности", html)
        self.assertIn("Поддержать проект", html)

    def test_support_donate_page_shows_wallet(self):
        response = self.client.get("/support/donate/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertIn("Поддержать проект", html)
        self.assertIn("donation-wallet", html)
        self.assertIn("legal.css", html)

    def test_base_template_includes_favicon_links(self):
        response = self.client.get("/")
        html = response.content.decode("utf-8")
        self.assertIn("favicon.ico", html)
        self.assertIn("logo.svg", html)

    @override_settings(DEBUG=False)
    def test_static_assets_served_when_debug_disabled(self):
        response = self.client.get("/static/css/common.css")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/css", response["Content-Type"])

    @override_settings(DEBUG=False)
    def test_custom_404_page_when_debug_disabled(self):
        response = self.client.get("/this-route-does-not-exist/")
        self.assertEqual(response.status_code, 404)
        html = response.content.decode("utf-8")
        self.assertIn("Страница не найдена", html)
        self.assertIn("error.css", html)
        self.assertIn("common.css", html)
        self.assertIn("site-footer", html)
        self.assertIn("page-error", html)

    def test_error_handlers_render_full_chrome(self):
        from apps.core.views.errors import bad_request, page_not_found, permission_denied, server_error

        cases = [
            (bad_request, 400, "Некорректный запрос", True),
            (permission_denied, 403, "Доступ запрещён", True),
            (page_not_found, 404, "Страница не найдена", True),
            (server_error, 500, "Что-то пошло не так", False),
        ]
        for handler, status, title, passes_exception in cases:
            with self.subTest(status=status):
                request = self.client.get("/").wsgi_request
                if passes_exception:
                    response = handler(request, Exception("probe"))
                else:
                    response = handler(request)
                self.assertEqual(response.status_code, status)
                html = response.content.decode("utf-8")
                self.assertIn(title, html)
                self.assertIn("error.css", html)
                self.assertIn("common.css", html)
                self.assertIn("responsive.css", html)
                self.assertIn("site-footer", html)
                self.assertIn("GitPlayground", html)
                self.assertIn("page-error", html)

    def test_playground_sandbox_unavailable_returns_styled_503(self):
        self.client.force_login(self.user)
        with (
            unittest.mock.patch(
                "apps.core.views.playground.get_or_create_active_session",
                side_effect=RuntimeError("Docker sandbox runtime is required but unavailable."),
            ),
            unittest.mock.patch("apps.core.views.playground.log_exception"),
        ):
            response = self.client.get("/playground/gh-1_1/")
        self.assertEqual(response.status_code, 503)
        html = response.content.decode("utf-8")
        self.assertIn("Песочница недоступна", html)
        self.assertIn("Песочница временно недоступна", html)
        self.assertIn("error.css", html)
        self.assertIn("common.css", html)
