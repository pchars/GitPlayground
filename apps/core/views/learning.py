"""Task list and theory pages (book TOC + one page per level)."""

from __future__ import annotations

import re

import markdown
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.utils.text import slugify

from apps.core.services import build_tasks_list_context
from apps.core.theory_html import sanitize_theory_html
from apps.tasks.models import Level
from apps.tasks.theory_extract import level_toc_sections, theory_for_task

THEORY_MARKDOWN_EXTENSIONS = ["fenced_code", "tables", "sane_lists"]


def render_theory_markdown(content_md: str) -> str:
    if not content_md:
        return ""
    rendered = markdown.markdown(content_md, extensions=THEORY_MARKDOWN_EXTENSIONS)
    rendered = rendered.replace("<table>", '<div class="theory-table-wrap"><table>')
    rendered = rendered.replace("</table>", "</table></div>")
    return sanitize_theory_html(_ensure_heading_ids(rendered))


def _ensure_heading_ids(html: str) -> str:
    """Force h2/h3 ids to match heading_anchor() used in the book TOC."""
    import html as html_lib

    def repl(match: re.Match[str]) -> str:
        tag, attrs, text = match.group(1), match.group(2), match.group(3)
        plain = re.sub(r"<[^>]+>", "", text)
        plain = html_lib.unescape(plain)
        plain = re.sub(r"[*_`]+", "", plain).strip()
        anchor = slugify(plain, allow_unicode=True)
        if not anchor:
            return match.group(0)
        attrs = re.sub(r'\s*id="[^"]*"', "", attrs)
        return f'<{tag} id="{anchor}"{attrs}>{text}</{tag}>'

    return re.sub(r"<(h[23])([^>]*)>(.*?)</\1>", repl, html, flags=re.I | re.S)


def task_theory_html(slug: str, *, level_number: int | None = None) -> str:
    return render_theory_markdown(theory_for_task(slug, level_number=level_number))


def _level_overview_markdown(level: Level) -> str:
    """Prefer THEORY_CONTENT so chapter pages match playground excerpts without a reseed."""
    from apps.tasks.theory_content import THEORY_CONTENT

    content = THEORY_CONTENT.get(level.number, "")
    if content.strip():
        return content
    theory = getattr(level, "theory", None)
    return (theory.content_md if theory else "") or ""


def _chapter_payload(level: Level) -> dict:
    content_md = _level_overview_markdown(level)
    return {
        "level": level,
        "sections": level_toc_sections(content_md),
        "has_content": bool(content_md.strip()),
    }


@login_required
def tasks_list(request, level_number=None):
    selected_level = None
    if level_number is not None:
        selected_level = get_object_or_404(Level, number=level_number)
    return render(
        request,
        "core/tasks.html",
        build_tasks_list_context(request.user, selected_level=selected_level),
    )

@login_required
def theory_home(request):
    """Book table of contents: levels as chapters, ## headings as section links."""
    chapters = []
    for level in Level.objects.prefetch_related("theory").order_by("number"):
        payload = _chapter_payload(level)
        if payload["has_content"]:
            chapters.append(payload)
    return render(request, "core/theory_home.html", {"chapters": chapters})


@login_required
def theory_detail(request, level_id):
    """One level = one theory page (full markdown)."""
    from apps.tasks.theory_content import LEVEL_DIAGRAMS

    level = get_object_or_404(Level.objects.prefetch_related("theory"), number=level_id)
    content_md = _level_overview_markdown(level)
    diagram_mermaid = (getattr(level, "theory", None) and level.theory.diagram_mermaid) or LEVEL_DIAGRAMS.get(
        level.number, ""
    )
    return render(
        request,
        "core/theory_chapter.html",
        {
            "level": level,
            "rendered_md": render_theory_markdown(content_md),
            "diagram_mermaid": diagram_mermaid,
        },
    )
