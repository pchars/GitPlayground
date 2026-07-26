"""Sanitize rendered theory HTML (markdown output before |safe)."""

from __future__ import annotations

import nh3

# Tags/attrs produced by markdown + heading ids + table wrap.
_THEORY_TAGS = {
    "a",
    "blockquote",
    "br",
    "code",
    "div",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "li",
    "ol",
    "p",
    "pre",
    "strong",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "ul",
}
_THEORY_ATTRIBUTES = {
    "a": {"href", "title"},
    "code": {"class"},
    "div": {"class"},
    "h1": {"id"},
    "h2": {"id"},
    "h3": {"id"},
    "h4": {"id"},
    "h5": {"id"},
    "h6": {"id"},
    "pre": {"class"},
    "td": {"align"},
    "th": {"align"},
}
_THEORY_URL_SCHEMES = {"http", "https", "mailto"}


def sanitize_theory_html(html: str) -> str:
    if not html:
        return ""
    return nh3.clean(
        html,
        tags=_THEORY_TAGS,
        attributes=_THEORY_ATTRIBUTES,
        url_schemes=_THEORY_URL_SCHEMES,
    )
