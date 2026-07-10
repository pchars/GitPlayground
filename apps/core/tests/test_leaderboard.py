from datetime import timedelta

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.utils import timezone

from apps.core.tests.helpers import make_user
from apps.progress.models import LeaderboardSnapshot
from apps.users.legal import PRIVACY_CONSENT_SNAPSHOT, PRIVACY_POLICY_VERSION
from apps.users.models import UserProfile


def _legacy_profile(user, *, pseudonym: str, points: int) -> UserProfile:
    return UserProfile.objects.create(
        user=user,
        pseudonym=pseudonym,
        certificate_name="Test User",
        learning_goal=UserProfile.LearningGoal.INTEREST,
        knowledge_level=UserProfile.KnowledgeLevel.BASIC,
        total_points=points,
        privacy_consent_at=timezone.now(),
        privacy_consent_version=PRIVACY_POLICY_VERSION,
        privacy_consent_text=PRIVACY_CONSENT_SNAPSHOT,
    )


class LeaderboardViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.viewer = make_user(username="viewer", points=5)
        self.client.force_login(self.viewer)

    def test_live_ranking_when_no_snapshot(self):
        alpha = make_user(username="alpha", points=100)
        beta = make_user(username="beta", points=50)
        response = self.client.get("/leaderboard/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["snapshot_mode"])
        ranks = [row["pseudonym"] for row in response.context["top_users"]]
        self.assertEqual(ranks[0], alpha.profile.pseudonym)
        self.assertIn(beta.profile.pseudonym, ranks)

    def test_snapshot_mode_uses_latest_capture(self):
        user = User.objects.create_user(username="snap_user", password="pw")
        _legacy_profile(user, pseudonym="Snap", points=42)
        newer = LeaderboardSnapshot.objects.create(user=user, rank=1, total_points=42)
        older = LeaderboardSnapshot.objects.create(user=user, rank=99, total_points=1)
        now = timezone.now()
        LeaderboardSnapshot.objects.filter(pk=newer.pk).update(captured_at=now)
        LeaderboardSnapshot.objects.filter(pk=older.pk).update(captured_at=now - timedelta(days=1))
        response = self.client.get("/leaderboard/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["snapshot_mode"])
        self.assertEqual(len(response.context["top_users"]), 1)
        self.assertEqual(response.context["top_users"][0]["rank"], 1)
        self.assertEqual(response.context["top_users"][0]["total_points"], 42)

    def test_page_uses_russian_leaderboard_title(self):
        response = self.client.get("/leaderboard/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertIn("Таблица лидеров", html)
        self.assertNotIn(">Лидерборд<", html)
        self.assertIn("Полный рейтинг", html)

    def test_solo_podium_has_single_place_class(self):
        user = User.objects.create_user(username="solo", password="pw")
        _legacy_profile(user, pseudonym="Solo", points=10)
        LeaderboardSnapshot.objects.create(user=user, rank=1, total_points=10)
        response = self.client.get("/leaderboard/")
        self.assertContains(response, 'podium-count-1')
