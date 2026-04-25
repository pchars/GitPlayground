import base64
from io import BytesIO
from pathlib import Path
import subprocess
import tempfile
import zipfile

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from apps.tasks.models import Level, Task, TaskAsset, TheoryBlock, TaskRevision


LEVELS = [
    (1, "Основы Git", 10),
    (2, "Ветвление", 9),
    (3, "Слияния и интеграция", 10),
    (4, "История и переписывание", 8),
    (5, "Удаленные репозитории и командная работа", 8),
    (6, "Диагностика, внутренности и автоматизация", 7),
    (7, "Гигиена репозитория: .gitignore и .gitkeep", 0),
    (8, "Тегирование и фиксация версий", 0),
]

TASK_BLUEPRINTS = {
    1: [
        ("init_repo", "Инициализируй репозиторий в текущей папке командой git init. После этого .git должен появиться в каталоге проекта.", 5),
        ("first_commit", "Создай файл hello.txt с текстом Hello, Git!, добавь его в индекс и сделай коммит с точным сообщением Add hello.", 10),
        ("check_status", "Измени hello.txt, но не добавляй файл в индекс. Проверка ожидает статус modified в блоке unstaged.", 5),
        ("stage_unstage", "Добавь hello.txt в staging, затем верни его обратно в unstaged состояние (например через git restore --staged).", 10),
        ("commit_second", "Сделай новое изменение в hello.txt и создай второй коммит с сообщением Update hello.", 10),
        ("view_diff", "Добавь строку Another line в hello.txt и убедись, что она видна в выводе git diff до индексации.", 5),
        ("amend_commit", "Создай config.txt и включи его в последний коммит через --amend, не меняя текст сообщения коммита.", 15),
        ("view_history", "Открой историю через git log --oneline --graph и проверь, что в репозитории уже есть минимум два коммита.", 5),
        ("setup_ignore", "Создай .gitignore и добавь правила для *.log и __pycache__/, чтобы эти файлы не отслеживались Git.", 10),
        ("create_tag", "Создай аннотированный тег v1.0 на текущем коммите и проверь его наличие командой git tag -l или git show v1.0.", 10),
    ],
    2: [
        ("create_branch", "Создай новую ветку feature-x и сразу переключись на нее. Текущая ветка должна стать feature-x.", 10),
        ("commit_on_branch", "На ветке feature-x создай feature.txt и зафиксируй файл отдельным коммитом.", 10),
        ("switch_branch", "Переключись обратно на main и убедись, что feature.txt не отображается в рабочем каталоге.", 5),
        ("list_branches", "Выведи список веток и проверь, что активная ветка отмечена символом *.", 5),
        ("delete_branch", "Находясь не в feature-x, удали ветку feature-x безопасной командой удаления.", 5),
        ("branch_from_commit", "Создай новую ветку не от HEAD, а от выбранного коммита из истории (по SHA).", 15),
        ("rename_branch", "Переименуй текущую ветку в более понятное имя, например feature-auth.", 10),
        ("track_remote_branch", "Создай локальную ветку, которая отслеживает удаленную ветку upstream (upstream tracking).", 15),
        ("branch_compare", "Сравни две ветки по коммитам и изменениям через git log --left-right и git diff A...B.", 15),
    ],
    3: [
        ("fast_forward_merge", "Выполни слияние, которое завершится fast-forward без отдельного merge-коммита.", 10),
        ("no_ff_merge", "Слей ветку с флагом --no-ff, чтобы в истории появился явный merge-коммит.", 15),
        ("resolve_conflict", "Разреши конфликт слияния вручную, добавь исправленные файлы и корректно заверши merge.", 25),
        ("abort_merge", "Запусти конфликтное слияние и откати процесс командой git merge --abort.", 10),
        ("merge_tool", "Разреши конфликт с помощью git mergetool (или эквивалентного ручного подхода), затем заверши merge.", 15),
        ("octopus_merge", "Выполни octopus merge: объедини сразу три совместимые ветки одной командой.", 20),
        ("squash_merge", "Слей изменения ветки в один squashed commit, чтобы получить одну итоговую фиксацию.", 20),
        ("merge_vs_rebase", "На одном и том же наборе изменений сравни результат merge и rebase в истории проекта.", 10),
        ("cherry_pick_hotfix", "Перенеси отдельный hotfix-коммит из другой ветки через git cherry-pick.", 15),
        ("revert_merge", "Откати merge-коммит через git revert -m и проверь, что история осталась корректной.", 20),
    ],
    4: [
        ("amend_message", "Исправь сообщение последнего коммита с помощью git commit --amend.", 10),
        ("reorder_commits", "Через interactive rebase поменяй порядок нескольких последних коммитов.", 25),
        ("squash_commits", "Объедини последние три коммита в один аккуратный коммит с понятной историей.", 20),
        ("drop_commit", "Через interactive rebase убери из истории один лишний коммит.", 15),
        ("edit_commit", "Во время rebase остановись на нужном коммите, измени его содержимое и продолжи rebase.", 25),
        ("rebase_onto", "Перенеси диапазон коммитов на новую базу с помощью git rebase --onto.", 30),
        ("stash_workflow", "Сохрани незавершенные изменения в stash, переключись на другую ветку и потом верни изменения обратно.", 15),
        ("reset_modes", "Покажи на практике разницу между reset --soft, --mixed и --hard на короткой истории.", 20),
    ],
    5: [
        ("clone_local", "Склонируй подготовленный upstream-репозиторий в новую локальную папку.", 10),
        ("add_remote", "Добавь второй remote с именем upstream к текущему репозиторию и проверь его в git remote -v.", 5),
        ("push_first", "Опубликуй локальную ветку main в remote upstream первым push.", 10),
        ("fetch_merge", "Забери новые изменения через git fetch и влей их вручную в текущую ветку.", 15),
        ("pull_rebase", "Настрой git pull так, чтобы обновления подтягивались через rebase, а не merge.", 15),
        ("push_conflict", "Разреши non-fast-forward конфликт (сначала обновись, потом снова push) и успешно опубликуй изменения.", 25),
        ("remote_prune", "Очисти локальные ссылки на удаленные ветки, которых уже нет на сервере, через git fetch --prune.", 10),
        ("push_tags", "Отправь аннотированный тег в удаленный репозиторий и убедись, что тег опубликован.", 10),
        ("github_pages_publish", "Настрой публикацию проекта в GitHub Pages из ветки gh-pages или из /docs и проверь доступность страницы.", 18),
        ("github_actions_ci", "Собери workflow GitHub Actions для lint/test и добейся зеленого статуса в CI.", 22),
        ("github_hooks_guard", "Добавь локальный pre-commit hook, который блокирует коммиты без обязательной проверки.", 18),
    ],
    6: [
        ("find_bisect", "Используй git bisect, чтобы найти конкретный коммит, после которого появилась поломка.", 30),
        ("reflog_recovery", "Восстанови потерянный коммит, используя запись из git reflog.", 25),
        ("filter_branch", "Перепиши историю так, чтобы чувствительный файл был удален из всех прошлых коммитов.", 35),
        ("worktree", "Создай отдельный worktree для hotfix-задачи и сделай там отдельный коммит исправления.", 15),
        ("submodule", "Подключи внешний репозиторий как submodule и зафиксируй это изменение в основном проекте.", 20),
        ("inspect_objects", "Проверь внутренние объекты Git через git cat-file, git ls-tree и git rev-parse.", 25),
        ("custom_aliases_hooks", "Добавь удобный alias в git config и включи локальный hook, который проверяет commit message.", 20),
    ],
    7: [],
    8: [],
}

