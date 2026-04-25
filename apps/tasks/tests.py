from io import BytesIO
import zipfile

from django.test import TestCase

from apps.tasks.importer import TaskImportError, import_task_zip, inspect_task_zip
from apps.tasks.models import Task, TaskAsset, TheoryBlock


def _build_task_zip(with_manifest: bool = True) -> bytes:
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        if with_manifest:
            archive.writestr(
                "task_01/manifest.yaml",
                "\n".join(
                    [
                        'id: "1.1"',
                        'title: "Init repo"',
                        'description: "Create repository"',
                        "level: 1",
                        "order: 1",
                        "points: 5",
                        'validator_cmd: "python validator.py"',
                    ]
                ),
            )
        archive.writestr("task_01/validator.py", "print('ok')\n")
        archive.writestr("task_01/hints/hint1.txt", "Use git init\n")
        archive.writestr("task_01/theory/explanation.md", "# Theory\n\nBody")
        archive.writestr("task_01/theory/diagram.mermaid", "graph LR\nA-->B")
    return stream.getvalue()


class TaskImporterTests(TestCase):
    def test_preview_contains_manifest(self):
        preview = inspect_task_zip(_build_task_zip())
        self.assertEqual(preview.manifest["id"], "1.1")
        self.assertTrue(preview.has_validator)
        self.assertGreaterEqual(preview.hints_count, 1)

    def test_import_creates_task_assets_and_theory(self):
        result = import_task_zip(_build_task_zip())
        self.assertEqual(result.task.external_id, "1.1")
        self.assertGreater(result.imported_assets, 0)
        self.assertTrue(Task.objects.filter(external_id="1.1").exists())
        self.assertTrue(
            TaskAsset.objects.filter(task=result.task, asset_type=TaskAsset.AssetType.VALIDATOR).exists()
        )
        self.assertTrue(TheoryBlock.objects.filter(level__number=1).exists())

    def test_import_fails_without_manifest(self):
        with self.assertRaises(TaskImportError):
            inspect_task_zip(_build_task_zip(with_manifest=False))

    def test_import_rejects_invalid_yaml_manifest(self):
        stream = BytesIO()
        with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("task_01/manifest.yaml", "id: [\n  broken")
        with self.assertRaises(TaskImportError) as ctx:
            inspect_task_zip(stream.getvalue())
        self.assertIn("YAML", str(ctx.exception))

    def test_import_rejects_manifest_missing_required_field(self):
        stream = BytesIO()
        with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                "task_01/manifest.yaml",
                "\n".join(
                    [
                        'id: "9.9"',
                        'title: "No points"',
                        'description: "x"',
                        "level: 1",
                        "order: 1",
                    ]
                ),
            )
        with self.assertRaises(TaskImportError) as ctx:
            inspect_task_zip(stream.getvalue())
        self.assertIn("missing fields", str(ctx.exception).lower())
