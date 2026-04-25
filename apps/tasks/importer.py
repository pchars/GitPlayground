from __future__ import annotations

import base64
from dataclasses import dataclass
from io import BytesIO
import zipfile

import yaml
from django.db import transaction
from django.utils.text import slugify

from .models import Level, Task, TaskAsset


@dataclass
class ImportResult:
    task: Task
    imported_assets: int


@dataclass
class ImportPreview:
    manifest: dict
    manifest_path: str
    files: list[str]
    hints_count: int
    has_validator: bool


class TaskImportError(Exception):
    pass


def _read_required(zip_file: zipfile.ZipFile, name: str) -> str:
    try:
        return zip_file.read(name).decode("utf-8")
    except KeyError as exc:
        raise TaskImportError(f"Missing required file in zip: {name}") from exc


def _parse_task_archive(raw_bytes: bytes) -> tuple[dict, str, str, list[str], zipfile.ZipFile]:
    archive = zipfile.ZipFile(BytesIO(raw_bytes))
    names = archive.namelist()
    manifest_path = next((n for n in names if n.endswith("manifest.yaml")), None)
    if not manifest_path:
        raise TaskImportError("manifest.yaml not found in uploaded archive")

    manifest_raw = _read_required(archive, manifest_path)
    try:
        manifest = yaml.safe_load(manifest_raw) or {}
    except yaml.YAMLError as exc:
        raise TaskImportError(f"Invalid YAML in manifest: {exc}") from exc

    required = ("id", "title", "description", "level", "order", "points")
    missing = [key for key in required if key not in manifest]
    if missing:
        raise TaskImportError(f"manifest.yaml missing fields: {', '.join(missing)}")
    return manifest, manifest_path, manifest_raw, names, archive


def inspect_task_zip(raw_bytes: bytes) -> ImportPreview:
    manifest, manifest_path, _manifest_raw, names, _archive = _parse_task_archive(raw_bytes)
    files = [name for name in names if not name.endswith("/")]
    hints_count = len([name for name in files if "/hints/" in name or "hints/" in name])
    has_validator = any("validator.py" in name for name in files)
    return ImportPreview(
        manifest=manifest,
        manifest_path=manifest_path,
        files=files,
        hints_count=hints_count,
        has_validator=has_validator,
    )


@transaction.atomic
def import_task_zip(raw_bytes: bytes) -> ImportResult:
    manifest, manifest_path, manifest_raw, names, archive = _parse_task_archive(raw_bytes)

    level = Level.objects.filter(number=int(manifest["level"])).first()
    if not level:
        level = Level.objects.create(
            number=int(manifest["level"]),
            title=f"Level {manifest['level']}",
            slug=f"level-{manifest['level']}",
            description="Imported level",
        )

    task, _ = Task.objects.update_or_create(
        external_id=str(manifest["id"]),
        defaults={
            "slug": slugify(str(manifest["id"])),
            "title": str(manifest["title"]),
            "description": str(manifest["description"]),
            "platform": str(manifest.get("platform", Task.Platform.GITHUB)).lower(),
            "level": level,
            "order": int(manifest["order"]),
            "points": int(manifest["points"]),
            "validator_cmd": str(manifest.get("validator_cmd", "python validator.py")),
            "success_message": str(manifest.get("success_message", "Task completed")),
            "metadata": {
                "tags": manifest.get("tags", []),
                "platform": str(manifest.get("platform", Task.Platform.GITHUB)).lower(),
            },
        },
    )

    TaskAsset.objects.filter(task=task).delete()
    imported_assets = 0
    theory_md = None
    theory_mermaid = None
    for file_name in names:
        if file_name.endswith("/") or file_name.endswith("manifest.yaml"):
            continue
        content = archive.read(file_name)
        text_content = ""
        try:
            text_content = content.decode("utf-8")
        except UnicodeDecodeError:
            encoded = base64.b64encode(content).decode("ascii")
            if "start_repo" in file_name and file_name.lower().endswith(".zip"):
                text_content = f"base64zip:{encoded}"
            else:
                text_content = f"base64:{encoded}"

        if "validator.py" in file_name:
            asset_type = TaskAsset.AssetType.VALIDATOR
        elif "start_repo" in file_name:
            asset_type = TaskAsset.AssetType.START_REPO
        elif "/hints/" in file_name:
            asset_type = TaskAsset.AssetType.HINT
        elif "/theory/" in file_name:
            asset_type = TaskAsset.AssetType.THEORY
        else:
            asset_type = TaskAsset.AssetType.MANIFEST

        TaskAsset.objects.create(
            task=task,
            asset_type=asset_type,
            path=file_name,
            content=text_content,
            sort_order=imported_assets + 1,
        )
        imported_assets += 1

        if asset_type == TaskAsset.AssetType.THEORY:
            lowered = file_name.lower()
            if lowered.endswith(".md") and theory_md is None:
                theory_md = text_content
            if lowered.endswith(".mermaid") and theory_mermaid is None:
                theory_mermaid = text_content

    TaskAsset.objects.create(
        task=task,
        asset_type=TaskAsset.AssetType.MANIFEST,
        path=manifest_path,
        content=manifest_raw,
        sort_order=imported_assets + 1,
    )
    imported_assets += 1

    if theory_md or theory_mermaid:
        from .models import TheoryBlock

        TheoryBlock.objects.update_or_create(
            level=level,
            defaults={
                "title": f"Теория: {level.title}",
                "content_md": theory_md or "",
                "diagram_mermaid": theory_mermaid or "",
            },
        )
    return ImportResult(task=task, imported_assets=imported_assets)
