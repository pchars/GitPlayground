"""Auth activation, login, and password-reset flows."""

from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.core.tests.helpers import make_user, signup_form_payload


class ActivationAndLoginTests(TestCase):
    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        SIGNUP_REQUIRE_EMAIL_CONFIRMATION=True,
    )
    def test_activate_valid_token_activates_and_logs_in(self):
        client = Client()
        password = "x3$QwertyActivate9z"
        client.post(
            "/signup/",
            signup_form_payload(email="activate_ok@example.com", password=password, pseudonym="act_ok"),
        )
        user = User.objects.get(email="activate_ok@example.com")
        self.assertFalse(user.is_active)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        response = client.get(f"/activate/{uid}/{token}/")
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        # Session should be authenticated after activation.
        self.assertTrue("_auth_user_id" in client.session)

    def test_activate_invalid_token_returns_400(self):
        user = make_user(username="activate_bad@example.com", password="x3$QwertyActivate9z")
        user.is_active = False
        user.save(update_fields=["is_active"])
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        response = Client().get(f"/activate/{uid}/not-a-real-token/")
        self.assertEqual(response.status_code, 400)
        user.refresh_from_db()
        self.assertFalse(user.is_active)

    def test_login_success_and_wrong_password(self):
        make_user(username="login_user@example.com", password="x3$QwertyLogin9zOk")
        client = Client()
        bad = client.post(
            "/login/",
            {"username": "login_user@example.com", "password": "wrong-password"},
        )
        self.assertEqual(bad.status_code, 200)
        self.assertFalse(bad.wsgi_request.user.is_authenticated)

        ok = client.post(
            "/login/",
            {"username": "login_user@example.com", "password": "x3$QwertyLogin9zOk"},
        )
        self.assertEqual(ok.status_code, 302)
        self.assertTrue(client.login(username="login_user@example.com", password="x3$QwertyLogin9zOk"))

    def test_inactive_user_cannot_login(self):
        user = make_user(username="inactive@example.com", password="x3$QwertyLogin9zOk")
        user.is_active = False
        user.save(update_fields=["is_active"])
        client = Client()
        response = client.post(
            "/login/",
            {"username": "inactive@example.com", "password": "x3$QwertyLogin9zOk"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", client.session)


class PasswordResetFlowTests(TestCase):
    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_password_reset_email_and_confirm(self):
        user = make_user(username="reset_me@example.com", password="x3$QwertyOldPass9z")
        client = Client()
        response = client.post("/password-reset/", {"email": "reset_me@example.com"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        # Extract /reset/<uid>/<token>/ from email body.
        import re

        match = re.search(r"/reset/([^/\s]+)/([^/\s]+)/", body)
        self.assertIsNotNone(match, body[:400])
        uidb64, token = match.group(1), match.group(2)
        new_password = "x3$QwertyNewPass9z"
        get_form = client.get(f"/reset/{uidb64}/{token}/")
        self.assertEqual(get_form.status_code, 302)
        set_password_url = get_form["Location"]
        confirm = client.post(
            set_password_url,
            {"new_password1": new_password, "new_password2": new_password},
        )
        self.assertIn(confirm.status_code, {200, 302})
        user.refresh_from_db()
        self.assertTrue(user.check_password(new_password))
