"""Validate and repair quiz question prompts before seeding."""

from __future__ import annotations

import re

_SINGLE_WORD_PROMPTS = frozenset(
    {"Почему", "Как", "Что", "Когда", "В", "Чем", "Где", "Зачем"}
)

# Truncated prompts from book-ingest consolidation (old -> fixed).
PROMPT_REPAIRS: dict[str, str] = {
    "Почему": "Почему index и staging area считаются одним и тем же?",
    "Как": "Как Git позволяет работать без сети?",
    "Что": "Что происходит с merge и ветками до первого push?",
    "Когда": "Когда предпочтителен revert вместо reset на общей ветке?",
    "В": "Что такое tree-объект в модели Git?",
    "Чем": "Чем staging area отличается от истории коммитов?",
    "Где": "Где уместен self-hosted Git (GitLab, Gitea)?",
    "Какие три основных состояния файла описывает": "Какие три основных состояния файла описывает Git?",
    "Что такое «Git directory» в модели": "Что такое «Git directory» в модели Git?",
    "Какой базовый цикл работы с Git описан в": "Какой базовый цикл работы с Git описан в Pro Git?",
    "Чем decentralized VCS отличается от centralized по": (
        "Чем decentralized VCS отличается от centralized по модели хранения?"
    ),
    "Что такое remote-tracking branch по": "Что такое remote-tracking branch по Pro Git?",
    "Что такое bare repository по": "Что такое bare repository по Pro Git?",
    "Что такое «integration-manager workflow» в": "Что такое «integration-manager workflow» в Pro Git?",
    "Какой типичный порядок интеграции topic-ветки перед push в": (
        "Какой типичный порядок интеграции topic-ветки перед push в upstream?"
    ),
    "Что такое «dictator and lieutenants workflow» в": (
        "Что такое «dictator and lieutenants workflow» в Pro Git?"
    ),
    "Какие «три дерева» Git описывает": "Какие «три дерева» Git описывает в модели состояния?",
    "Что такое «золотое правило rebase» в": "Что такое «золотое правило rebase» в командной работе?",
    "Что делает `git commit --amend` по": "Что делает `git commit --amend` по сути?",
    "Когда уместен `git cherry-pick` по": "Когда уместен `git cherry-pick` по workflow?",
    "Где хранятся client-side hooks по": "Где хранятся client-side hooks по умолчанию?",
    "Какие четыре типа объектов Git описывает": "Какие четыре типа объектов Git описывает в object database?",
    "Где Git хранит указатели веток по": "Где Git хранит указатели веток по умолчанию?",
    "Что показывает `git status --short` в модели": (
        "Что показывает `git status --short` в модели состояний Git?"
    ),
    "Что означает «fast-forward» при merge по": "Что означает «fast-forward» при merge по определению?",
    "Что делает `core.autocrlf` по": "Что делает `core.autocrlf` в настройках Git?",
    "Чем blob отличается от commit в модели": "Чем blob отличается от commit в модели объектов Git?",
    "Цикл состояний файла в": "Какой цикл состояний файла описывает Git?",
    "Коммит по": "Где виден коммит сразу после `git commit`?",
    "Баг в уже выпущенном релизе — :": "Баг в уже выпущенном релизе — что делать?",
    "Удалить неотслеживаемый мусор в рабочей копии :": "Как безопасно удалить неотслеживаемый мусор в рабочей копии?",
    "При corrupt index (`bad index file sha1`) :": "При corrupt index (`bad index file sha1`) что делать?",
    "Локальный аналог `git hash-object -w` в Git Data API —": (
        "Локальный аналог `git hash-object -w` в Git Data API — это:"
    ),
    "Activity API включает :": "Activity API на GitHub включает:",
    "В `.git/objects/` loose-объект с SHA `a576fac3…` лежит как :": (
        "В `.git/objects/` loose-объект с SHA `a576fac3…` лежит как:"
    ),
    "Индекс в ранней терминологии Git назывался :": "Индекс в ранней терминологии Git назывался:",
    "`git commit` строит tree/commit из :": "`git commit` строит tree/commit из:",
    "Переменная `GIT_DIR` позволяет :": "Переменная `GIT_DIR` позволяет:",
    "Packfiles в Git нужны для :": "Packfiles в Git нужны для:",
    "После `git clone` ветка upstream `story84` станет :": "После `git clone` ветка upstream `story84` станет:",
    "Teams vs отдельные users в GitLab :": "Teams vs отдельные users в GitLab — в чём разница?",
    "Официальные каналы помощи GitLab :": "Официальные каналы помощи GitLab — это:",
    "Reflog shortnames (`main@{3}`) в :": "Reflog shortnames (`main@{3}`) в Git — это:",
    "Индекс (staging) в — это:": "Индекс (staging) в Git — это:",
    "Bare repository в — это:": "Bare repository в Git — это:",
    "Integration manager workflow :": "Integration manager workflow — это:",
    "Topic/feature branch в — это:": "Topic/feature branch в Git — это:",
    "Push mode `simple` (по умолчанию) :": "Push mode `simple` (по умолчанию) означает:",
    "Cherry-pick в — это:": "Cherry-pick в Git — это:",
    "Subtree merge vs submodule :": "Subtree merge vs submodule — в чём разница?",
    "Ключевое преимущество распределённой модели :": "Ключевое преимущество распределённой модели Git:",
    "Porcelain vs plumbing в :": "Porcelain vs plumbing в Git — это:",
    "Annotated tag vs lightweight :": "Annotated tag vs lightweight tag — в чём разница?",
    "Detached HEAD в — это:": "Detached HEAD в Git — это:",
    "Модель «несколько репозиториев» :": "Модель «несколько репозиториев» в Git:",
    "Fork-and-pull workflow :": "Fork-and-pull workflow — это:",
    "`git fetch` vs `git pull` :": "`git fetch` vs `git pull` — в чём разница?",
    "git subtree vs submodule :": "git subtree vs submodule — в чём разница?",
    "Squash merge :": "Squash merge — это:",
    "`git reset --soft` :": "`git reset --soft` — что делает?",
    "Bare repository :": "Bare repository — это:",
    "Maintainer vs developer :": "Maintainer vs developer в open source — в чём разница?",
    "pre-commit hook :": "pre-commit hook — когда выполняется?",
}


def normalize_concept_prompt(prompt: str) -> str | None:
    """Return a usable prompt or None if the question should be dropped."""
    text = prompt.strip()
    if not text:
        return None
    if text in PROMPT_REPAIRS:
        text = PROMPT_REPAIRS[text]
    if text in _SINGLE_WORD_PROMPTS:
        return None
    if len(text) < 12:
        return None
    if _looks_truncated(text):
        return None
    if not text.endswith("?") and not text.endswith(":"):
        text = f"{text}?"
    return text


def _looks_truncated(prompt: str) -> bool:
    if prompt in _SINGLE_WORD_PROMPTS:
        return True
    if re.search(r"\bв\s*—\s*это:\s*$", prompt):
        return True
    if re.search(r"\bв\s*:\s*$", prompt):
        return True
    if prompt.endswith(" описывает") or prompt.endswith(" в модели"):
        return True
    if prompt.endswith(" по") or prompt.endswith(" в"):
        return True
    if prompt.endswith(" —") and "?" not in prompt:
        return True
    return False


def is_usable_prompt(prompt: str) -> bool:
    return normalize_concept_prompt(prompt) is not None
