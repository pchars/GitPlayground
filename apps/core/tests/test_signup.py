from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.core import mail
from django.test.utils import override_settings

from apps.users.models import UserProfile


class SignupViewTests(TestCase):
    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_signup_valid_sends_activation_email_and_creates_inactive_user(self):
        client = Client()
        password = "x3$QwertySignup9zUnique"
        response = client.post(
            "/signup/",
            {
                "username": "signup_new_user",
                "email": "signup_new_user@example.com",
                "password1": password,
                "password2": password,
            },
        )
        self.assertEqual(response.status_code, 200, response.content.decode("utf-8")[:500])
        user = User.objects.get(username="signup_new_user")
        self.assertTrue(user.check_password(password))
        self.assertFalse(user.is_active)
        self.assertTrue(UserProfile.objects.filter(user=user).exists())
        self.assertEqual(len(mail.outbox), 1)

    def test_signup_shows_field_errors_when_passwords_mismatch(self):
        client = Client()
        response = client.post(
            "/signup/",
            {
                "username": "bad_signup_user",
                "email": "bad@example.com",
                "password1": "x3$QwertySignup9zUnique",
                "password2": "other-password-9z",
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8")
        self.assertIn("errorlist", body)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_signup_public_nickname_avoids_collision_with_existing_profile(self):
        existing = User.objects.create_user(username="u1", password="x3$Pw9zUnique1")
        UserProfile.objects.create(user=existing, public_nickname="wanted_name", total_points=0)
        client = Client()
        password = "x3$QwertySignup9zUnique"
        response = client.post(
            "/signup/",
            {
                "username": "wanted_name",
                "email": "wanted_name@example.com",
                "password1": password,
                "password2": password,
            },
        )
        self.assertEqual(response.status_code, 200, response.content.decode("utf-8")[:500])
        newbie = User.objects.get(username="wanted_name")
        profile = UserProfile.objects.get(user=newbie)
        self.assertNotEqual(profile.public_nickname, "wanted_name")
        self.assertIn(str(newbie.pk), profile.public_nickname)
