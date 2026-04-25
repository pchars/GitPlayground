from django.contrib.auth.models import User
from django.test import Client, TestCase

from apps.core.services import (
    SANDBOX_TEXT_FILE_WRITE_MAX_BYTES,
    get_or_create_active_session,
    read_text_file_from_repo,
    run_command,
    write_text_file_to_repo,
)
from apps.tasks.models import Level, Task, TaskRevision
from apps.users.models import UserProfile


class SandboxFileToolsTests(TestCase):
    """Безопасное чтение/запись файлов в песочнице (без произвольного shell)."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="bob", password="password123")
        self.level = Level.objects.create(number=1, title="L1", slug="l1", description="d")
        self.task1 = Task.objects.create(
            external_id="1.1",
            slug="task-1-1",
            title="Task 1",
            description="desc",
            level=self.level,
            order=1,
            points=5,
        )
        TaskRevision.objects.create(
            task=self.task1,
            version=1,
            is_active=True,
            objective="Objective",
            steps=[],
            expected_state="",
            validator_notes="",
        )
        UserProfile.objects.create(user=self.user, public_nickname="bob", total_points=20)
        self.client.force_login(self.user)
        self.session = get_or_create_active_session(self.user, self.task1)

    def test_playground_page_includes_file_tool_urls(self):
        page = self.client.get("/playground/1_1/")
        self.assertEqual(page.status_code, 200)
        body = page.content.decode("utf-8")
        self.assertIn('readFile: "/playground/1_1/file/read/"', body)
        self.assertIn('writeFile: "/playground/1_1/file/write/"', body)
        self.assertIn("file-editor-path", body)

    def test_cat_reads_text_file(self):
        ok, _msg = write_text_file_to_repo(self.session, "notes/x.txt", "line1\nline2")
        self.assertTrue(ok)
        res = run_command(self.session, "cat notes/x.txt")
        self.assertEqual(res.return_code, 0)
        self.assertIn("line1", res.output)
        self.assertIn("line2", res.output)

    def test_cat_rejects_flags(self):
        res = run_command(self.session, "cat -n README_TASK.txt")
        self.assertEqual(res.return_code, 126)

    def test_cat_rejects_path_escape(self):
        res = run_command(self.session, "cat ../../../manage.py")
        self.assertEqual(res.return_code, 126)

    def test_arbitrary_shell_still_blocked(self):
        for cmd in (
            'python -c "print(1)"',
            "bash -c echo",
            "powershell Write-Host hi",
            "sh -c id",
            "cmd /c dir",
        ):
            with self.subTest(cmd=cmd):
                res = run_command(self.session, cmd)
                self.assertEqual(res.return_code, 126, msg=res.output)

    def test_read_file_api_success(self):
        write_text_file_to_repo(self.session, "api_read.txt", "hello-api")
        r = self.client.get("/playground/1_1/file/read/", {"path": "api_read.txt"})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["content"], "hello-api")

    def test_read_file_api_rejects_escape(self):
        r = self.client.get("/playground/1_1/file/read/", {"path": "../../../manage.py"})
        self.assertEqual(r.status_code, 400)
        self.assertFalse(r.json()["ok"])

    def test_write_file_api_then_readable(self):
        w = self.client.post(
            "/playground/1_1/file/write/",
            {"path": "deep/w.txt", "content": "saved\n"},
        )
        self.assertEqual(w.status_code, 200)
        self.assertTrue(w.json()["ok"])
        ok, text, _ = read_text_file_from_repo(self.session, "deep/w.txt")
        self.assertTrue(ok)
        self.assertEqual(text.strip(), "saved")

    def test_write_file_api_rejects_null_byte(self):
        w = self.client.post(
            "/playground/1_1/file/write/",
            {"path": "bad.bin", "content": "a\x00b"},
        )
        self.assertEqual(w.status_code, 400)
        self.assertIn("Null", w.json()["message"])

    def test_write_file_api_rejects_oversized_body(self):
        huge = "x" * (SANDBOX_TEXT_FILE_WRITE_MAX_BYTES + 1)
        w = self.client.post("/playground/1_1/file/write/", {"path": "big.txt", "content": huge})
        self.assertEqual(w.status_code, 400)
        self.assertFalse(w.json()["ok"])

    def test_file_endpoints_require_login(self):
        self.client.logout()
        self.assertEqual(self.client.get("/playground/1_1/file/read/", {"path": "x"}).status_code, 302)
        self.assertEqual(
            self.client.post("/playground/1_1/file/write/", {"path": "x", "content": "y"}).status_code,
            302,
        )
