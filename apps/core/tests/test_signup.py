from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.core import mail
from django.test.utils import override_settings
from django.utils import timezone
from unittest.mock import patch

from apps.core.forms import PASSWORD_POLICY_MESSAGE
from apps.core.tests.helpers import signup_form_payload
from apps.users.models import UserProfile


class SignupViewTests(TestCase):
    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        SIGNUP_REQUIRE_EMAIL_CONFIRMATION=True,
    )
    def test_signup_valid_sends_activation_email_and_creates_inactive_user(self):
        client = Client()
        password = "x3$QwertySignup9zUnique"
        response = client.post(
            "/signup/",
            signup_form_payload(
                email="signup_new_user@example.com",
                password=password,
            ),
        )
        self.assertEqual(response.status_code, 200, response.content.decode("utf-8")[:500])
        user = User.objects.get(email="signup_new_user@example.com")
        self.assertEqual(user.username, "signup_new_user@example.com")
        self.assertTrue(user.check_password(password))
        self.assertFalse(user.is_active)
        profile = UserProfile.objects.get(user=user)
        self.assertEqual(profile.certificate_name, "Иван Иванов")
        self.assertEqual(profile.pseudonym, "ivan_dev")
        self.assertFalse(profile.marketing_opt_in)
        self.assertTrue(profile.privacy_consent_at)
        self.assertEqual(len(mail.outbox), 1)

    def test_signup_shows_field_errors_when_passwords_mismatch(self):
        client = Client()
        payload = signup_form_payload(
            email="bad@example.com",
            password="x3$QwertySignup9zUnique",
        )
        payload["password2"] = "other-password-9z"
        response = client.post("/signup/", payload)
        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8")
        self.assertIn("errorlist", body)

    def test_signup_shows_password_policy_message_for_weak_password(self):
        client = Client()
        response = client.post(
            "/signup/",
            signup_form_payload(
                email="weak@example.com",
                password="12345678",
                pseudonym="weak_user",
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(PASSWORD_POLICY_MESSAGE, response.content.decode("utf-8"))

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        SIGNUP_REQUIRE_EMAIL_CONFIRMATION=True,
    )
    def test_signup_rejects_duplicate_pseudonym(self):
        existing = User.objects.create_user(
            username="existing@example.com",
            password="x3$Pw9zUnique1",
            email="existing@example.com",
        )
        UserProfile.objects.create(
            user=existing,
            pseudonym="wanted",
            certificate_name="Existing User",
            learning_goal=UserProfile.LearningGoal.WORK,
            knowledge_level=UserProfile.KnowledgeLevel.BASIC,
            privacy_consent_at=timezone.now(),
            privacy_consent_version="2026-07-10",
            privacy_consent_text="ok",
        )
        client = Client()
        password = "x3$QwertySignup9zUnique"
        response = client.post(
            "/signup/",
            signup_form_payload(
                email="wanted_name@example.com",
                password=password,
                pseudonym="wanted",
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="wanted_name@example.com").exists())

    @override_settings(SIGNUP_REQUIRE_EMAIL_CONFIRMATION=True)
    @patch("apps.core.views.auth.send_mail", side_effect=RuntimeError("smtp down"))
    def test_signup_does_not_crash_when_email_send_fails(self, _mock_send_mail):
        client = Client()
        password = "x3$QwertySignup9zUnique"
        response = client.post(
            "/signup/",
            signup_form_payload(
                email="signup_mail_fail_user@example.com",
                password=password,
            ),
        )
        self.assertEqual(response.status_code, 200, response.content.decode("utf-8")[:500])
        user = User.objects.get(email="signup_mail_fail_user@example.com")
        self.assertFalse(user.is_active)
        self.assertTrue(UserProfile.objects.filter(user=user).exists())

    @override_settings(SIGNUP_REQUIRE_EMAIL_CONFIRMATION=False)
    def test_signup_without_confirmation_activates_and_logs_in_user(self):
        client = Client()
        password = "x3$QwertySignup9zUnique"
        response = client.post(
            "/signup/",
            signup_form_payload(
                email="signup_no_confirm_user@example.com",
                password=password,
            ),
            follow=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/profile/")
        user = User.objects.get(email="signup_no_confirm_user@example.com")
        self.assertTrue(user.is_active)
        self.assertTrue(UserProfile.objects.filter(user=user).exists())

    @override_settings(SIGNUP_REQUIRE_EMAIL_CONFIRMATION=False)
    def test_signup_stores_marketing_consent_when_opted_in(self):
        client = Client()
        password = "x3$QwertySignup9zUnique"
        client.post(
            "/signup/",
            signup_form_payload(
                email="marketing_user@example.com",
                password=password,
                marketing_opt_in=True,
            ),
        )
        profile = UserProfile.objects.get(user__email="marketing_user@example.com")
        self.assertTrue(profile.marketing_opt_in)
        self.assertIsNotNone(profile.marketing_consent_at)
        self.assertTrue(profile.marketing_consent_text)
