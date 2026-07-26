from django.test import SimpleTestCase, override_settings

from apps.core.playground_limits import allow_auth_action, allow_playground_action
from apps.core.theory_html import sanitize_theory_html
from apps.core.views.learning import render_theory_markdown


class TheoryHtmlSanitizeTests(SimpleTestCase):
    def test_strips_script_and_event_handlers(self):
        dirty = '<p>ok</p><script>alert(1)</script><img src=x onerror="alert(1)">'
        clean = sanitize_theory_html(dirty)
        self.assertIn("<p>ok</p>", clean)
        self.assertNotIn("<script", clean.lower())
        self.assertNotIn("onerror", clean.lower())
        self.assertNotIn("<img", clean.lower())

    def test_render_theory_markdown_keeps_heading_ids_and_strips_raw_html(self):
        html = render_theory_markdown('## Раздел\n\n<script>alert(1)</script>\n\nТекст')
        self.assertIn('id="раздел"', html)
        self.assertNotIn("<script", html.lower())
        self.assertIn("Текст", html)


class RateLimitHelperTests(SimpleTestCase):
    @override_settings(
        CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    )
    def test_playground_validate_cap(self):
        with override_settings():
            import os
            import uuid

            os.environ["PLAYGROUND_RL_WINDOW_SEC"] = "60"
            os.environ["PLAYGROUND_RL_MAX_VALIDATE"] = "2"
            uid = int(uuid.uuid4().int % 10_000_000) + 10_000
            try:
                self.assertTrue(allow_playground_action(uid, uid, "validate"))
                self.assertTrue(allow_playground_action(uid, uid, "validate"))
                self.assertFalse(allow_playground_action(uid, uid, "validate"))
            finally:
                os.environ.pop("PLAYGROUND_RL_MAX_VALIDATE", None)

    @override_settings(
        CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    )
    def test_auth_action_cap(self):
        import os
        import uuid

        os.environ["AUTH_RL_WINDOW_SEC"] = "60"
        os.environ["AUTH_RL_MAX_LOGIN"] = "2"
        key = f"test-ip-{uuid.uuid4().hex}"
        try:
            self.assertTrue(allow_auth_action(key, "login"))
            self.assertTrue(allow_auth_action(key, "login"))
            self.assertFalse(allow_auth_action(key, "login"))
        finally:
            os.environ.pop("AUTH_RL_MAX_LOGIN", None)
