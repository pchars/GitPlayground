from django.test import SimpleTestCase

from apps.core.services.command_policy import normalize_repo_relative_path


class NormalizeRepoRelativePathTests(SimpleTestCase):
    def test_accepts_simple_relative_paths(self):
        self.assertEqual(normalize_repo_relative_path("notes/todo.txt"), "notes/todo.txt")
        self.assertEqual(normalize_repo_relative_path("."), ".")

    def test_rejects_traversal_and_absolute_paths(self):
        self.assertIsNone(normalize_repo_relative_path("../etc/passwd"))
        self.assertIsNone(normalize_repo_relative_path("/etc/passwd"))
        self.assertIsNone(normalize_repo_relative_path("~/secret"))
