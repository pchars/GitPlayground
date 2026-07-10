"""Generate a large bank of Git questions (no sections in the UI)."""

from __future__ import annotations

import random
import re
from typing import Any

from apps.quiz.concept_questions import CONCEPT_QUESTIONS
from apps.quiz.difficulty import classify_command_difficulty, classify_concept_difficulty

# Command -> short correct description (for the learning quiz).
CMD_TO_DESC: dict[str, str] = {
    "git add": "добавляет изменения рабочей копии в индекс (staging)",
    "git status": "показывает состояние файлов: индекс, неотслеживаемые, изменённые",
    "git diff": "показывает различия между рабочей копией, индексом и коммитами",
    "git commit": "создаёт новый коммит из текущего индекса с сообщением",
    "git push": "отправляет локальные коммиты на удалённый репозиторий",
    "git pull": "забирает изменения с remote и обычно сливает их в текущую ветку",
    "git fetch": "скачивает объекты с remote, не меняя рабочую ветку автоматически",
    "git merge": "вносит историю другой ветки в текущую (слияние)",
    "git rebase": "переносит коммиты текущей ветки поверх другой ветки",
    "git branch": "показывает или создаёт ветки, не переключаясь на них",
    "git checkout": "переключает ветку или восстанавливает файлы из указанной ревизии",
    "git switch": "переключает текущую ветку (современная альтернатива части checkout)",
    "git restore": "восстанавливает файлы в рабочей копии или индексе из ревизии",
    "git reset": "сдвигает указатель ветки и опционально меняет индекс/рабочую копию",
    "git revert": "создаёт новый коммит, отменяющий изменения указанного коммита",
    "git cherry-pick": "применяет один или несколько коммитов из другой ветки в текущую",
    "git stash": "временно сохраняет незакоммиченные изменения в стек",
    "git tag": "создаёт или показывает метки на коммитах",
    "git blame": "показывает, какой коммит и автор изменили каждую строку файла",
    "git bisect": "двоичный поиск коммита, в котором появился баг",
    "git grep": "ищет шаблон в отслеживаемых файлах репозитория",
    "git log": "показывает историю коммитов текущей ветки (или указанной)",
    "git show": "показывает объект (коммит, тег) и связанный diff",
    "git remote": "управляет ссылками на удалённые репозитории",
    "git clone": "копирует репозиторий с сервера в новый локальный каталог",
    "git init": "создаёт новый репозиторий Git в каталоге",
    "git mv": "переименовывает или перемещает отслеживаемый файл с учётом индекса",
    "git rm": "удаляет файл из рабочей копии и индекса",
    "git clean": "удаляет неотслеживаемые файлы из рабочей копии",
    "git submodule": "управляет вложенными репозиториями внутри основного",
    "git worktree": "позволяет иметь несколько рабочих копий одного репозитория",
    "git reflog": "показывает историю перемещений HEAD и веток",
    "git config": "читает и записывает настройки Git (локально, глобально, системно)",
    "git describe": "строит человекочитаемое имя на основе ближайших тегов",
    "git archive": "упаковывает дерево файлов репозитория в архив",
    "git notes": "добавляет к коммитам дополнительные метаданные, не меняя сообщение",
    "git format-patch": "формирует серии патчей из коммитов для рассылки",
    "git am": "применяет серию патчей из почтового ящика в виде коммитов",
    "git apply": "применяет патч к рабочей копии или индексу",
    "git shortlog": "группирует коммиты по авторам с краткой статистикой",
    "git range-diff": "сравнивает два диапазона коммитов (например, до/после rebase)",
    "git rerere": "запоминает разрешения конфликтов для повторного применения",
    "git sparse-checkout": "ограничивает рабочую копию подмножеством путей",
    "git bundle": "упаковывает объекты репозитория в файл для переноса офлайн",
    "git gc": "собирает мусор и оптимизирует локальное хранилище объектов",
    "git fsck": "проверяет целостность объектов и ссылок в репозитории",
    "git help": "показывает справку по командам и руководствам Git",
    "git version": "выводит установленную версию Git",
    "git pull --rebase": "забирает с remote и переносит ваши коммиты поверх чужих",
    "git merge --no-ff": "создаёт merge-коммит даже при возможности fast-forward",
    "git merge --squash": "собирает изменения в один diff без merge-коммита автоматически",
    "git rebase -i": "интерактивно переписывает, объединяет или переупорядочивает коммиты",
    "git commit --amend": "заменяет последний коммит новым деревом или сообщением",
    "git push -u": "пушит ветку и настраивает отслеживание upstream",
    "git push --force-with-lease": "безопаснее чем --force: перезапись с проверкой remote",
    "git log --oneline": "показывает коммиты в одну строку на коммит",
    "git log --graph": "рисует ASCII-граф ветвлений рядом с историей",
    "git diff --staged": "сравнивает индекс с последним коммитом",
    "git diff HEAD": "сравнивает рабочую копию и индекс с указанной ревизией",
    "git reset --soft": "сдвигает ветку, сохраняя индекс и рабочую копию",
    "git reset --hard": "сдвигает ветку и выравнивает индекс и рабочую копию",
    "git reset --mixed": "сдвигает ветку и сбрасывает индекс, рабочая копия сохраняется",
    "git checkout -b": "создаёт новую ветку и сразу переключается на неё",
    "git branch -d": "удаляет локальную ветку, если она уже слита",
    "git branch -D": "принудительно удаляет локальную ветку",
    "git remote -v": "показывает URL fetch/push для remotes",
    "git remote add": "добавляет новое имя удалённого репозитория",
    "git remote remove": "удаляет ссылку на удалённый репозиторий",
    "git fetch --prune": "удаляет локальные ссылки на ветки, исчезнувшие на remote",
    "git tag -a": "создаёт аннотированный тег с сообщением",
    "git stash pop": "применяет верхний stash и удаляет его из стека",
    "git stash apply": "применяет stash, оставляя его в стеке",
    "git cherry-pick --continue": "продолжает cherry-pick после разрешения конфликта",
    "git merge --abort": "отменяет незавершённый merge и возвращает состояние",
    "git rebase --abort": "отменяет незавершённый rebase",
    "git rebase --continue": "продолжает rebase после разрешения конфликта",
    "git clean -fd": "удаляет неотслеживаемые файлы и каталоги",
    "git submodule update --init": "инициализирует и обновляет вложенные модули",
    "git worktree add": "добавляет вторую рабочую копию для той же .git",
    "git bisect start": "начинает сессию двоичного поиска регрессии",
    "git bisect good": "помечает текущий коммит как «хороший» в bisect",
    "git bisect bad": "помечает текущий коммит как «плохой» в bisect",
    "git blame -L": "ограничивает blame диапазоном строк",
    "git log -p": "показывает патч для каждого коммита в истории",
    "git show HEAD~1": "показывает родителя текущего коммита",
    "git rev-parse": "выводит канонический SHA или разрешает ссылку",
    "git cat-file": "печатает содержимое или метаданные объекта по SHA",
    "git ls-tree": "перечисляет файлы в дереве коммита",
    "git update-index": "низкоуровневое изменение индекса",
    "git write-tree": "записывает текущее дерево индекса как объект",
    "git commit-tree": "создаёт коммит-объект из дерева и родителей",
    "git symbolic-ref": "читает или устанавливает символическую ссылку (например HEAD)",
    "git update-ref": "обновляет ссылку на конкретный SHA",
    "git for-each-ref": "перебирает ссылки с фильтрами и форматированием",
    "git merge-base": "находит общего предка для слияния или rebase",
    "git cherry": "показывает, какие коммиты есть в одной ветке, но не в другой",
    "git request-pull": "формирует текст запроса на подтягивание изменений",
    "git maintenance start": "регистрирует фоновое обслуживание репозитория",
}