GITLAB_BLUEPRINTS = {
    1: [
        ("gitlab_repo_init", "Создай проект в GitLab, добавь remote origin и выполни первый push.", 8),
        ("gitlab_readme_badges", "Добавь бейдж pipeline и ссылку на проект в README.md.", 8),
        ("gitlab_protected_branch", "Настрой protected branch для main/master через настройки проекта.", 12),
    ],
    2: [
        ("gitlab_mr_flow", "Создай feature-ветку и оформи Merge Request с осмысленным описанием.", 12),
        ("gitlab_codeowners", "Подключи CODEOWNERS и проверь, что для MR требуется review.", 12),
        ("gitlab_ci_lint_test", "Собери .gitlab-ci.yml с этапами lint и test.", 14),
    ],
    3: [
        ("gitlab_ci_cache", "Добавь cache/artifacts для ускорения и передачи данных между stage.", 16),
        ("gitlab_pages_basic", "Опубликуй документацию проекта через GitLab Pages.", 14),
        ("gitlab_pages_preview", "Сделай preview окружение для Merge Request через GitLab CI.", 18),
    ],
    4: [
        ("gitlab_release_notes", "Собери релиз с changelog и публикацией по git tag.", 18),
        ("gitlab_env_approval", "Добавь approval перед deploy в production environment.", 20),
    ],
    5: [
        ("gitlab_security_scan", "Подключи SAST/Dependency scanning и сделай fail на critical issues.", 20),
        ("gitlab_child_pipelines", "Разбей основной pipeline на child pipelines по подсистемам.", 22),
    ],
    6: [
        ("gitlab_monorepo_rules", "Настрой rules:changes для selective jobs в monorepo.", 24),
        ("gitlab_ci_optimize", "Оптимизируй тяжелый CI за счет needs/parallel и сравни время прогона.", 24),
    ],
}

