from pathlib import Path
import tempfile
import unittest

from django.test import TestCase

from gitplayground.env import load_env_file


class EnvLoaderTests(TestCase):
    def test_load_env_file_overrides_existing_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text(
                "DJANGO_DEBUG=true\nEXISTING_KEY=from_file\n",
                encoding="utf-8",
            )
            with unittest.mock.patch.dict("os.environ", {"EXISTING_KEY": "preset"}, clear=False):
                load_env_file(env_path)
                self.assertEqual(__import__("os").environ.get("DJANGO_DEBUG"), "true")
                self.assertEqual(__import__("os").environ.get("EXISTING_KEY"), "from_file")

    def test_load_env_file_skips_comments_and_blank_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text(
                "# comment\n\nSANDBOX_ENGINE=local\n",
                encoding="utf-8",
            )
            with unittest.mock.patch.dict("os.environ", {}, clear=True):
                load_env_file(env_path)
                self.assertEqual(__import__("os").environ.get("SANDBOX_ENGINE"), "local")