QUESTION_TEMPLATES = (
    "Что делает команда `{0}`?",
    "За что отвечает команда `{0}`?",
    "Какую задачу решает команда `{0}`?",
    "Какой основной эффект у `{0}`?",
    "Когда обычно используют `{0}`?",
    "Какой результат чаще всего даёт `{0}`?",
    "Для чего чаще всего запускают `{0}`?",
    "Что изменится после выполнения `{0}`?",
)

SCENARIO_TEMPLATES = (
    "Нужно выполнить действие: «{1}». Какую команду выбрать?",
    "Какая команда лучше подходит, если цель: «{1}»?",
    "Что нужно выполнить в ситуации: «{1}»?",
    "Какая команда решает задачу: «{1}»?",
    "Какой вариант корректен для сценария: «{1}»?",
    "Что уместно запустить первым, если нужно: «{1}»?",
)

PARAMETER_ROLE_TEMPLATES = (
    "За что отвечает опция/команда `{0}` в типичном workflow?",
    "Какую практическую пользу даёт `{0}`?",
    "Какой смысл чаще всего вкладывают в использование `{0}`?",
    "Что важно помнить про `{0}` в повседневной работе?",
)

INVERSE_TEMPLATE = (
    "Какая команда Git лучше всего соответствует описанию: «{0}»?"
)

