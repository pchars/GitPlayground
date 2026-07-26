import tempfile

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.achievements.models import Achievement, UserAchievement
from apps.achievements.services import bootstrap_default_achievements
from apps.core.tests.helpers import make_user
from apps.users.certificate_pdf import build_certificate_pdf
from apps.users.certificate_services import (
    issue_completion_certificate,
    user_eligible_for_certificate,
)


class CertificatePdfTests(TestCase):
    def test_pdf_bytes_start_with_pdf_header(self):
        raw = build_certificate_pdf(
            display_name="Ivan Ivanov",
            issued_at=timezone.now(),
            verification_code="abc123xyz",
            verify_url="http://127.0.0.1:8000/certificate/verify/abc123xyz/",
        )
        self.assertTrue(raw.startswith(b"%PDF"))


class CertificateIssueTests(TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.user = make_user(username="cert_user@example.com", certificate_name="Cert User")
        bootstrap_default_achievements()
        for slug in ("git_master", "quiz_all_complete"):
            ach = Achievement.objects.get(slug=slug)
            UserAchievement.objects.get_or_create(user=self.user, achievement=ach)

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_eligible_when_both_achievements_present(self):
        self.assertTrue(user_eligible_for_certificate(self.user))

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPAGATES=True,
    )
    def test_issue_creates_pdf_and_sends_email_once(self):
        with self.settings(MEDIA_ROOT=self._tmpdir.name):
            cert = issue_completion_certificate(self.user, send_email=True)
            self.assertIsNotNone(cert)
            self.assertTrue(cert.pdf.name)
            self.assertEqual(len(mail.outbox), 1)
            self.assertEqual(len(mail.outbox[0].attachments), 1)
            self.assertTrue(mail.outbox[0].attachments[0][0].endswith(".pdf"))
            again = issue_completion_certificate(self.user, send_email=True)
            self.assertEqual(again.id, cert.id)
            self.assertEqual(len(mail.outbox), 1)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        CELERY_TASK_ALWAYS_EAGER=True,
    )
    def test_verify_and_download_pages(self):
        with self.settings(MEDIA_ROOT=self._tmpdir.name):
            cert = issue_completion_certificate(self.user, send_email=False)
            verify = self.client.get(
                reverse("certificate-verify", kwargs={"code": cert.verification_code})
            )
            self.assertEqual(verify.status_code, 200)
            self.assertContains(verify, "Cert User")
            self.assertContains(verify, "не является образовательной")

            self.client.force_login(self.user)
            download = self.client.get(reverse("certificate-download"))
            self.assertEqual(download.status_code, 200)
            self.assertEqual(download["Content-Type"], "application/pdf")
