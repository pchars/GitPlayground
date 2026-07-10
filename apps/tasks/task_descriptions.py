"""Per-task condition text shown in the playground (objective block).

Условия формулируют цель и обязательные детали (имена файлов, веток, тегов,
сообщения коммитов), но намеренно не разжёвывают точную команду — она доступна
в подсказках (`task_hints.py`) и в теории уровня.
"""

from __future__ import annotations

FILE_CREATE_HINT = (
    " Файлы: одна строка — `echo текст > имя` или `touch имя`; несколько строк — "
    "`nano имя` (Ctrl+S — сохранить, Ctrl+X — выйти)."
)

FILE_EDIT_HINT = (
    " Правка файла: `nano имя` (Ctrl+S — сохранить, Ctrl+X — выйти)."
)

_FILE_CREATE_SLUGS = frozenset(
    {
        "first_commit",
        "amend_commit",
        "grep_in_repo",
        "stage_tracked_only",
        "diff_cached_staged",
        "commit_on_branch",
        "branch_without_checkout",
        "rescue_detached_head",
        "merge_base_ready",
        "save_symbolic_head",
        "tree_list_root",
        "attach_git_note",
        "rev_parse_head_sha",
        "log_double_dot_range",
        "pickaxe_log_search",
        "triple_dot_log_range",
        "setup_ignore",
        "ignore_node_modules",
        "ignore_exceptions",
        "keep_empty_dir",
        "clean_untracked",
        "readme_first",
        "gh_pages_branch",
        "jekyll_post_front_matter",
        "write_git_blob",
        "mr_feature_branch",
        "add_gitlab_ci_yaml",
        "gitlab_md_issue_ref",
    }
)

_FILE_EDIT_SLUGS = frozenset(
    {
        "check_status",
        "stage_unstage",
        "view_diff",
        "commit_second",
        "reset_head_unstage",
        "resolve_conflict",
        "edit_commit",
    }
)


def _with_file_hints(conditions: dict[str, str]) -> dict[str, str]:
    enriched: dict[str, str] = {}
    for slug, text in conditions.items():
        suffix = ""
        if slug in _FILE_CREATE_SLUGS:
            suffix = FILE_CREATE_HINT
        elif slug in _FILE_EDIT_SLUGS:
            suffix = FILE_EDIT_HINT
        enriched[slug] = text + suffix
    return enriched