def _shuffle_choices(correct: str, w1: str, w2: str, w3: str, seed: int) -> tuple[list[str], int]:
    rng = random.Random(seed)
    opts = [correct, w1, w2, w3]
    order = [0, 1, 2, 3]
    rng.shuffle(order)
    permuted = [opts[i] for i in order]
    correct_index = permuted.index(correct)
    return permuted, correct_index


def _explanation_map_for_command_question(cmd: str, choices: list[str], correct_index: int) -> dict[str, str]:
    explanations: dict[str, str] = {}
    correct_desc = CMD_TO_DESC[cmd]
    for idx, label in enumerate(choices):
        if idx == correct_index:
            explanations[f"explanation_{idx}"] = (
                f"Верно. `{cmd}` действительно {correct_desc}."
            )
        else:
            explanations[f"explanation_{idx}"] = (
                f"Неверно. Этот вариант описывает другое действие: «{label}». "
                f"На самом деле `{cmd}` {correct_desc}."
            )
    return explanations


def _explanation_map_for_inverse_question(correct_cmd: str, choices: list[str], correct_index: int) -> dict[str, str]:
    explanations: dict[str, str] = {}
    for idx, label in enumerate(choices):
        if idx == correct_index:
            explanations[f"explanation_{idx}"] = (
                f"Верно. Именно `{correct_cmd}` {CMD_TO_DESC[correct_cmd]}."
            )
        else:
            explanations[f"explanation_{idx}"] = (
                f"Неверно. `{label}` {CMD_TO_DESC.get(label, 'делает другое действие')}. "
                f"Правильный ответ: `{correct_cmd}`, потому что он {CMD_TO_DESC[correct_cmd]}."
            )
    return explanations


def _explanation_map_for_concept_question(correct_text: str, choices: list[str], correct_index: int) -> dict[str, str]:
    explanations: dict[str, str] = {}
    for idx, label in enumerate(choices):
        if idx == correct_index:
            explanations[f"explanation_{idx}"] = f"Верно. Это точное определение: {correct_text}."
        else:
            explanations[f"explanation_{idx}"] = (
                f"Неверно. Вариант «{label}» не отражает смысл вопроса. "
                f"Правильное утверждение: {correct_text}."
            )
    return explanations


