"""Theory excerpt / TOC helpers stay aligned with level markdown."""

from django.test import SimpleTestCase

from apps.core.views.learning import render_theory_markdown
from apps.tasks.theory_content import THEORY_CONTENT
from apps.tasks.theory_extract import heading_anchor, level_toc_sections, theory_for_task


class TheoryExtractTests(SimpleTestCase):
    def test_sandbox_cat_excerpt_comes_from_level_0(self):
        excerpt = theory_for_task("sandbox_cat", level_number=0)
        self.assertIn("## `cat`", excerpt)
        self.assertIn("cat practice/notes.txt", excerpt)
        self.assertNotIn("Бизнес", excerpt)

    def test_toc_anchors_match_rendered_heading_ids(self):
        md = THEORY_CONTENT[0]
        sections = level_toc_sections(md)
        self.assertGreaterEqual(len(sections), 3)
        html = render_theory_markdown(md)
        for section in sections:
            self.assertIn(f'id="{section["anchor"]}"', html)

    def test_heading_anchor_strips_backticks(self):
        self.assertEqual(heading_anchor("`cat` — прочитать файл"), "cat-прочитать-файл")
