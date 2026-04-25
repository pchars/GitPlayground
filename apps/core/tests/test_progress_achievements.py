from django.contrib.auth.models import User
from django.test import TestCase

from apps.achievements.models import Achievement, UserAchievement
from apps.achievements.services import bootstrap_default_achievements, evaluate_achievements_for_user
from apps.progress.models import TaskCompletion
from apps.quiz.models import QuizUserStats
from apps.tasks.models import Level, Task
from apps.users.models import UserProfile


class ProgressAndAchievementsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="achiever", password="password123")
        self.level = Level.objects.create(number=1, title="L1", slug="l1", description="d")
        self.task1 = Task.objects.create(
            external_id="1.1",
            slug="t1",
            title="T1",
            description="d",
            level=self.level,
            order=1,
            points=5,
        )
        UserProfile.objects.create(user=self.user, public_nickname="achiever", total_points=10)

    def test_bootstrap_default_achievements_is_idempotent(self):
        bootstrap_default_achievements()
        n1 = Achievement.objects.count()
        bootstrap_default_achievements()
        n2 = Achievement.objects.count()
        self.assertEqual(n1, n2)
        self.assertGreaterEqual(n1, 1)

    def test_task_completion_signal_awards_first_commit_achievement(self):
        bootstrap_default_achievements()
        ach = Achievement.objects.get(slug="first_commit")
        self.user.profile.refresh_from_db()
        before = self.user.profile.total_points
        TaskCompletion.objects.create(user=self.user, task=self.task1, points_awarded=5)
        self.user.profile.refresh_from_db()
        self.assertTrue(UserAchievement.objects.filter(user=self.user, achievement=ach).exists())
        self.assertGreaterEqual(self.user.profile.total_points, before + ach.points_bonus)

    def test_evaluate_achievements_does_not_double_award(self):
        bootstrap_default_achievements()
        TaskCompletion.objects.create(user=self.user, task=self.task1, points_awarded=5)
        evaluate_achievements_for_user(self.user)
        self.user.profile.refresh_from_db()
        pts = self.user.profile.total_points
        awarded_again = evaluate_achievements_for_user(self.user)
        self.assertEqual(awarded_again, [])
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.total_points, pts)

    def test_quiz_streak_achievement_is_awarded(self):
        bootstrap_default_achievements()
        QuizUserStats.objects.update_or_create(
            user=self.user,
            defaults={"best_streak": 12, "answered_total": 12, "correct_total": 12},
        )
        awarded = evaluate_achievements_for_user(self.user)
        slugs = {item.achievement.slug for item in awarded}
        self.assertIn("streak_5", slugs)
        self.assertIn("streak_10", slugs)