THEORY_CONTENT = {
    1: """# Волшебство Git: старт без магии

Этот уровень опирается на первые разделы **«Волшебства Git»**: идея «сохранений как в игре», буферная зона и базовые операции.

## Ментальная модель

- **Рабочий каталог** — текущая «сцена»: файлы на диске, с которыми вы работаете.
- **Индекс (staging / буферная зона)** — список изменений, подготовленных к следующему коммиту.
- **Коммит** — неизменяемый снимок дерева файлов плюс метаданные (автор, сообщение, родители).

## Базовые рецепты

Ниже типичный порядок действий в новом проекте. Каждая команда — с определением; у флагов указано назначение.

### `git init`

**Определение:** создаёт в текущей папке каталог `.git` и пустой репозиторий: появляются ссылки на ветки, объекты и конфигурация. Без этого Git не отслеживает историю в каталоге.

```bash
git init
```

### `git add`

**Определение:** переносит изменения из рабочего каталога в **индекс** (staging). Пока файл не добавлен в индекс, он не попадёт в следующий коммит.

- **`git add .`** — добавить в индекс все изменения в текущем каталоге и подкаталогах (удобно после правок нескольких файлов). Точка — это путь «текущая папка».

```bash
git add .
```

### `git commit`

**Определение:** фиксирует текущее состояние индекса как новый коммит в истории текущей ветки.

- **`-m "текст"`** — задать **сообщение коммита** сразу в командной строке, без открытия редактора. Нужно для скриптов, CI и быстрых локальных снимков; сообщение должно осмысленно описывать изменение.

```bash
git commit -m "Первый снимок"
```

### `git status`

**Определение:** показывает, какие файлы изменены, что в индексе, что готово к коммиту, какая ветка активна.

- **`--short` (или `-s`)** — **краткий формат**: по одной строке на файл, первые два символа кодируют состояние *индекс / рабочее дерево* (например `M ` — изменён только в индексе, ` M` — только в рабочей копии, `MM` — и там и там). Удобно в длинных выводах и в скриптах.

```bash
git status --short
```

### `git diff`

**Определение:** показывает **непроиндексированные** различия между рабочим каталогом и индексом (что изменилось после последнего `git add`). Для сравнения индекса с последним коммитом используют `git diff --staged` (или `--cached`).

```bash
git diff
```

### `git log`

**Определение:** выводит историю коммитов текущей ветки (и доступных по ссылкам).

- **`--oneline`** — по **одному короткому идентификатору и одной строке сообщения** на коммит: компактный обзор ветки, удобно скроллить и копировать SHA.

```bash
git log --oneline
```

### Пример цепочки (как в рецепте)

```bash
git init
git add .
git commit -m "Первый снимок"
git status --short
git diff
git log --oneline
```

## Важные принципы из книги

- Коммить часто: «наводить порядок» можно позже.
- Перед рискованным шагом делай сохранение (коммит).
- Сначала проверяй состояние (`git status`), затем действуй.
""",
    2: """# Ветки как «кнопка босса»

В терминах Git Magic ветки — мгновенное переключение между альтернативными реальностями проекта. Ветка — это **именованный указатель на коммит**; `HEAD` показывает, на какой ветке (и коммите) вы сейчас.

## Команды ветвления и переключения

### `git checkout`

**Определение:** переключает рабочее дерево на указанную ветку или коммит (в старых рабочих процессах — основной способ сменить ветку).

- **`-b имя-ветки`** — **создать новую ветку** с указанным именем и **сразу переключиться** на неё (эквивалент `git branch` + `git checkout` в одном шаге).

```bash
git checkout -b boss
git checkout master
git checkout boss
```

### `git switch` (современная альтернатива)

**Определение:** явно переключает **только** ветку или коммит, без лишних смыслов `checkout`. **`git switch -c feature-x`** — создать ветку и переключиться (аналог `checkout -b`).

### `git branch`

**Определение:** без аргументов — список локальных веток; с именем — создать ветку. Активная ветка помечена `*`.

- **`-vv`** — **подробный список**: для каждой ветки показан последний коммит и **upstream** (отслеживаемая удалённая ветка), если настроен. Нужно, чтобы быстро увидеть «кто куда пушит» и не отстал ли локальный конец.

```bash
git branch -vv
```

## Практика из книги

- Используй короткие topic-ветки под одну цель.
- Для срочного фикса отделяй ветку `fixes` от старого коммита.
- Если работа временная — можно использовать `stash`, а не отдельную ветку.
""",
    3: """# Слияния, конфликты и интеграция

Этот уровень развивает идеи Git Magic о merge-конфликтах и непрерывном рабочем процессе.

## Как работает слияние

- Простые независимые правки сливаются автоматически.
- Конфликты требуют решения человеком.
- После ручного разрешения конфликтов изменения снова попадают в индекс и завершаются коммитом (для merge — отдельный merge-коммит, если не fast-forward).

## Команды интеграции

### `git merge`

**Определение:** вливает историю указанной ветки в **текущую**: переносит изменения, при необходимости создаёт merge-коммит.

- **`--no-ff`** — **запретить fast-forward**: даже если Git мог бы просто «передвинуть указатель», всё равно создаётся **отдельный merge-коммит** с двумя родителями. Зачем: в истории явно видно событие «ветка X была влита в main», удобно для code review и релизов.

- **`--abort`** — **отменить незавершённое слияние**: вернуть индекс и рабочее дерево к состоянию до `git merge`, если вы в процессе конфликта и решили начать заново.

```bash
git merge feature-x
git merge --no-ff feature-x
git merge --abort
```

### `git cherry-pick`

**Определение:** **переносит один (или несколько) выбранных коммитов** на текущую ветку, создавая *новые* коммиты с тем же диффом. Нужно для hotfix: взять конкретный патч из другой ветки, не сливая всю ветку целиком.

```bash
git cherry-pick abc1234
```

### `git revert`

**Определение:** создаёт **новый коммит**, который отменяет изменения указанного коммита (без переписывания истории). Безопасно для уже опубликованных веток. Для merge-коммитов часто нужен **`-m родитель`**, чтобы Git понял, какую линию истории считать «основной».

```bash
git revert abc1234
```

## Рабочий цикл

- Часто подтягивай изменения (`pull`/`fetch`).
- Держи коммиты мелкими и осмысленными.
- После интеграции проверяй граф: **`git log --graph --oneline`** — компактное дерево коммитов с ветвлениями и merge.

```bash
git log --graph --oneline
```
""",
    4: """# История под контролем: amend, rebase, stash, reset

Материал основан на разделах Git Magic «Уроки истории» и «Оставаясь корректным».

## Когда переписывать историю

- Пока изменения локальные и не опубликованы.
- Чтобы сгруппировать коммиты в логичные единицы.
- Чтобы исправить описания и структуру серии.

## Ключевые команды

### `git commit --amend`

**Определение:** **заменяет последний коммит**: можно добавить забытые файлы из индекса и/или изменить сообщение. История переписывается у конца ветки; не используйте на уже запушенных коммитах без согласования с командой.

```bash
git commit --amend
```

### `git rebase -i`

**Определение:** **интерактивный rebase** — переписать серию последних коммитов: поменять порядок, объединить (squash), разбить, отредактировать сообщения.

- **`-i`** — режим **интерактивного списка** инструкций (pick/reword/squash/…).
- **`HEAD~10`** — «последние 10 коммитов от текущего HEAD» как область переписывания (число подбирается под задачу).

```bash
git rebase -i HEAD~10
```

### `git stash`

**Определение:** временно **убирает незакоммиченные изменения** (рабочее дерево ± индекс) в стек, оставляя чистое дерево — чтобы переключить ветку или подтянуть remote.

### `git stash apply`

**Определение:** **восстанавливает** последнее (или указанное) сохранение из stash **без удаления** его из стека; `git stash pop` — восстановить и снять со стека.

```bash
git stash
git stash apply
```

### `git reset`

**Определение:** двигает указатель текущей ветки и по-разному обрабатывает индекс и рабочее дерево.

- **`--soft`** — только ветка откатывается к коммиту; **индекс и файлы** остаются как после «более новых» коммитов — удобно пересобрать коммиты.
- **`--mixed`** (по умолчанию) — ветка и **индекс** откатываются; рабочие файлы сохраняют изменения (**unstaged**).
- **`--hard`** — ветка, индекс и **рабочий каталог** приводятся к состоянию коммита: **несохранённые правки теряются**.

```bash
git reset --hard abc1234
```

### `git checkout` к коммиту (или `git switch --detach`)

**Определение:** перейти к коммиту в **detached HEAD** — «посмотреть прошлое» или собрать hotfix; новые коммиты здесь не привязаны к ветке, пока не создадите ветку. Вместо `abc1234` подставьте полный или короткий хэш.

```bash
git checkout abc1234
```

## Практическое правило

- `reset --hard` уничтожает несохранённые локальные изменения относительно целевого коммита.
- `checkout` / detached позволяют временно «уйти в прошлое».
- **`git reflog`** — журнал перемещений `HEAD`; помогает вернуть «потерянные» коммиты после reset.
""",
    5: """# Распределенная работа: clone, pull, push, bare

Уровень собран по главам Git Magic о распределенной модели, публикации и совместной работе.

## Основной поток

### `git clone`

**Определение:** **копирует удалённый репозиторий**: скачивает объекты, создаёт локальную ветку, настраивает `remote` с именем по умолчанию (`origin`) и рабочее дерево. Вместо URL ниже — адрес вашего сервера или путь к bare-репозиторию.

```bash
git clone https://example.com/project.git
```

### `git pull`

**Определение:** по умолчанию **`fetch` + слияние** в текущую ветку изменений с настроенного upstream. Смысл — «подтянуть чужие коммиты и обновить рабочую копию»; при расхождении истории возможны конфликты.

```bash
git pull
```

### `git push`

**Определение:** **отправляет** локальные коммиты текущей ветки на удалённый репозиторий и двигает тамошнюю ветку, если сервер разрешает fast-forward или настроен приём force-with-lease и т.д.

```bash
git push
```

### `git remote add`

**Определение:** добавляет **именованный URL** для обмена коммитами (например второй источник правды — форк и оригинал).

```bash
git remote add upstream https://example.com/upstream.git
```

### `git fetch`

**Определение:** **забирает объекты и ссылки** с remote, **не меняя** ваши локальные ветки и файлы — безопасное обновление «картины мира».

- **`--all`** — опросить **все** настроенные remotes.
- **`--prune`** — удалить локальные **удалённые ветки** (`origin/feature`), если на сервере ветку уже удалили: меньше путаницы в списках.

```bash
git fetch --all --prune
```

## Почему bare-хранилище

- **Bare** — репозиторий **без рабочего каталога**: только `.git`-данные, принято для серверных «центральных» копий.
- Разработчики работают в своих **non-bare** клонах.
- Публикация идёт в bare-узел, а не в чужой рабочий каталог.

## Практики команды

- Подтягивай перед push.
- Разрешай конфликты локально.
- Публикуй только «чистые» ветки и релевантные теги.
""",
    6: """# Глубины Git: bisect, blame, объекты, хуки

Финальный уровень отражает технические главы Git Magic: диагностика, внутренности и автоматизация.

## Диагностика

### `git bisect`

**Определение:** **двоичный поиск по коммитам**, чтобы найти первый «плохой» коммит между известно хорошей и плохой версией.

- **`start`** — начать сессию bisect.
- **`bad`** / **`good`** — пометить текущий (или указанный) коммит как сломанный или исправный; Git переключает HEAD на середину диапазона.
- **`git bisect run ./test.sh`** — автоматически помечать good/bad по **коду выхода** скрипта (0 = good, иначе bad): ускоряет поиск регрессии; вместо `./test.sh` — ваша команда проверки.

```bash
git bisect start
git bisect bad HEAD
git bisect good abc1234
git bisect run ./test.sh
```

### `git blame`

**Определение:** построчно показывает **какой коммит** последним менял строку и кто автор — для разбора «кто и когда внёс эту строку».

```bash
git blame src/module.py
```

## Внутренности

- Git хранит объекты: **`blob`** (содержимое файла), **`tree`** (список имён и ссылок на blob/tree), **`commit`** (снимок дерева, родители, метаданные).
- Целостность обеспечивается **SHA-1/SHA-256** идентификаторами объектов.

### `git cat-file -p`

**Определение:** **печатает содержимое** объекта по SHA в читаемом виде (`-p` — «pretty»). Зачем: увидеть сообщение коммита, дерево, raw blob без обхода через `log`/`show`.

### `git ls-tree`

**Определение:** выводит **содержимое дерева** (файлы и подкаталоги) для коммита или tree-объекта — «какой набор файлов был в этом снимке».

```bash
git cat-file -p abc1234
git ls-tree abc1234
```

### `git rev-parse`

**Определение:** превращает **имя в SHA** (ветка, `HEAD~3`, тег) — удобно в скриптах и для точных ссылок.

## Автоматизация и защита

- **`git config` с alias** — короткие имена для длинных команд (например `git st` → `status -sb`).
- **Хуки** (`hooks/`) — скрипты на события (`pre-commit`, `commit-msg`, …): блокируют плохие коммиты, запускают тесты, проверяют формат сообщения.
- **`git filter-repo`** / устаревший **`git filter-branch`** — переписать историю (удалить секрет из всех коммитов): требует force-push и согласования с командой; делайте только осознанно.
""",
    7: """# Гигиена репозитория: .gitignore и .gitkeep

Не всё, что находится в папке с вашим проектом, должно храниться в Git. Логи, временные файлы системы, папки вроде `node_modules` или секретные ключи доступа (`.env`) не только раздувают репозиторий, но и могут стать угрозой безопасности.

## .gitignore — Список исключений

**`.gitignore`** — это обычный текстовый файл в корне проекта, в который вы записываете шаблоны имен файлов и папок, которые Git должен полностью игнорировать.

* **Как это работает:** Git сверяется с этим файлом перед тем, как показать вам список измененных файлов в `git status`. Если файл подходит под шаблон в `.gitignore`, Git делает вид, что его не существует.
* **Что обычно добавляют:**
    * Конфиденциальные данные: `.env`, `secrets.json`.
    * Зависимости: `node_modules/`, `vendor/`, `target/`.
    * Системный мусор: `.DS_Store` (macOS), `Thumbs.db` (Windows).
    * Логи и временные файлы: `*.log`, `tmp/`.

### Примеры синтаксиса:
```bash
# Игнорировать конкретный файл
config.ini

# Игнорировать все файлы с расширением .log
*.log

# Игнорировать всю папку node_modules
node_modules/

# Игнорировать всё в папке logs, кроме файла README.md
logs/*
!logs/README.md
```

> **Важно:** `.gitignore` работает только для тех файлов, которые **ещё не были добавлены** в репозиторий. Если вы уже сделали коммит с файлом, а потом добавили его в игнор, Git продолжит его отслеживать. Чтобы это исправить, нужно удалить файл из индекса: `git rm --cached <file>`.

## .gitkeep — Сохранение пустых папок

В Git есть одна архитектурная особенность: **он не умеет отслеживать пустые папки**. Git следит за файлами, и если в папке нет ни одного файла, она просто не попадет в коммит.

Иногда вам нужно, чтобы папка существовала (например, `uploads/` или `logs/`), даже если она пока пуста. Для этого используется «костыль» под названием **`.gitkeep`**.

* **Что это:** Это не официальная команда Git, а общепринятое соглашение среди разработчиков. Вы просто создаете внутри пустой папки пустой файл с именем `.gitkeep`.
* **Результат:** Теперь папка содержит файл, а значит, Git её «увидит» и сохранит в истории.

## Различия в двух словах

| Файл | Назначение |
| :--- | :--- |
| **`.gitignore`** | Говорит Git: «Не смотри на эти файлы и не предлагай их сохранить». |
| **`.gitkeep`** | Говорит Git: «Сохрани эту папку, даже если в ней больше ничего нет». |

## Практический совет
Перед первым коммитом в новом проекте всегда заглядывайте на [gitignore.io](https://www.toptal.com/developers/gitignore). Там можно ввести название вашего языка программирования или IDE (например, `Python`, `Windows`, `PyCharm`), и сервис создаст для вас идеальный готовый файл `.gitignore`.
""",
    8: """# Работа с тегами: Фиксация версий

Теги в Git — это своего рода «закладки» в истории проекта. Если ветки постоянно двигаются вперёд, то теги остаются приклеенными к конкретным коммитам навсегда. Чаще всего их используют для фиксации версий (v1.0, v2.4.2).

В Git существует два типа тегов: **легковесные (lightweight)** и **аннотированные (annotated)**.

## 1. Типы тегов

### Легковесные теги
Это просто указатель на конкретный коммит. Представь это как временную наклейку «здесь был я». Они не хранят информацию о том, кто и когда их создал.
* **Команда:** `git tag v1.0-lw`

### Аннотированные теги
Это полноценные объекты в базе данных Git. Они имеют своё описание, автора, дату и даже могут быть подписаны электронной подписью. **Это стандарт для релизов.**
* **Команда:** `git tag -a v1.0 -m "Релиз первой стабильной версии"`

## 2. Основные операции

### Просмотр тегов
Чтобы увидеть список всех созданных тегов:
```bash
git tag
```
Для поиска конкретной серии (например, всех патчей версии 1):
```bash
git tag -l "v1.*"
```

### Просмотр данных тега
Если ты хочешь увидеть, кто поставил тег и какой код за ним скрывается:
```bash
git show v1.0
```

### Тегирование прошлых коммитов
Не обязательно ставить тег прямо сейчас. Если ты забыл пометить релиз вчера, просто укажи хэш нужного коммита:
```bash
git tag -a v1.2 abc1234 -m "Версия с исправлением бага"
```

## 3. Обмен тегами с сервером

По умолчанию команда `git push` **не отправляет** теги на удалённый сервер. Это частая ошибка новичков: тег создан локально, но на GitHub его нет.

* **Отправить конкретный тег:**
  ```bash
  git push origin v1.0
  ```
* **Отправить все теги разом:**
  ```bash
  git push origin --tags
  ```

## 4. Удаление и исправление

* **Удалить локально:** `git tag -d v1.0`
* **Удалить на сервере:** `git push origin --delete v1.0`

> **Важно:** Старайся не переставлять теги. Если версия `v1.0` уже ушла в мир, а ты нашел ошибку — сделай новый коммит и назови его `v1.0.1`. Тег должен гарантировать, что код под этим именем неизменен.

### Практический совет
Используй **семантическое версионирование** (Semantic Versioning). Это формат `X.Y.Z` (Мажорная.Минорная.Патч).
- `1.0.0` — первый релиз.
- `1.0.1` — исправили опечатку.
- `1.1.0` — добавили новую кнопку.
- `2.0.0` — полностью переписали интерфейс.
""",
}

