"""Анализ распределения сложности банка вопросов квиза."""

from __future__ import annotations

import sys
from collections import Counter

sys.path.insert(0, ".")

from apps.quiz.question_generator import iter_packed_questions  # noqa: E402

rows = iter_packed_questions()
by_diff = Counter(r["difficulty"] for r in rows)
total = len(rows)
print("=== Текущее распределение ===")
for key in ("easy", "medium", "hard"):
    count = by_diff[key]
    print(f"  {key}: {count} ({100 * count / total:.1f}%)")

cmd_prefixes = (
    "Что делает команда",
    "За что отвечает команда",
    "Нужно выполнить действие",
    "Какая команда",
)


def is_command_row(row: dict) -> bool:
    return any(row["prompt"].startswith(p) for p in cmd_prefixes)


cmd_rows = [r for r in rows if is_command_row(r)]
concept_rows = [r for r in rows if not is_command_row(r)]
print(f"\nКомандные: {len(cmd_rows)}, концептуальные: {len(concept_rows)}")
print("Командные:", dict(Counter(r["difficulty"] for r in cmd_rows)))
print("Концептуальные:", dict(Counter(r["difficulty"] for r in concept_rows)))

print("\n=== Концепты HARD, но про базовые темы ===")
easy_markers = (
    "fast-forward",
    "origin",
    "head",
    "staging",
    "три состоян",
    "gitignore",
    "clone",
    "ветк",
    "индекс",
    "коммит",
)
for row in concept_rows:
    if row["difficulty"] != "hard":
        continue
    text = (row["prompt"] + row[f"choice_{row['correct_index']}"]).lower()
    if any(m in text for m in easy_markers):
        print(f"  - {row['prompt'][:90]}")
