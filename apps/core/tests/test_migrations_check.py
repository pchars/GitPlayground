import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase


class MigrationGraphSanityTests(SimpleTestCase):
    def test_makemigrations_check_clean(self):
        root = Path(__file__).resolve().parents[3]
        manage = root / "manage.py"
        proc = subprocess.run(
            [sys.executable, str(manage), "makemigrations", "--check", "--dry-run"],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