LEVEL_SECTION_HINTS = {
    1: (
        "Работай по циклу из книги: status -> add -> commit -> log.",
        "Буферная зона — ключ к управлению изменениями перед коммитом.",
    ),
    2: (
        "Ветка — это быстрый способ переключить контекст без клонирования каталога.",
        "Для срочных задач создавай отдельную ветку, а затем делай слияние.",
    ),
    3: (
        "Конфликт слияния решается вручную, потом изменения нужно повторно добавить в буфер.",
        "После merge проверь граф истории и убедись, что коммиты связаны ожидаемо.",
    ),
    4: (
        "Используй rebase -i чтобы собрать историю в читаемую последовательность.",
        "Перед reset --hard создай страховочную ветку или пометь текущий SHA.",
    ),
    5: (
        "Проверяй remotes через git remote -v и отслеживай ветки через git branch -vv.",
        "Безопасный цикл: fetch -> review -> merge/rebase -> push.",
    ),
    6: (
        "При поиске регрессии используй бинарный подход bisect, а не линейный перебор.",
        "Для контроля качества подключай pre-commit и commit-msg хуки.",
    ),
}

LEVEL_DIAGRAMS = {
    1: "flowchart LR\n  worktree[Working tree] --> index[Index]\n  index --> commit[Commit]\n  commit --> log[git log]",
    2: "graph LR\n  main[main] --> C1\n  C1 --> C2\n  C1 --> Fx1[feature-x]\n  Fx1 --> Fx2\n  main -. checkout .-> Fx2",
    3: "graph LR\n  M1 --> M2\n  M2 --> F1\n  M2 --> M3\n  F1 --> F2\n  M3 --> Merge((merge))\n  F2 --> Merge",
    4: "flowchart TD\n  A[commit A] --> B[commit B]\n  B --> C[commit C]\n  C --> D[commit D]\n  D --> R[rebase -i]\n  R --> C2[clean history]",
    5: "graph LR\n  Dev[local repo] -- push --> Origin[(origin)]\n  Origin -- fetch --> Dev\n  Origin -- fetch --> UpstreamClone[teammate clone]\n  Dev -- fetch upstream --> Upstream[(upstream)]",
    6: "flowchart LR\n  Bad[regression] --> Bisect[git bisect]\n  Bisect --> Good[good commit]\n  Bisect --> Bad2[bad commit]\n  Good --> Fix[fix + hook]\n  Fix --> Objects[cat-file / ls-tree]",
    7: "flowchart TB\n  A[Рабочая папка проекта] --> B{Файл/папка нужен в истории?}\n  B -- Нет --> C[Добавить шаблон в .gitignore]\n  B -- Да --> D{Папка пустая?}\n  D -- Да --> E[Добавить .gitkeep]\n  D -- Нет --> F[Коммитить как обычно]\n  C --> G[Чистый git status]\n  E --> G\n  F --> G",
    8: "graph LR\n    C1((C1)) --> C2((C2))\n    C2 --> C3((C3))\n    T1[tag: v0.1] --- C1\n    T2[tag: v1.0] --- C3\n    C3 --> C4((C4))\n    main[Ветка: main] --- C4\n    classDef tagStyle fill:#fff9c4,stroke:#fbc02d,color:#000\n    class T1,T2 tagStyle",
}

