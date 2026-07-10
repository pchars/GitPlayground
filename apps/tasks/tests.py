from io import BytesIO
import zipfile

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from apps.tasks.importer import TaskImportError, import_task_zip, inspect_task_zip
from apps.tasks.management.commands.seed_initial_data import TASK_BLUEPRINTS
from apps.tasks.models import Task, TaskAsset, TheoryBlock
from apps.tasks.task_descriptions import TASK_CONDITIONS
from apps.tasks.task_hints import TASK_HINTS


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


class TaskHintsCoverageTests(SimpleTestCase):
    def test_every_seeded_task_slug_has_two_hints(self):
        slugs = [slug for level_tasks in TASK_BLUEPRINTS.values() for slug, _, _ in level_tasks]
        missing = [slug for slug in slugs if slug not in TASK_HINTS]
        self.assertFalse(missing, f"TASK_HINTS missing slugs: {missing}")
        for slug in slugs:
            hints = TASK_HINTS[slug]
            self.assertEqual(len(hints), 2, msg=f"{slug} must have exactly two hints")
            self.assertTrue(all(h.strip() for h in hints), msg=f"{slug} has empty hint text")

    def test_init_repo_hint_is_task_specific_not_generic_level_text(self):
        hint1, hint2 = TASK_HINTS["init_repo"]
        self.assertIn("git init", hint1.lower())
        self.assertNotIn("status -> add -> commit", hint1.lower())
        self.assertNotIn("буферная зона", hint2.lower())


class TaskConditionsCoverageTests(SimpleTestCase):
    def test_every_seeded_task_slug_has_condition_text(self):
        slugs = [slug for level_tasks in TASK_BLUEPRINTS.values() for slug, _, _ in level_tasks]
        missing = [slug for slug in slugs if slug not in TASK_CONDITIONS]
        self.assertFalse(missing, f"TASK_CONDITIONS missing slugs: {missing}")
        for slug in slugs:
            text = TASK_CONDITIONS[slug]
            self.assertTrue(text.strip(), msg=f"{slug} has empty condition text")

    def test_init_repo_condition_states_goal_without_fluff_or_exact_command(self):
        text = TASK_CONDITIONS["init_repo"]
        # Condition states the goal without spelling out the exact command.
        self.assertIn("репозитор", text.lower())
        self.assertNotIn("git init", text.lower())
        self.assertNotIn("Контекст раздела", text)
        self.assertNotIn("буферной зоны", text)


class TaskConditionsSeedTests(TestCase):
    def test_seeded_revision_objective_is_task_description_without_section_fluff(self):
        call_command("seed_initial_data")
        task = Task.objects.get(slug="init_repo")
        revision = task.revisions.get(is_active=True)
        self.assertEqual(revision.objective, task.description)
        self.assertNotIn("Контекст раздела", revision.objective)
