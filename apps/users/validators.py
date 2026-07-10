import re

from django.core.exceptions import ValidationError

PSEUDONYM_RE = re.compile(r"^[A-Za-z0-9_]+$")


def validate_pseudonym(value: str) -> str:
    candidate = (value or "").strip()
    if not candidate:
        raise ValidationError("Укажите псевдоним.")
    if len(candidate) > 10:
        raise ValidationError("Псевдоним не длиннее 10 символов.")
    if not PSEUDONYM_RE.fullmatch(candidate):
        raise ValidationError("Псевдоним: только латиница, цифры и подчёркивание.")
    return candidate