TASK_VALIDATORS = {
    "1.1": """\
import sys
import subprocess
from pathlib import Path

if not Path('.git').exists():
    print('Repository is not initialized')
    sys.exit(1)
subprocess.run(['git', 'rev-parse', '--git-dir'], check=True, capture_output=True, text=True)
print('OK: repository initialized')
""",
    "1.2": """\
import sys
import subprocess

msg = subprocess.run(['git', 'log', '-1', '--pretty=%s'], capture_output=True, text=True, check=False)
if msg.returncode != 0 or msg.stdout.strip() != 'Add hello':
    print('Expected last commit message: Add hello')
    sys.exit(1)

file_content = subprocess.run(['git', 'show', 'HEAD:hello.txt'], capture_output=True, text=True, check=False)
if file_content.returncode != 0 or file_content.stdout.strip() != 'Hello, Git!':
    print('hello.txt content mismatch in HEAD')
    sys.exit(1)
print('OK')
""",
    "1.3": """\
import sys
import subprocess

status = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True, check=False).stdout
if ' M hello.txt' not in status:
    print('hello.txt should be modified and unstaged')
    sys.exit(1)
print('OK')
""",
    "1.4": """\
import sys
import subprocess

status = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True, check=False).stdout
if ' M hello.txt' not in status:
    print('Expected unstaged modification after unstage step')
    sys.exit(1)
print('OK')
""",
    "1.5": """\
import sys
import subprocess

count = subprocess.run(['git', 'rev-list', '--count', 'HEAD'], capture_output=True, text=True, check=False)
if count.returncode != 0 or int(count.stdout.strip()) < 2:
    print('Expected at least two commits')
    sys.exit(1)
msg = subprocess.run(['git', 'log', '-1', '--pretty=%s'], capture_output=True, text=True, check=False).stdout.strip()
if msg != 'Update hello':
    print('Expected latest commit message Update hello')
    sys.exit(1)
print('OK')
""",
    "1.6": """\
import sys
import subprocess

diff = subprocess.run(['git', 'diff'], capture_output=True, text=True, check=False).stdout
if 'Another line' not in diff:
    print('Expected Another line in git diff')
    sys.exit(1)
print('OK')
""",
    "1.7": """\
import sys
import subprocess

show = subprocess.run(['git', 'show', '--name-only', '--pretty=', 'HEAD'], capture_output=True, text=True, check=False).stdout
if 'config.txt' not in show:
    print('config.txt must be part of amended commit')
    sys.exit(1)
print('OK')
""",
    "1.8": """\
import sys
import subprocess

count = subprocess.run(['git', 'rev-list', '--count', 'HEAD'], capture_output=True, text=True, check=False)
if count.returncode != 0 or int(count.stdout.strip()) < 2:
    print('Need at least two commits to inspect history')
    sys.exit(1)
print('OK')
""",
    "2.1": """\
import sys
import subprocess

branch = subprocess.run(['git', 'branch', '--show-current'], capture_output=True, text=True, check=False).stdout.strip()
if branch != 'feature-x':
    print('Current branch should be feature-x')
    sys.exit(1)
print('OK')
""",
    "2.2": """\
import sys
import subprocess

show = subprocess.run(['git', 'show', '--name-only', '--pretty=', 'HEAD'], capture_output=True, text=True, check=False).stdout
if 'feature.txt' not in show:
    print('feature.txt should be committed in HEAD')
    sys.exit(1)
print('OK')
""",
    "2.3": """\
import sys
import subprocess
from pathlib import Path

branch = subprocess.run(['git', 'branch', '--show-current'], capture_output=True, text=True, check=False).stdout.strip()
if branch != 'main':
    print('Switch back to main')
    sys.exit(1)
if Path('feature.txt').exists():
    print('feature.txt should not exist in main worktree')
    sys.exit(1)
print('OK')
""",
    "3.1": """\
import sys
import subprocess

parents = subprocess.run(['git', 'rev-list', '--parents', '-n', '1', 'HEAD'], capture_output=True, text=True, check=False).stdout.strip().split()
if len(parents) != 2:
    print('Expected fast-forward without merge commit')
    sys.exit(1)
print('OK')
""",
    "3.2": """\
import sys
import subprocess

parents = subprocess.run(['git', 'rev-list', '--parents', '-n', '1', 'HEAD'], capture_output=True, text=True, check=False).stdout.strip().split()
if len(parents) < 3:
    print('Expected merge commit with two parents')
    sys.exit(1)
print('OK')
""",
    "3.3": """\
import sys
import subprocess

status = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True, check=False).stdout
if 'UU ' in status:
    print('Conflicts are not fully resolved')
    sys.exit(1)
print('OK')
""",
}