_RAW_TASK_CONDITIONS: dict[str, str] = {
    # Level 1 — basics
    "init_repo": (
        "Преврати текущую папку в Git-репозиторий. После этого в ней должен "
        "появиться служебный каталог `.git`."
    ),
    "first_commit": (
        "Создай файл `hello.txt` с единственной строкой `Hello, Git!`, "
        "добавь его под контроль версий и зафиксируй первым коммитом "
        "с сообщением `Add hello`."
    ),
    "check_status": (
        "Измени `hello.txt`, но не добавляй правку в индекс. Убедись, что Git "
        "видит файл как изменённый, но не подготовленный к коммиту (статус ` M`)."
    ),
    "stage_unstage": (
        "Измени `hello.txt` и добавь его в индекс, затем сними файл из индекса, "
        "сохранив саму правку. Итог: файл изменён, но не подготовлен к коммиту "
        "(статус ` M`). Важно снять из индекса, не откатывая изменения."
    ),
    "view_diff": (
        "Добавь в `hello.txt` строку `Another line` и, не коммитя её, посмотри "
        "незакоммиченные изменения — добавленная строка должна быть видна в diff."
    ),
    "commit_second": (
        "Внеси ещё одну правку в `hello.txt` и зафиксируй её вторым коммитом "
        "с сообщением `Update hello`."
    ),
    "amend_commit": (
        "Создай файл `config.txt` и включи его в последний коммит, "
        "не создавая новый."
    ),
    "view_history": "Выведи историю коммитов в компактном однострочном виде.",
    "grep_in_repo": (
        "Найди в отслеживаемых файлах строку `Git` командой `git grep` "
        "и запиши одну найденную строку (формат `файл:текст`) в файл `grep-hit.txt`."
    ),
    "stage_tracked_only": (
        "Измени `hello.txt`, создай неотслеживаемый `scratch.txt` и закоммить "
        "только изменения уже отслеживаемых файлов (`git add -u`), не добавляя `scratch.txt`."
    ),
    "reset_head_unstage": (
        "Измени `hello.txt`, добавь в индекс, затем сними с индекса через "
        "`git reset HEAD hello.txt` (без `git restore`)."
    ),
    "diff_cached_staged": (
        "Измени `hello.txt`, добавь в индекс (`git add`) и создай маркер "
        "`staged-ready.txt` — валидатор проверит непустой `git diff --cached`."
    ),
    # Level 2 — branching
    "create_branch": "Создай новую ветку `feature-x` и переключись на неё.",
    "commit_on_branch": (
        "Находясь на ветке `feature-x`, создай файл `feature.txt` "
        "и зафиксируй его коммитом."
    ),
    "switch_branch": (
        "Вернись на ветку `main`. Файла `feature.txt` не должно быть "
        "в рабочей папке."
    ),
    "list_branches": (
        "Выведи список всех веток и определи, на какой ты находишься сейчас."
    ),
    "rename_branch": (
        "Переименуй текущую ветку (она не должна называться `main`) "
        "в более понятное имя."
    ),
    "branch_from_commit": (
        "Найди в истории нужный коммит по его SHA и создай от него новую ветку."
    ),
    "delete_branch": (
        "Удали неактивную ветку `feature-x`, предварительно переключившись "
        "на другую ветку."
    ),
    "branch_without_checkout": (
        "Создай ветку `sidecar` командой `git branch`, не переключаясь с `main`, "
        "и запиши имя текущей ветки в `active-branch.txt`."
    ),
    "rescue_detached_head": (
        "Перейди в detached HEAD (`git checkout --detach`), затем создай ветку "
        "`rescue-tip` и запиши её имя в `rescue-branch.txt`."
    ),
    # Level 3 — merges
    "fast_forward_merge": (
        "Влей ветку `feature` в `main` так, чтобы слияние прошло перемоткой "
        "(fast-forward), без отдельного merge-коммита."
    ),
    "no_ff_merge": (
        "Влей ветку `feature` в `main` так, чтобы обязательно образовался "
        "отдельный merge-коммит с двумя родителями."
    ),
    "resolve_conflict": (
        "Заверши начатое слияние: устрани конфликты в файлах, отметь их "
        "как решённые и корректно закончи merge."
    ),
    "abort_merge": (
        "Прерви незавершённое слияние и верни репозиторий в состояние до merge."
    ),
    "squash_merge": (
        "Влей изменения ветки одним общим коммитом (squash), "
        "а не набором отдельных коммитов."
    ),
    "cherry_pick_hotfix": (
        "Перенеси на текущую ветку один конкретный коммит из другой ветки "
        "по его SHA."
    ),
    "revert_merge": (
        "Отмени ранее сделанный merge-коммит, создав обратный коммит "
        "(учти, что у merge два родителя)."
    ),
    "merge_base_ready": (
        "Создай ветку `prof-feature`, сделай на ней коммит и убедись, что "
        "`git merge-base main HEAD` возвращает общий предок; создай маркер `merge-base-done.txt`."
    ),
    # Level 4 — history rewriting
    "amend_message": (
        "Измени сообщение последнего коммита, не создавая новый коммит."
    ),
    "reorder_commits": (
        "С помощью интерактивного rebase поменяй порядок последних коммитов."
    ),
    "squash_commits": (
        "С помощью интерактивного rebase объедини несколько последних коммитов "
        "в один."
    ),
    "edit_commit": (
        "В ходе интерактивного rebase остановись на нужном коммите, внеси правку "
        "и продолжи перебазирование."
    ),
    "stash_workflow": (
        "Временно спрячь незакоммиченные изменения, а затем верни их обратно "
        "в рабочую копию."
    ),
    "reset_modes": (
        "Покажи на практике разницу между режимами сброса `--soft`, `--mixed` "
        "и `--hard`."
    ),
    # Level 5 — remotes
    "clone_local": "Склонируй репозиторий в новую папку.",
    "add_remote": (
        "Добавь репозиторию удалённый источник с именем `upstream` "
        "и проверь, что он появился в списке remotes."
    ),
    "push_first": (
        "Опубликуй свою ветку в удалённом репозитории первым push "
        "с привязкой к upstream."
    ),
    "fetch_merge": (
        "Подтяни изменения из удалённого репозитория и влей их в текущую ветку "
        "вручную (без `git pull`)."
    ),
    "pull_rebase": (
        "Настрой получение изменений через rebase и подтяни обновления."
    ),
    "push_conflict": (
        "Push отклонён из-за расхождения истории (non-fast-forward). "
        "Интегрируй удалённые изменения и повтори публикацию."
    ),
    "create_offline_bundle": (
        "Создай офлайн-пакет `repo.bundle` из текущей ветки `main` "
        "(команда `git bundle create`)."
    ),
    # Level 6 — diagnostics
    "find_bisect": (
        "С помощью бинарного поиска по истории найди первый «плохой» коммит, "
        "где появилась регрессия."
    ),
    "reflog_recovery": (
        "Найди в журнале ссылок потерянный коммит и восстанови его."
    ),
    "worktree": (
        "Создай отдельную рабочую копию для параллельной работы "
        "над hotfix-веткой."
    ),
    "inspect_objects": (
        "Изучи внутренние объекты Git: определи тип и содержимое объекта "
        "и просмотри дерево коммита."
    ),
    "custom_aliases_hooks": (
        "Создай псевдоним (alias) для git-команды и локальный хук `commit-msg`."
    ),
    "filter_branch": (
        "Полностью удали файл из всей истории репозитория, переписав "
        "прошлые коммиты."
    ),
    "save_symbolic_head": (
        "Создай ветку `internals-demo` и запиши в `head-ref.txt` результат "
        "`git symbolic-ref HEAD` (куда указывает HEAD)."
    ),
    "tree_list_root": (
        "Создай `tree-list.txt` со списком имён файлов в корне `HEAD` "
        "(по одному на строку), как в `git ls-tree --name-only HEAD`."
    ),
    "attach_git_note": (
        "Добавь к `HEAD` git note с текстом `reviewed` и запиши тот же текст "
        "в `note-check.txt`."
    ),
    "rev_parse_head_sha": (
        "Выполни `git rev-parse --abbrev-ref HEAD` и запиши имя ветки в `current-branch.txt` "
        "(через `echo`, без shell-редиректа из git)."
    ),
    "log_double_dot_range": (
        "Создай ветку `explore-range`, сделай на ней коммит (чтобы `git log main..HEAD` "
        "был непустым) и создай маркер `range-done.txt`."
    ),
    "pickaxe_log_search": (
        "Добавь в `hello.txt` уникальную строку `PROGIT_FIND`, закоммить и создай "
        "маркер `pickaxe-done.txt` — валидатор проверит `git log -S PROGIT_FIND`."
    ),
    "triple_dot_log_range": (
        "Создай ветку `triple-explore`, сделай коммит и маркер `triple-done.txt` — "
        "валидатор проверит непустой `git log main...HEAD`."
    ),
    # Level 7 — hygiene
    "setup_ignore": (
        "Настрой `.gitignore`, чтобы Git игнорировал логи `*.log`, файл `.env` "
        "и папку `__pycache__/`."
    ),
    "ignore_node_modules": (
        "Добавь правило в `.gitignore`, чтобы Git игнорировал папку "
        "`node_modules/`."
    ),
    "untrack_cached": (
        "Перестань отслеживать уже добавленный в Git файл, "
        "но не удаляй его с диска."
    ),
    "keep_empty_dir": (
        "Добейся, чтобы пустая папка сохранилась в Git "
        "(Git не хранит пустые каталоги сами по себе)."
    ),
    "ignore_exceptions": (
        "Настрой `.gitignore` так, чтобы игнорировались все `*.log`, "
        "кроме одного конкретного файла."
    ),
    "clean_untracked": (
        "Создай неотслеживаемый `garbage.tmp` и удали его командой `git clean` "
        "(сначала посмотри список через `git clean -n`)."
    ),
    # Level 8 — tagging
    "create_lightweight_tag": (
        "Поставь на текущий коммит лёгкий (lightweight) тег `v0.1-lw`."
    ),
    "create_tag": (
        "Создай на текущем коммите аннотированный тег `v1.0` с сообщением."
    ),
    "show_tag": "Выведи подробную информацию о теге `v1.0`.",
    "tag_old_commit": (
        "Поставь тег на конкретный прошлый коммит, указав его SHA."
    ),
    "push_tags": (
        "Подготовь релизный тег `v1.0` с сообщением. В песочнице сеть отключена, "
        "поэтому проверяется наличие локального тега."
    ),
    # Level 9 — platforms & pro practices
    "export_format_patch": (
        "Экспортируй последний коммит в файл патча (`git format-patch`). "
        "В корне репозитория должен появиться файл с расширением `.patch`."
    ),
    "git_mv_rename": (
        "Переименуй отслеживаемый файл `hello.txt` в `readme.txt` через `git mv`, "
        "закоммить переименование. Файл `hello.txt` не должен остаться в индексе."
    ),
    "commit_signoff": (
        "Сделай коммит с правкой и строкой **Signed-off-by** (`git commit -s`). "
        "Проверяется тело последнего коммита."
    ),
    "semantic_describe": (
        "Создай аннотированный тег `v1.0.0` и выполни `git describe --tags`. "
        "Вывод describe должен содержать `v1.0.0`."
    ),
    "readme_first": (
        "Создай файл `README.md` в корне с заголовком проекта (строка с `#`) "
        "и закоммить его — как первый шаг публикации на GitHub."
    ),
    "issue_close_message": (
        "Сделай коммит с сообщением, содержащим `Fixes #42` — так GitHub "
        "автоматически закроет issue при merge (в песочнице проверяется текст коммита)."
    ),
    "gh_pages_branch": (
        "Создай ветку `gh-pages`, добавь `index.html` с любым содержимым и закоммить. "
        "Это конвенция GitHub Pages для project site."
    ),
    "jekyll_post_front_matter": (
        "Создай каталог `_posts` и файл поста с YAML Front Matter (`title`, `layout: post`) "
        "и телом в Markdown; закоммить."
    ),
    "write_git_blob": (
        "Создай `api.txt` и сохрани его в объектную БД Git командой `git hash-object -w api.txt`."
    ),
    "mr_feature_branch": (
        "Создай ветку `awesome-feature`, измени `hello.txt`, закоммить с сообщением "
        "`Feature for MR` и запиши имя ветки в `mr-branch.txt`."
    ),
    "add_gitlab_ci_yaml": (
        "Добавь и закоммить `.gitlab-ci.yml` с job `test` и шагом `script: echo ok` "
        "(минимальный CI-конфиг для GitLab)."
    ),
    "closes_issue_gitlab": (
        "Сделай коммит с сообщением, содержащим `Closes #7` — в GitLab так "
        "автоматически закрывают issue при merge MR (в песочнице проверяется текст коммита)."
    ),
    "gitlab_md_issue_ref": (
        "Создай `notes.md` со строкой, ссылающейся на issue в стиле GLFM (`#3` или "
        "`issue #3`), и закоммить файл."
    ),
}

TASK_CONDITIONS: dict[str, str] = _with_file_hints(_RAW_TASK_CONDITIONS)
