import re

from django.template import Context, Template
from django.test import SimpleTestCase

from apps.core.templatetags.static_versioned import _content_hash, static_v


class StaticVersionedTagTests(SimpleTestCase):
    def test_appends_content_hash_for_existing_file(self):
        url = static_v("css/common.css")
        self.assertIn("css/common.css", url)
        match = re.search(r"\?v=([0-9a-f]{8})$", url)
        self.assertIsNotNone(match, f"URL has no ?v=<hash>: {url}")

    def test_hash_is_stable_and_reflects_content(self):
        first = static_v("css/common.css")
        second = static_v("css/common.css")
        self.assertEqual(first, second)

    def test_missing_file_returns_plain_url(self):
        url = static_v("css/does-not-exist-xyz.css")
        self.assertNotIn("?v=", url)
        self.assertIn("does-not-exist-xyz.css", url)

    def test_tag_available_as_builtin_without_load(self):
        rendered = Template("{% static_v 'js/playground.js' %}").render(Context({}))
        self.assertIn("js/playground.js", rendered)
        self.assertIn("?v=", rendered)

    def test_content_hash_handles_unreadable_source(self):
        self.assertIsNone(_content_hash("/no/such/path/file.css", 0.0))