def _validator_by_slug(slug: str, external_id: str) -> str:
    if slug in {"list_branches"}:
        return "import subprocess, sys\nr=subprocess.run(['git','branch'],capture_output=True,text=True);sys.exit(0 if '*' in r.stdout else 1)"
    if slug in {"delete_branch"}:
        return "import subprocess, sys\nr=subprocess.run(['git','branch'],capture_output=True,text=True).stdout\nsys.exit(0 if 'feature-x' not in r else 1)"
    if slug in {"rename_branch"}:
        return "import subprocess, sys\nb=subprocess.run(['git','branch','--show-current'],capture_output=True,text=True).stdout.strip();sys.exit(0 if b and b!='main' else 1)"
    if slug in {"setup_ignore"}:
        return "from pathlib import Path\nimport sys\nc=Path('.gitignore').read_text(encoding='utf-8') if Path('.gitignore').exists() else ''\nsys.exit(0 if '*.log' in c and '__pycache__/' in c else 1)"
    if slug in {"create_tag", "push_tags"}:
        return "import subprocess, sys\nr=subprocess.run(['git','tag','-l','v1.0'],capture_output=True,text=True).stdout.strip();sys.exit(0 if r=='v1.0' else 1)"
    if slug in {"view_history", "branch_compare", "branch_from_commit", "track_remote_branch"}:
        return "import subprocess, sys\nr=subprocess.run(['git','rev-list','--count','HEAD'],capture_output=True,text=True,check=False)\nsys.exit(0 if r.returncode==0 and int((r.stdout or '0').strip() or 0)>=1 else 1)"
    if slug in {"switch_branch"}:
        return TASK_VALIDATORS["2.3"]
    if slug in {"commit_on_branch"}:
        return TASK_VALIDATORS["2.2"]
    if slug in {"create_branch"}:
        return TASK_VALIDATORS["2.1"]
    if slug in {"fast_forward_merge"}:
        return TASK_VALIDATORS["3.1"]
    if slug in {"no_ff_merge"}:
        return TASK_VALIDATORS["3.2"]
    if slug in {"resolve_conflict"}:
        return TASK_VALIDATORS["3.3"]
    if slug in {"abort_merge"}:
        return "import subprocess, sys\nr=subprocess.run(['git','status','--porcelain'],capture_output=True,text=True).stdout\nsys.exit(0 if 'UU ' not in r else 1)"
    if slug in {"merge_tool", "octopus_merge", "squash_merge", "merge_vs_rebase", "cherry_pick_hotfix", "revert_merge"}:
        return "import subprocess, sys\nr=subprocess.run(['git','status','--porcelain'],capture_output=True,text=True)\nsys.exit(0 if r.returncode==0 else 1)"
    if slug in {"amend_message"}:
        return "import subprocess, sys\nm=subprocess.run(['git','log','-1','--pretty=%s'],capture_output=True,text=True).stdout.strip();sys.exit(0 if m else 1)"
    if slug in {"reorder_commits", "squash_commits", "drop_commit", "edit_commit", "rebase_onto"}:
        return "import subprocess, sys\nr=subprocess.run(['git','log','--oneline','-n','3'],capture_output=True,text=True);sys.exit(0 if r.returncode==0 else 1)"
    if slug in {"stash_workflow"}:
        return "import subprocess, sys\nr=subprocess.run(['git','stash','list'],capture_output=True,text=True);sys.exit(0 if r.returncode==0 else 1)"
    if slug in {"reset_modes"}:
        return "import subprocess, sys\nr=subprocess.run(['git','reflog','-n','5'],capture_output=True,text=True);sys.exit(0 if r.returncode==0 and bool(r.stdout.strip()) else 1)"
    if slug in {"clone_local", "add_remote", "push_first", "fetch_merge", "pull_rebase", "push_conflict", "remote_prune"}:
        return "import subprocess, sys\nr=subprocess.run(['git','remote','-v'],capture_output=True,text=True);sys.exit(0 if r.returncode==0 else 1)"
    if slug in {"find_bisect", "reflog_recovery", "filter_branch", "worktree", "submodule", "inspect_objects", "custom_aliases_hooks"}:
        return "import subprocess, sys\nr=subprocess.run(['git','status','--porcelain'],capture_output=True,text=True);sys.exit(0 if r.returncode==0 else 1)"
    if slug in {"init_repo", "first_commit", "check_status", "stage_unstage", "commit_second", "view_diff", "amend_commit"}:
        reverse_lookup = {
            "init_repo": "1.1",
            "first_commit": "1.2",
            "check_status": "1.3",
            "stage_unstage": "1.4",
            "commit_second": "1.5",
            "view_diff": "1.6",
            "amend_commit": "1.7",
        }
        mapped = reverse_lookup.get(slug)
        if mapped and mapped in TASK_VALIDATORS:
            return TASK_VALIDATORS[mapped]
    return "import subprocess, sys\nr=subprocess.run(['git','status','--porcelain'],capture_output=True,text=True)\nsys.exit(0 if r.returncode==0 else 1)"


