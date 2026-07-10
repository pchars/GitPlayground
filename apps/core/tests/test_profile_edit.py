from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.utils import timezone

from apps.core.tests.helpers import make_user
from apps.users.legal import MARKETING_CONSENT_VERSION
from apps.users.models import UserProfile


class ProfileEditTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user(username="editor", pseudonym="editor1", certificate_name="Editor User")
        self.client.force_login(self.user)

    def test_profile_edit_updates_knowledge_level_and_email(self):
        response = self.client.post(
            "/profile/edit/",
            {
                "certificate_name": "Editor User",
                "pseudonym": "editor1",
                "email": "newmail@example.com",
                "learning_goal": UserProfile.LearningGoal.WORK,
                "knowledge_level": UserProfile.KnowledgeLevel.ADVANCED,
                "job_role": "Team Lead",
                "company_name": "",
                "marketing_opt_in": "on",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        profile = self.user.profile
        profile.refresh_from_db()
        self.assertEqual(self.user.email, "newmail@example.com")
        self.assertEqual(profile.knowledge_level, UserProfile.KnowledgeLevel.ADVANCED)
        self.assertEqual(profile.job_role, "Team Lead")
        self.assertTrue(profile.marketing_opt_in)
        self.assertEqual(profile.marketing_consent_version, MARKETING_CONSENT_VERSION)

    def test_profile_edit_requires_login(self):
        self.client.logout()
        response = self.client.get("/profile/edit/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])