def _normalize_prompt(text: str) -> str:
    lowered = text.lower().strip()
    lowered = re.sub(r"`[^`]+`", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered


def _semantic_dedup_key(row: dict[str, Any]) -> str:
    """Dedup key for balanced bank: one idea -> one question."""
    prompt = _normalize_prompt(row["prompt"])
    correct = _normalize_prompt(row[f"choice_{row['correct_index']}"])
    if prompt.startswith("нужно выполнить действие") or "какую команду выбрать" in prompt:
        return f"scenario:{correct}"
    if prompt.startswith("что делает команда") or prompt.startswith("за что отвечает команда"):
        return f"direct:{correct}"
    # Single-fact concept questions (detached HEAD, staging, rerere…) — one answer.
    if any(
        marker in prompt
        for marker in (
            "что такое",
            "что означает",
            "чем отличается",
            "зачем",
            "почему",
            "что делает `git",
        )
    ):
        return f"concept-fact:{correct}"
    return f"concept:{correct}|{prompt[:72]}"


def _dedupe_question_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen_prompts: set[str] = set()
    seen_semantic: set[str] = set()
    unique: list[dict[str, Any]] = []
    for row in rows:
        prompt_key = row["prompt"]
        semantic_key = _semantic_dedup_key(row)
        if prompt_key in seen_prompts or semantic_key in seen_semantic:
            continue
        seen_prompts.add(prompt_key)
        seen_semantic.add(semantic_key)
        unique.append(row)
    return unique


def iter_packed_questions() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    all_descs = list(CMD_TO_DESC.values())
    all_cmds = list(CMD_TO_DESC.keys())

    for cmd, desc in CMD_TO_DESC.items():
        wrong_pool = [d for d in all_descs if d != desc]
        # Per action keep one meaning question + one scenario question,
        # to avoid near-duplicate phrasing.
        direct_tmpl = QUESTION_TEMPLATES[abs(hash(cmd)) % len(QUESTION_TEMPLATES)]
        rng = random.Random((hash(cmd) ^ hash(direct_tmpl)) & 0xFFFFFFFF)
        shuffled_wrong = wrong_pool[:]
        rng.shuffle(shuffled_wrong)
        w1, w2, w3 = shuffled_wrong[:3]
        prompt = direct_tmpl.format(cmd)
        choices, ci = _shuffle_choices(desc, w1, w2, w3, seed=(hash(prompt) % 2**31))
        rows.append(
            {
                "prompt": prompt,
                "choice_0": choices[0],
                "choice_1": choices[1],
                "choice_2": choices[2],
                "choice_3": choices[3],
                "correct_index": ci,
                "difficulty": classify_command_difficulty(cmd),
                **_explanation_map_for_command_question(cmd, choices, ci),
            }
        )

        scenario_tmpl = SCENARIO_TEMPLATES[abs(hash(f"scenario:{cmd}")) % len(SCENARIO_TEMPLATES)]
        scenario_prompt = scenario_tmpl.format(cmd, desc)
        wrong_cmds = random.Random((hash(scenario_prompt) ^ 0x55555555) & 0xFFFFFFFF).sample(
            [c for c in all_cmds if c != cmd],
            3,
        )
        scenario_choices, scenario_ci = _shuffle_choices(
            cmd,
            wrong_cmds[0],
            wrong_cmds[1],
            wrong_cmds[2],
            seed=(hash(scenario_prompt) % 2**31),
        )
        rows.append(
            {
                "prompt": scenario_prompt,
                "choice_0": scenario_choices[0],
                "choice_1": scenario_choices[1],
                "choice_2": scenario_choices[2],
                "choice_3": scenario_choices[3],
                "correct_index": scenario_ci,
                "difficulty": classify_command_difficulty(cmd),
                **_explanation_map_for_inverse_question(cmd, scenario_choices, scenario_ci),
            }
        )

    all_concept_questions = CONCEPT_QUESTIONS
    for q, a, b, c, d in all_concept_questions:
        choices, ci = _shuffle_choices(a, b, c, d, seed=(hash(q) % 2**31))
        rows.append(
            {
                "prompt": q,
                "choice_0": choices[0],
                "choice_1": choices[1],
                "choice_2": choices[2],
                "choice_3": choices[3],
                "correct_index": ci,
                "difficulty": classify_concept_difficulty(q, a),
                **_explanation_map_for_concept_question(a, choices, ci),
            }
        )

    return _dedupe_question_rows(rows)


def question_count() -> int:
    return len(iter_packed_questions())