def validator_for(external_id: str, slug: str) -> str:
    return TASK_VALIDATORS.get(external_id) or _validator_by_slug(slug, external_id)


def task_metadata(level_number: int, slug: str, description: str, platform: str = "github") -> dict:
    requires = []
    if slug != "init_repo":
        requires.append("repo_initialized")
    if slug in {"check_status", "stage_unstage", "commit_second", "view_diff", "amend_commit", "view_history"}:
        requires.append("hello_committed")
    if slug in {"commit_on_branch", "switch_branch", "list_branches", "delete_branch"}:
        requires.extend(["hello_committed", "feature_branch_exists"])
    return {
        "objective": description,
        "platform": platform,
        "playground_subtitle": (
            f"{slug.replace('_', ' ').title()} · Режим обучения: приоритет у команд git; "
            "для подготовки файлов разрешены безопасные команды echo/touch."
        ),
        "steps": [
            "Проверь стартовое состояние через git status --short.",
            "Выполни требуемые команды из условия.",
            "Подтверди результат через git status/git log и запусти проверку.",
        ],
        "expected_state": "Состояние репозитория соответствует формулировке задания.",
        "preconditions": requires,
        "validatorHints": ["Проверка опирается на состояние репозитория и историю коммитов."],
        "start": {
            "mode": "guided",
            "requires": requires,
            "assumes": [f"level_{level_number}_context"],
        },
        "recommendations": [
            "Начинай с git status, чтобы увидеть исходную точку.",
            "После каждого шага сверяйся с git log --oneline --graph.",
        ],
    }


