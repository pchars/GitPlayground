"""Per-task hint text for the playground (two hints per task slug)."""

from __future__ import annotations

# Each value is (hint_1, hint_2) shown in order; hint_2 costs another unlock step.
TASK_HINTS: dict[str, tuple[str, str]] = {
    # Level 1 — basics
    "init_repo": (
        "В пустой папке выполни `git init` — появится скрытая директория `.git`.",
        "Проверь результат: `git status` должен показать пустой репозиторий на ветке `main`.",
    ),
    "first_commit": (
        "Создай `hello.txt` с текстом `Hello, Git!` (`echo \"Hello, Git!\" > hello.txt` или `nano hello.txt`), затем `git add hello.txt`.",
        "Зафиксируй изменение коммитом: `git commit -m \"Add hello\"`. Сообщение должно совпасть с условием.",
    ),
    "check_status": (
        "Измени `hello.txt` (`nano hello.txt` или `echo \"...\" >> hello.txt`), но не выполняй `git add` — файл должен остаться только в рабочей копии.",
        "Выполни `git status --short`: для изменённого, но не застейдженного файла ожидается префикс ` M`.",
    ),
    "stage_unstage": (
        "Сначала измени `hello.txt`, затем `git add hello.txt`, чтобы файл попал в staging.",
        "Сними файл из индекса: `git restore --staged hello.txt`. Не используй `git restore hello.txt` без `--staged` — это откатит правку.",
    ),
    "view_diff": (
        "Добавь в `hello.txt` строку `Another line` и не коммить изменение сразу.",
        "Выполни `git diff` — в выводе должна быть добавленная строка до коммита.",
    ),
    "commit_second": (
        "Внеси правку в `hello.txt`, добавь файл в индекс (`git add hello.txt`).",
        "Сделай коммит с сообщением `Update hello`: `git commit -m \"Update hello\"`.",
    ),
    "amend_commit": (
        "Создай `config.txt` (например, `touch config.txt`) и добавь его в индекс.",
        "Включи файл в последний коммит без нового сообщения: `git commit --amend --no-edit`.",
    ),
    "view_history": (
        "Для компактного списка коммитов используй `git log --oneline`.",
        "В выводе должен быть хотя бы один коммит из истории репозитория.",
    ),
    "grep_in_repo": (
        "Поиск по отслеживаемым файлам: `git grep Git` (или `git grep -n Git` для номеров строк).",
        "Запиши одну строку вывода в файл: `echo \"hello.txt:Hello, Git!\" > grep-hit.txt`.",
    ),
    "stage_tracked_only": (
        "Измени отслеживаемый файл и создай новый: `echo \"...\" >> hello.txt`, `echo temp > scratch.txt`.",
        "Стадируй только tracked: `git add -u`, затем `git commit -m \"...\"` — `scratch.txt` останется untracked.",
    ),
    "reset_head_unstage": (
        "После правки: `git add hello.txt`, затем `git reset HEAD hello.txt`.",
        "Проверь `git status --short`: должно быть ` M hello.txt` (изменён, но не staged).",
    ),
    "diff_cached_staged": (
        "Измени `hello.txt`, затем `git add hello.txt`.",
        "Проверь `git diff --cached`, создай маркер: `echo ok > staged-ready.txt`.",
    ),
    # Level 2 — repository hygiene (.gitignore)
    "setup_ignore": (
        "Создай `.gitignore` через `nano .gitignore` и добавь строки: `*.log`, `.env`, `__pycache__/` (по одной на строку).",
        "Проверь `git status` — перечисленные файлы не должны появляться как неотслеживаемые, если они подпадают под маски.",
    ),
    "ignore_node_modules": (
        "Добавь в `.gitignore` строку `node_modules/`.",
        "После сохранения `git status` не должен предлагать отслеживать содержимое `node_modules/`.",
    ),
    "untrack_cached": (
        "Убери файл из индекса, но оставь на диске: `git rm --cached <файл>`.",
        "Добавь маску в `.gitignore`, чтобы Git снова не подхватил файл при следующем `git add .`.",
    ),
    "keep_empty_dir": (
        "Git не хранит пустые папки — положи внутрь файл `.gitkeep` и добавь его в коммит.",
        "Типично: `touch notes/.gitkeep`, затем `git add notes/.gitkeep` и коммит.",
    ),
    "ignore_exceptions": (
        "В `.gitignore` правило `*.log` игнорирует все `.log`, исключение: `!important.log`.",
        "Исключение сработает только если родительская папка не игнорируется целиком.",
    ),
    "clean_untracked": (
        "Создай мусорный файл: `echo tmp > garbage.tmp`, затем `git clean -n` — dry-run.",
        "Удали untracked: `git clean -f` (или `git clean -f garbage.tmp`).",
    ),
    # Level 3 — branching
    "create_branch": (
        "Создай и сразу переключись на ветку: `git checkout -b feature-x` (или `git switch -c feature-x`).",
        "Проверь текущую ветку: `git branch --show-current` должен вернуть `feature-x`.",
    ),
    "commit_on_branch": (
        "Убедись, что активна ветка `feature-x`, затем создай `feature.txt` и закоммить изменения.",
        "Типичная последовательность: `git add feature.txt`, затем `git commit -m \"...\"`.",
    ),
    "switch_branch": (
        "Вернись на `main`: `git checkout main` (или `git switch main`).",
        "На `main` файла `feature.txt` быть не должно — он существует только в ветке `feature-x`.",
    ),
    "list_branches": (
        "Список веток и текущей отметки: `git branch` — активная помечена звёздочкой `*`.",
        "Для краткого вида с последним коммитом: `git branch -v`.",
    ),
    "rename_branch": (
        "Переименуй текущую ветку: `git branch -m новое-имя` (ветка не должна быть `main`).",
        "Проверь: `git branch --show-current` показывает новое имя.",
    ),
    "branch_from_commit": (
        "Найди SHA нужного коммита через `git log --oneline`.",
        "Создай ветку от этого коммита: `git branch имя-ветки <SHA>`.",
    ),
    "delete_branch": (
        "Удаляй только неактивную ветку: `git branch -d feature-x` (сначала переключись на другую).",
        "Если ветка не слита, Git может отказать — для учебной задачи используй безопасное удаление слитой ветки.",
    ),
    "branch_without_checkout": (
        "Только `git branch sidecar` — без `checkout`/`switch`.",
        "Проверь: `git branch --show-current` всё ещё `main`; запиши: `echo main > active-branch.txt`.",
    ),
    "rescue_detached_head": (
        "Detached HEAD: `git checkout --detach` (или `git switch --detach`).",
        "Спасение: `git checkout -b rescue-tip`, затем `echo rescue-tip > rescue-branch.txt`.",
    ),
    # Level 4 — merges
    "fast_forward_merge": (
        "Слей ветку в `main`, когда `main` не ушёл вперёд: `git checkout main`, затем `git merge feature`.",
        "При fast-forward не появляется отдельный merge-коммит — указатель `main` просто перемещается вперёд.",
    ),
    "no_ff_merge": (
        "Перед merge убедись, что на `main` есть коммиты, которых нет в feature-ветке.",
        "Выполни `git merge --no-ff feature -m \"Merge feature\"` — появится merge-коммит с двумя родителями.",
    ),
    "resolve_conflict": (
        "При конфликте открой файлы с маркерами `<<<<<<<`, выбери итоговый текст, удали маркеры.",
        "После правки: `git add <файл>` для каждого конфликтного файла, затем заверши merge (`git commit` при необходимости).",
    ),
    "abort_merge": (
        "Если merge зашёл в тупик, отмени его: `git merge --abort`.",
        "После abort в `git status` не должно остаться незавершённого merge и маркеров `UU`.",
    ),
    "squash_merge": (
        "На `main` выполни `git merge --squash feature` — изменения попадут в индекс одним набором.",
        "Зафиксируй результат отдельным коммитом: `git commit -m \"Squashed feature\"`.",
    ),
    "cherry_pick_hotfix": (
        "Найди SHA нужного коммита на другой ветке через `git log --oneline`.",
        "Перенеси его на текущую ветку: `git cherry-pick <SHA>`.",
    ),
    "revert_merge": (
        "Для отката merge-коммита используй `git revert -m 1 <merge-commit-sha>`.",
        "Параметр `-m 1` указывает, какого родителя считать «главной» линией истории.",
    ),
    "merge_base_ready": (
        "Ветка: `git checkout -b prof-feature`, измени `hello.txt`, commit.",
        "Проверь `git merge-base main HEAD`, затем `echo ok > merge-base-done.txt`.",
    ),
    # Level 5 — history rewriting
    "amend_message": (
        "Исправь сообщение последнего коммита: `git commit --amend -m \"Новый текст\"`.",
        "Команда меняет только HEAD; если коммит уже отправлен в remote, понадобится осторожность (в песочнице это безопасно).",
    ),
    "reorder_commits": (
        "Запусти интерактивный rebase: `git rebase -i HEAD~N` (N — число последних коммитов).",
        "В редакторе поменяй порядок строк `pick` — Git пересоберёт историю в указанной последовательности.",
    ),
    "squash_commits": (
        "В `git rebase -i` замени `pick` на `squash` (или `s`) у коммитов, которые нужно объединить.",
        "Сохрани файл — Git предложит итоговое сообщение для объединённого коммита.",
    ),
    "edit_commit": (
        "В `git rebase -i` поставь `edit` у коммита, который нужно изменить.",
        "Когда rebase остановится, внеси правки, `git add`, затем `git rebase --continue`.",
    ),
    "stash_workflow": (
        "Спрячь незакоммиченные изменения: `git stash push -m \"wip\"`.",
        "Верни их обратно: `git stash pop` (или `git stash apply`, если stash нужно сохранить).",
    ),
    "reset_modes": (
        "`git reset --soft HEAD~1` — откатывает коммит, оставляя изменения в индексе.",
        "`git reset --mixed` (по умолчанию) снимает и коммит, и staging; `--hard` ещё и чистит рабочую копию.",
    ),
    # Level 6 — remotes
    "clone_local": (
        "Клонируй репозиторий: `git clone <url> <папка>` — появится копия с настроенным `origin`.",
        "После clone перейди в папку клона и проверь `git remote -v`.",
    ),
    "add_remote": (
        "Добавь удалённый репозиторий: `git remote add upstream <url>`.",
        "Проверь список: `git remote -v` должен показать `upstream` с fetch/push URL.",
    ),
    "push_first": (
        "Первый push ветки с привязкой: `git push -u origin <ветка>`.",
        "Флаг `-u` запоминает upstream для последующих `git push` / `git pull`.",
    ),
    "fetch_merge": (
        "Подтяни объекты без слияния: `git fetch origin`.",
        "Влей изменения вручную: `git merge origin/<ветка>` (или `git rebase` — по условию задачи).",
    ),
    "pull_rebase": (
        "Настрой rebase при pull: `git config pull.rebase true` (локально для репозитория).",
        "Затем `git pull` подтянет коммиты и перебазирует ваши поверх удалённых.",
    ),
    "push_conflict": (
        "Если push отклонён (non-fast-forward), сначала подтяни изменения: `git pull --rebase` или `git fetch` + merge/rebase.",
        "После успешной интеграции повтори `git push`.",
    ),
    "create_offline_bundle": (
        "Офлайн-пакет: `git bundle create repo.bundle HEAD main`.",
        "Проверка: `git bundle verify repo.bundle` — должен завершиться без ошибок.",
    ),
    # Level 8 — diagnostics
    "find_bisect": (
        "Запусти бинарный поиск: `git bisect start`, затем `git bisect bad` на текущем и `git bisect good` на известно хорошем коммите.",
        "Git будет переключать HEAD — на каждом шаге отмечай `git bisect good` или `git bisect bad`, пока не найдёшь первый плохой.",
    ),
    "reflog_recovery": (
        "Потерянные коммиты ищи в `git reflog` — там журнал перемещений HEAD.",
        "Восстанови нужный SHA: `git checkout <sha>` или `git branch recovery <sha>`.",
    ),
    "worktree": (
        "Добавь отдельную рабочую копию: `git worktree add ../hotfix hotfix-branch`.",
        "В новой папке можно работать параллельно, не переключая основной worktree.",
    ),
    "inspect_objects": (
        "Посмотри тип объекта: `git cat-file -t <sha>`, содержимое: `git cat-file -p <sha>`.",
        "Дерево коммита: `git ls-tree HEAD` показывает файлы и подкаталоги в снимке.",
    ),
    "custom_aliases_hooks": (
        "Alias: `git config alias.st status` — после этого `git st` вызывает `git status`.",
        "Hook commit-msg: исполняемый скрипт в `.git/hooks/commit-msg` (без расширения) проверяет сообщение коммита.",
    ),
    "filter_branch": (
        "Для удаления файла из всей истории в учебных задачах часто используют `git filter-branch` или последовательность checkout/rm/commit.",
        "После переписывания истории проверь `git log --oneline` и что чувствительный файл больше не встречается.",
    ),
    "save_symbolic_head": (
        "Новая ветка: `git checkout -b internals-demo` (или `git switch -c`).",
        "Запиши вывод `git symbolic-ref HEAD` в файл: `echo refs/heads/internals-demo > head-ref.txt`.",
    ),
    "tree_list_root": (
        "Посмотри корень: `git ls-tree --name-only HEAD`.",
        "Запиши имена в файл, например `echo hello.txt > tree-list.txt` если в корне только hello.txt.",
    ),
    "attach_git_note": (
        "Заметка: `git notes add -m \"reviewed\"` к текущему HEAD.",
        "Сверь: `git notes show HEAD` и содержимое `note-check.txt` должны совпадать.",
    ),
    "rev_parse_head_sha": (
        "Узнай ветку: `git rev-parse --abbrev-ref HEAD` (должно быть `main`).",
        "Запиши: `echo main > current-branch.txt`.",
    ),
    "log_double_dot_range": (
        "Ветка и коммит: `git checkout -b explore-range`, измени `hello.txt`, `git commit`.",
        "Проверь `git log main..HEAD --oneline`, затем `echo ok > range-done.txt`.",
    ),
    "pickaxe_log_search": (
        "Уникальный текст: `echo PROGIT_FIND >> hello.txt`, `git add`, `git commit`.",
        "Поиск: `git log -S PROGIT_FIND --oneline`, маркер: `echo ok > pickaxe-done.txt`.",
    ),
    "triple_dot_log_range": (
        "Ветка: `git checkout -b triple-explore`, измени `hello.txt`, commit.",
        "Проверь `git log main...HEAD --oneline`, затем `echo ok > triple-done.txt`.",
    ),
    # Level 7 — tagging
    "create_lightweight_tag": (
        "Лёгкий тег на текущем коммите: `git tag v0.1-lw` (без `-a` и без сообщения).",
        "Проверь: `git tag -l` должен показать `v0.1-lw`.",
    ),
    "create_tag": (
        "Аннотированный тег: `git tag -a v1.0 -m \"Release v1.0\"`.",
        "В отличие от lightweight, такой тег хранит автора, дату и сообщение.",
    ),
    "show_tag": (
        "Детали тега и связанного коммита: `git show v1.0`.",
        "В выводе будут метаданные тега и diff коммита, на который он указывает.",
    ),
    "tag_old_commit": (
        "Найди SHA в `git log --oneline`, затем поставь тег: `git tag v0.9 <SHA>`.",
        "Проверь `git show v0.9` — коммит должен совпасть с выбранным SHA.",
    ),
    "push_tags": (
        "В песочнице сеть отключена — достаточно создать тег `v1.0` локально: `git tag -a v1.0 -m \"Release v1.0\"`.",
        "В реальном проекте теги публикуют `git push origin v1.0` или `git push --tags`.",
    ),
    # Level 9
    "export_format_patch": (
        "Экспорт одного коммита: `git format-patch -1 HEAD` — появится файл `0001-....patch`.",
        "Патч можно отправить по почте или применить на другой машине через `git am`.",
    ),
    "git_mv_rename": (
        "Переименование с историей: `git mv hello.txt readme.txt`.",
        "Зафиксируй: `git commit -m \"Rename hello to readme\"`.",
    ),
    "commit_signoff": (
        "Измени файл, добавь в индекс, коммить с подписью: `git commit -s -m \"...\"`.",
        "В теле коммита появится строка `Signed-off-by: ...` — это DCO.",
    ),
    "semantic_describe": (
        "Тег SemVer: `git tag -a v1.0.0 -m \"Release 1.0.0\"`.",
        "Версия в тексте: `git describe --tags` — должно содержать `v1.0.0`.",
    ),
    "readme_first": (
        "Создай README через `nano README.md` со строкой-заголовком `# ...` (или `echo \"# GitPlayground Demo\" > README.md`).",
        "Добавь и закоммить: `git add README.md`, `git commit -m \"Add README\"`.",
    ),
    "issue_close_message": (
        "Измени файл, добавь в индекс, коммить с `Fixes #42` в сообщении.",
        "Пример: `git commit -m \"Fix typo, Fixes #42\"`.",
    ),
    "gh_pages_branch": (
        "Новая ветка: `git checkout -b gh-pages`.",
        "Создай `index.html` (`nano index.html` или `echo \"<h1>Pages</h1>\" > index.html`), затем `git add index.html`, `git commit -m \"Add pages stub\"`.",
    ),
    "jekyll_post_front_matter": (
        "Каталог: `mkdir -p _posts`. Файл поста удобно набрать через `nano _posts/welcome.md`: YAML между `---`, поля `title:` и `layout: post`, затем тело.",
        "После сохранения (Ctrl+S в редакторе): `git add _posts/welcome.md`, `git commit -m \"Add welcome post\"`.",
    ),
    "write_git_blob": (
        "Создай файл: `echo api > api.txt`.",
        "Запиши blob в БД: `git hash-object -w api.txt` (SHA появится в выводе).",
    ),
    "mr_feature_branch": (
        "Ветка для MR: `git checkout -b awesome-feature`.",
        "Измени `hello.txt`, commit с `Feature for MR`, запиши `echo awesome-feature > mr-branch.txt`.",
    ),
    "add_gitlab_ci_yaml": (
        "Минимальный CI в `.gitlab-ci.yml` удобно набрать через `nano .gitlab-ci.yml`: job `test` с `script:` и `echo ok`.",
        "Не забудь `git add` и `git commit` — файл должен быть в истории.",
    ),
    "closes_issue_gitlab": (
        "Измени файл, добавь в индекс, коммить с `Closes #7` в сообщении.",
        "Пример: `git commit -m \"Update docs, Closes #7\"`.",
    ),
    "gitlab_md_issue_ref": (
        "GLFM-ссылка: `echo \"See issue #3 for details\" > notes.md`.",
        "Закоммить: `git add notes.md`, `git commit -m \"Add issue reference\"`.",
    ),
}