def _zip_workspace(repo: Path) -> str:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for item in repo.rglob("*"):
            if item.is_file():
                archive.write(item, item.relative_to(repo))
    return f"base64zip:{base64.b64encode(buffer.getvalue()).decode('ascii')}"


def build_start_repo_asset(slug: str) -> str | None:
    if slug not in {"check_status", "stage_unstage", "commit_second", "view_diff", "amend_commit", "view_history"}:
        return None
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td) / "repo"
        repo.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init"], cwd=repo, check=False, capture_output=True, text=True)
        subprocess.run(
            ["git", "config", "user.email", "gitplayground@example.local"],
            cwd=repo,
            check=False,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "GitPlayground Bot"],
            cwd=repo,
            check=False,
            capture_output=True,
            text=True,
        )
        (repo / "hello.txt").write_text("Hello, Git!\n", encoding="utf-8")
        subprocess.run(["git", "add", "hello.txt"], cwd=repo, check=False, capture_output=True, text=True)
        subprocess.run(["git", "commit", "-m", "Add hello"], cwd=repo, check=False, capture_output=True, text=True)
        return _zip_workspace(repo)


def revision_payload(task: Task) -> dict:
    level_hint = {
        1: "Сфокусируйся на базовой механике хранилища и буферной зоны.",
        2: "Тренируй мгновенное переключение контекста через ветки.",
        3: "Отработай безопасную интеграцию изменений и разбор конфликтов.",
        4: "Научись аккуратно переписывать историю без потери контроля.",
        5: "Применяй распределенную модель: локально работаешь, в remote публикуешь.",
        6: "Используй диагностические и низкоуровневые инструменты Git.",
    }.get(task.level.number, "")
    objective = f"{task.description}\n\nКонтекст раздела: {level_hint}"
    metadata = task.metadata or {}
    steps = metadata.get(
        "steps",
        [
            "Проверь текущее состояние репозитория через git status --short.",
            "Выполни целевое действие из формулировки задачи.",
            "Подтверди результат через git status/git log и запусти проверку.",
        ],
    )
    expected_state = metadata.get(
        "expected_state",
        "Репозиторий находится в требуемом состоянии без лишних изменений.",
    )
    validator_notes = "Проверка использует validator.py и состояние Git-репозитория."
    return {
        "objective": objective,
        "steps": steps,
        "expected_state": expected_state,
        "validator_notes": validator_notes,
        "schema_version": 1,
    }


class Command(BaseCommand):
    help = "Seed levels, theory blocks and task records with enriched GitMagic content."

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        created_tasks = 0
        created_assets = 0
        for level_number, level_title, task_count in LEVELS:
            level_slug = f"level-{level_number}-{slugify(level_title)}"
            level, _ = Level.objects.update_or_create(
                number=level_number,
                defaults={
                    "title": level_title,
                    "slug": level_slug,
                    "description": f"Блок {level_number}: {level_title}",
                    "is_active": True,
                },
            )

            # DB data is source of truth: не перетираем уже отредактированную теорию.
            TheoryBlock.objects.get_or_create(
                level=level,
                defaults={
                    "title": f"Теория: {level_title}",
                    "content_md": THEORY_CONTENT[level_number],
                    "diagram_mermaid": LEVEL_DIAGRAMS[level_number],
                },
            )

            for platform, blueprints in (
                ("github", TASK_BLUEPRINTS.get(level_number, [])),
                ("gitlab", GITLAB_BLUEPRINTS.get(level_number, [])),
            ):
                for order, (slug, description, points) in enumerate(blueprints, start=1):
                    metadata = task_metadata(level_number, slug, description, platform=platform)
                    defaults = {
                        "slug": slug,
                        "title": slug.replace("_", " ").title(),
                        "description": description,
                        "platform": platform,
                        "level": level,
                        "order": order,
                        "points": points,
                        "validator_cmd": "python validator.py",
                        "success_message": "Отлично! Задача решена.",
                        "metadata": metadata,
                    }
                    task = Task.objects.filter(external_id=f"{platform[:2]}-{level_number}.{order}").first()
                    if task is None:
                        task = Task.objects.filter(level=level, platform=platform, order=order).first()
                    if task is None:
                        task = Task.objects.create(
                            external_id=f"{platform[:2]}-{level_number}.{order}",
                            **defaults,
                        )
                    else:
                        for key, value in defaults.items():
                            setattr(task, key, value)
                        task.external_id = f"{platform[:2]}-{level_number}.{order}"
                        task.save()
                    revision, _ = TaskRevision.objects.update_or_create(
                        task=task,
                        version=1,
                        defaults={
                            "is_active": True,
                            **revision_payload(task),
                        },
                    )
                    TaskRevision.objects.filter(task=task).exclude(pk=revision.pk).update(is_active=False)
                    start_repo_payload = build_start_repo_asset(slug)
                    if start_repo_payload:
                        TaskAsset.objects.update_or_create(
                            task=task,
                            asset_type=TaskAsset.AssetType.START_REPO,
                            path="start-repo.zip",
                            defaults={
                                "sort_order": 1,
                                "content": start_repo_payload,
                            },
                        )
                    else:
                        TaskAsset.objects.filter(task=task, asset_type=TaskAsset.AssetType.START_REPO).delete()
                    TaskAsset.objects.update_or_create(
                        task=task,
                        asset_type=TaskAsset.AssetType.VALIDATOR,
                        path="validator.py",
                        defaults={
                            "sort_order": 1,
                            "content": validator_for(task.external_id, slug),
                        },
                    )
                    TaskAsset.objects.update_or_create(
                        task=task,
                        asset_type=TaskAsset.AssetType.HINT,
                        path="hints/hint1.txt",
                        defaults={
                            "sort_order": 1,
                            "content": LEVEL_SECTION_HINTS[level_number][0],
                        },
                    )
                    TaskAsset.objects.update_or_create(
                        task=task,
                        asset_type=TaskAsset.AssetType.HINT,
                        path="hints/hint2.txt",
                        defaults={
                            "sort_order": 2,
                            "content": LEVEL_SECTION_HINTS[level_number][1],
                        },
                    )
                    created_tasks += 1
                    created_assets += 3

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete: {len(LEVELS)} levels, {created_tasks} tasks, {created_assets} assets."
            )
        )
