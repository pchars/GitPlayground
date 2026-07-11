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
from apps.tasks.task_hints import TASK_HINTS
from apps.tasks.task_registry import LEVEL_TASK_POINTS, blueprints_for_level
from apps.tasks.theory_content import LEVEL_DIAGRAMS, LEVEL_SECTION_HINTS, THEORY_CONTENT


TASK_BLUEPRINTS = {level: blueprints_for_level(level) for level in LEVEL_TASK_POINTS}

LEVELS = [
    (1, "Основы Git", 12),
    (2, "Чистый репозиторий: .gitignore", 6),
    (3, "Ветвление", 9),
    (4, "Слияния и интеграция", 8),
    (5, "История и переписывание", 6),
    (6, "Удалённые репозитории", 7),
    (7, "Теги и релизы", 5),
    (8, "Диагностика и устройство Git", 13),
    (9, "Платформы и профессиональные практики", 13),
]

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
from pathlib import Path

log = Path('.gp/commands.log')
lines = log.read_text(encoding='utf-8').splitlines() if log.exists() else []
if not any(line.strip().lower().startswith('git status') for line in lines):
    print('Выполни git status, чтобы посмотреть состояние файлов')
    sys.exit(1)

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
    print('Expected modified but unstaged hello.txt. Use git add hello.txt then git restore --staged hello.txt (do not run git restore hello.txt).')
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
from pathlib import Path

log = Path('.gp/commands.log')
lines = log.read_text(encoding='utf-8').splitlines() if log.exists() else []
if not any('git log' in line and '--oneline' in line for line in lines):
    print('Выполни git log --oneline для компактной истории')
    sys.exit(1)

count = subprocess.run(['git', 'rev-list', '--count', 'HEAD'], capture_output=True, text=True, check=False)
if count.returncode != 0 or int(count.stdout.strip()) < 1:
    print('Need at least one commit to inspect history')
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
    if slug == "export_format_patch":
        return "import sys\nfrom pathlib import Path\np=list(Path('.').glob('*.patch'))\nsys.exit(0 if p else 1)"
    if slug == "git_mv_rename":
        return "import subprocess, sys\nfrom pathlib import Path\nif not Path('readme.txt').exists():\n    sys.exit(1)\nr=subprocess.run(['git','ls-files','hello.txt'],capture_output=True,text=True)\nsys.exit(0 if not r.stdout.strip() else 1)"
    if slug == "commit_signoff":
        return "import subprocess, sys\nm=subprocess.run(['git','log','-1','--pretty=%B'],capture_output=True,text=True).stdout\nsys.exit(0 if 'Signed-off-by:' in m else 1)"
    if slug == "semantic_describe":
        return "import subprocess, sys\nd=subprocess.run(['git','describe','--tags'],capture_output=True,text=True)\nsys.exit(0 if d.returncode==0 and 'v1.0.0' in (d.stdout or '') else 1)"
    if slug == "readme_first":
        return "from pathlib import Path\nimport sys\np=Path('README.md')\nif not p.exists():\n    sys.exit(1)\nc=p.read_text(encoding='utf-8')\nsys.exit(0 if '#' in c and c.strip() else 1)"
    if slug == "issue_close_message":
        return "import subprocess, sys\nb=subprocess.run(['git','log','-1','--pretty=%B'],capture_output=True,text=True).stdout.lower()\nsys.exit(0 if 'fixes #42' in b or 'fixes#42' in b.replace(' ', '') else 1)"
    if slug == "closes_issue_gitlab":
        return "import subprocess, sys\nb=subprocess.run(['git','log','-1','--pretty=%B'],capture_output=True,text=True).stdout.lower()\nsys.exit(0 if 'closes #7' in b or 'closes#7' in b.replace(' ', '') else 1)"
    if slug == "gitlab_md_issue_ref":
        return (
            "import pathlib, subprocess, sys\n"
            "p = pathlib.Path('notes.md')\n"
            "if not p.is_file():\n"
            "    sys.exit(1)\n"
            "t = p.read_text(encoding='utf-8').lower()\n"
            "if '#3' not in t:\n"
            "    sys.exit(1)\n"
            "r = subprocess.run(['git', 'ls-files', '--error-unmatch', 'notes.md'], capture_output=True)\n"
            "sys.exit(r.returncode)"
        )
    if slug == "rev_parse_head_sha":
        return (
            "import pathlib, subprocess, sys\n"
            "p = pathlib.Path('current-branch.txt')\n"
            "if not p.is_file():\n"
            "    sys.exit(1)\n"
            "expected = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], capture_output=True, text=True)\n"
            "if expected.returncode != 0:\n"
            "    sys.exit(1)\n"
            "branch = (expected.stdout or '').strip()\n"
            "content = p.read_text(encoding='utf-8').strip()\n"
            "sys.exit(0 if branch and branch == content else 1)"
        )
    if slug == "log_double_dot_range":
        return (
            "import pathlib, subprocess, sys\n"
            "if not pathlib.Path('range-done.txt').is_file():\n"
            "    sys.exit(1)\n"
            "branch = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], capture_output=True, text=True)\n"
            "if branch.returncode != 0 or (branch.stdout or '').strip() == 'main':\n"
            "    sys.exit(1)\n"
            "log = subprocess.run(['git', 'log', 'main..HEAD', '--oneline'], capture_output=True, text=True)\n"
            "if log.returncode != 0 or not (log.stdout or '').strip():\n"
            "    sys.exit(1)\n"
            "sys.exit(0)"
        )
    if slug == "pickaxe_log_search":
        return (
            "import pathlib, subprocess, sys\n"
            "if not pathlib.Path('pickaxe-done.txt').is_file():\n"
            "    sys.exit(1)\n"
            "log = subprocess.run(['git', 'log', '-S', 'PROGIT_FIND', '--oneline'], capture_output=True, text=True)\n"
            "if log.returncode != 0 or not (log.stdout or '').strip():\n"
            "    sys.exit(1)\n"
            "sys.exit(0)"
        )
    if slug == "merge_base_ready":
        return (
            "import pathlib, subprocess, sys\n"
            "if not pathlib.Path('merge-base-done.txt').is_file():\n"
            "    sys.exit(1)\n"
            "branch = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], capture_output=True, text=True)\n"
            "if branch.returncode != 0 or (branch.stdout or '').strip() == 'main':\n"
            "    sys.exit(1)\n"
            "mb = subprocess.run(['git', 'merge-base', 'main', 'HEAD'], capture_output=True, text=True)\n"
            "if mb.returncode != 0 or not (mb.stdout or '').strip():\n"
            "    sys.exit(1)\n"
            "sys.exit(0)"
        )
    if slug == "diff_cached_staged":
        return (
            "import pathlib, subprocess, sys\n"
            "if not pathlib.Path('staged-ready.txt').is_file():\n"
            "    sys.exit(1)\n"
            "d = subprocess.run(['git', 'diff', '--cached'], capture_output=True, text=True)\n"
            "if d.returncode != 0 or not (d.stdout or '').strip():\n"
            "    sys.exit(1)\n"
            "sys.exit(0)"
        )
    if slug == "triple_dot_log_range":
        return (
            "import pathlib, subprocess, sys\n"
            "if not pathlib.Path('triple-done.txt').is_file():\n"
            "    sys.exit(1)\n"
            "branch = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], capture_output=True, text=True)\n"
            "if branch.returncode != 0 or (branch.stdout or '').strip() == 'main':\n"
            "    sys.exit(1)\n"
            "log = subprocess.run(['git', 'log', 'main...HEAD', '--oneline'], capture_output=True, text=True)\n"
            "if log.returncode != 0 or not (log.stdout or '').strip():\n"
            "    sys.exit(1)\n"
            "sys.exit(0)"
        )
    if slug == "gh_pages_branch":
        return "import subprocess, sys\nc=subprocess.run(['git','show','gh-pages:index.html'],capture_output=True,text=True)\nsys.exit(0 if c.returncode==0 and c.stdout.strip() else 1)"
    if slug == "jekyll_post_front_matter":
        return """from pathlib import Path
import subprocess, sys
posts = list(Path('_posts').glob('*.md')) if Path('_posts').is_dir() else []
if not posts:
    print('_posts/*.md missing')
    sys.exit(1)
text = posts[0].read_text(encoding='utf-8')
if '---' not in text or 'title:' not in text or 'layout: post' not in text:
    print('Expected YAML front matter with title and layout: post')
    sys.exit(1)
r = subprocess.run(['git','ls-files', posts[0].as_posix()], capture_output=True, text=True)
if not r.stdout.strip():
    print('Post file should be tracked in git')
    sys.exit(1)
sys.exit(0)"""
    if slug == "write_git_blob":
        return """import subprocess, sys
from pathlib import Path
if not Path('api.txt').exists():
    print('api.txt missing')
    sys.exit(1)
h = subprocess.run(['git','hash-object','api.txt'], capture_output=True, text=True).stdout.strip()
if not h:
    sys.exit(1)
e = subprocess.run(['git','cat-file','-e', h], capture_output=True, text=True)
sys.exit(0 if e.returncode == 0 else 1)"""
    if slug == "save_symbolic_head":
        return """from pathlib import Path
import subprocess, sys
p = Path('head-ref.txt')
if not p.exists():
    print('head-ref.txt missing')
    sys.exit(1)
text = p.read_text(encoding='utf-8').strip()
ref = subprocess.run(['git','symbolic-ref','HEAD'], capture_output=True, text=True)
if ref.returncode != 0 or text != ref.stdout.strip():
    print('head-ref.txt should match git symbolic-ref HEAD')
    sys.exit(1)
sys.exit(0)"""
    if slug == "tree_list_root":
        return """from pathlib import Path
import subprocess, sys
p = Path('tree-list.txt')
if not p.exists():
    print('tree-list.txt missing')
    sys.exit(1)
expected = subprocess.run(['git','ls-tree','--name-only','HEAD'], capture_output=True, text=True).stdout.strip().splitlines()
actual = [ln.strip() for ln in p.read_text(encoding='utf-8').splitlines() if ln.strip()]
if sorted(actual) != sorted(expected):
    print('tree-list.txt should match git ls-tree --name-only HEAD')
    sys.exit(1)
sys.exit(0)"""
    if slug == "mr_feature_branch":
        return """from pathlib import Path
import subprocess, sys
p = Path('mr-branch.txt')
if not p.exists():
    print('mr-branch.txt missing')
    sys.exit(1)
name = p.read_text(encoding='utf-8').strip()
if name != 'awesome-feature':
    print('expected awesome-feature in mr-branch.txt')
    sys.exit(1)
ref = subprocess.run(['git','symbolic-ref','HEAD'], capture_output=True, text=True)
if ref.returncode != 0 or ref.stdout.strip() != 'refs/heads/awesome-feature':
    print('HEAD should be on awesome-feature')
    sys.exit(1)
msg = subprocess.run(['git','log','-1','--pretty=%s'], capture_output=True, text=True).stdout
if 'Feature for MR' not in msg:
    print('commit message should mention Feature for MR')
    sys.exit(1)
sys.exit(0)"""
    if slug == "add_gitlab_ci_yaml":
        return """import subprocess, sys
show = subprocess.run(['git','show','HEAD:.gitlab-ci.yml'], capture_output=True, text=True)
if show.returncode != 0:
    print('.gitlab-ci.yml not in HEAD')
    sys.exit(1)
text = show.stdout.lower()
if 'script' not in text or 'echo ok' not in text:
    print('.gitlab-ci.yml should define a script with echo ok')
    sys.exit(1)
if 'test' not in text:
    print('expected test job in .gitlab-ci.yml')
    sys.exit(1)
sys.exit(0)"""
    if slug == "create_offline_bundle":
        return """from pathlib import Path
import subprocess, sys
p = Path('repo.bundle')
if not p.exists():
    print('repo.bundle missing')
    sys.exit(1)
v = subprocess.run(['git','bundle','verify','repo.bundle'], capture_output=True, text=True)
if v.returncode != 0:
    print('git bundle verify failed')
    sys.exit(1)
sys.exit(0)"""
    if slug == "attach_git_note":
        return """from pathlib import Path
import subprocess, sys
p = Path('note-check.txt')
if not p.exists():
    print('note-check.txt missing')
    sys.exit(1)
expected = p.read_text(encoding='utf-8').strip()
note = subprocess.run(['git','notes','show','HEAD'], capture_output=True, text=True)
if note.returncode != 0 or note.stdout.strip() != expected:
    print('note-check.txt should match git notes show HEAD')
    sys.exit(1)
if expected != 'reviewed':
    print('expected note text reviewed')
    sys.exit(1)
sys.exit(0)"""
    if slug == "branch_without_checkout":
        return """from pathlib import Path
import subprocess, sys
p = Path('active-branch.txt')
if not p.exists():
    print('active-branch.txt missing')
    sys.exit(1)
current = subprocess.run(['git','branch','--show-current'], capture_output=True, text=True).stdout.strip()
if current != 'main':
    print('expected to stay on main')
    sys.exit(1)
if p.read_text(encoding='utf-8').strip() != current:
    print('active-branch.txt should match current branch')
    sys.exit(1)
br = subprocess.run(['git','branch','--list','sidecar'], capture_output=True, text=True).stdout
if 'sidecar' not in br:
    print('sidecar branch missing')
    sys.exit(1)
sys.exit(0)"""
    if slug == "rescue_detached_head":
        return """from pathlib import Path
import subprocess, sys
p = Path('rescue-branch.txt')
if not p.exists():
    print('rescue-branch.txt missing')
    sys.exit(1)
name = p.read_text(encoding='utf-8').strip()
ref = subprocess.run(['git','symbolic-ref','HEAD'], capture_output=True, text=True)
if ref.returncode != 0 or ref.stdout.strip() != f'refs/heads/{name}':
    print('HEAD should be on branch named in rescue-branch.txt')
    sys.exit(1)
if name != 'rescue-tip':
    print('expected rescue-tip branch')
    sys.exit(1)
br = subprocess.run(['git','branch','--list','rescue-tip'], capture_output=True, text=True).stdout
if 'rescue-tip' not in br:
    print('rescue-tip branch missing')
    sys.exit(1)
sys.exit(0)"""
    if slug == "view_history":
        return TASK_VALIDATORS["1.8"]
    if slug in {"branch_compare", "branch_from_commit", "track_remote_branch"}:
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
    if slug == "grep_in_repo":
        return """import sys
from pathlib import Path
p = Path('grep-hit.txt')
if not p.exists():
    print('grep-hit.txt missing')
    sys.exit(1)
text = p.read_text(encoding='utf-8')
if 'hello.txt' not in text or 'Git' not in text:
    print('grep-hit.txt should contain a git grep hit from hello.txt')
    sys.exit(1)
sys.exit(0)"""
    if slug == "stage_tracked_only":
        return """import subprocess, sys
tracked = subprocess.run(['git', 'ls-files', 'scratch.txt'], capture_output=True, text=True)
if tracked.stdout.strip():
    print('scratch.txt must remain untracked')
    sys.exit(1)
names = subprocess.run(['git', 'diff', 'HEAD~1', 'HEAD', '--name-only'], capture_output=True, text=True)
if names.returncode != 0:
    print('Need at least two commits to verify the last change')
    sys.exit(1)
if 'hello.txt' not in names.stdout:
    print('hello.txt should be in the last commit')
    sys.exit(1)
if 'scratch.txt' in names.stdout:
    print('scratch.txt must not be committed')
    sys.exit(1)
sys.exit(0)"""
    if slug in {"reset_head_unstage", "stage_unstage"}:
        return TASK_VALIDATORS["1.4"]
    if slug == "clean_untracked":
        return """import sys
from pathlib import Path
if Path('garbage.tmp').exists():
    print('garbage.tmp should be removed')
    sys.exit(1)
import subprocess
tracked = subprocess.run(['git', 'ls-files', 'garbage.tmp'], capture_output=True, text=True)
if tracked.stdout.strip():
    print('garbage.tmp must never have been tracked')
    sys.exit(1)
sys.exit(0)"""
    if slug in {"init_repo", "first_commit", "check_status", "stage_unstage", "commit_second", "view_diff", "amend_commit", "view_history"}:
        reverse_lookup = {
            "init_repo": "1.1",
            "first_commit": "1.2",
            "check_status": "1.3",
            "stage_unstage": "1.4",
            "commit_second": "1.5",
            "view_diff": "1.6",
            "amend_commit": "1.7",
            "view_history": "1.8",
        }
        mapped = reverse_lookup.get(slug)
        if mapped and mapped in TASK_VALIDATORS:
            return TASK_VALIDATORS[mapped]
    return "import subprocess, sys\nr=subprocess.run(['git','status','--porcelain'],capture_output=True,text=True)\nsys.exit(0 if r.returncode==0 else 1)"


def validator_for(external_id: str, slug: str) -> str:
    return TASK_VALIDATORS.get(external_id) or _validator_by_slug(slug, external_id)


def task_metadata(level_number: int, slug: str, description: str) -> dict:
    requires = []
    if slug != "init_repo":
        requires.append("repo_initialized")
    if slug in {"check_status", "stage_unstage", "commit_second", "view_diff", "amend_commit", "view_history", "grep_in_repo", "stage_tracked_only", "reset_head_unstage", "tree_list_root", "branch_without_checkout", "rescue_detached_head", "create_offline_bundle", "attach_git_note", "mr_feature_branch", "add_gitlab_ci_yaml"}:
        requires.append("hello_committed")
    if slug in {"export_format_patch", "git_mv_rename", "commit_signoff", "semantic_describe", "issue_close_message", "closes_issue_gitlab", "rev_parse_head_sha", "log_double_dot_range", "pickaxe_log_search", "merge_base_ready", "diff_cached_staged", "triple_dot_log_range"}:
        requires.append("hello_committed")
    if slug in {"readme_first", "gh_pages_branch", "jekyll_post_front_matter", "write_git_blob", "save_symbolic_head", "gitlab_md_issue_ref"}:
        requires.append("repo_initialized")
    if slug in {"commit_on_branch", "switch_branch", "list_branches", "delete_branch"}:
        requires.extend(["hello_committed", "feature_branch_exists"])
    validator_hints = ["Проверка опирается на состояние репозитория и историю коммитов."]
    if slug == "stage_unstage":
        validator_hints = [
            "Ожидается измененный `hello.txt` без staged-изменений.",
            "Подходит `git add hello.txt`, затем `git restore --staged hello.txt`.",
        ]
    return {
        "objective": description,
        "preconditions": requires,
        "validatorHints": validator_hints,
        "start": {
            "mode": "guided",
            "requires": requires,
        },
    }


def revision_payload(task: Task) -> dict:
    return {
        "objective": task.description,
        "steps": [],
        "expected_state": "",
        "validator_notes": "",
        "schema_version": 1,
    }


def _zip_workspace(repo: Path) -> str:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for item in repo.rglob("*"):
            if item.is_file():
                archive.write(item, item.relative_to(repo))
    return f"base64zip:{base64.b64encode(buffer.getvalue()).decode('ascii')}"


def build_start_repo_asset(slug: str) -> str | None:
    if slug not in {"check_status", "stage_unstage", "commit_second", "view_diff", "amend_commit", "view_history", "grep_in_repo", "stage_tracked_only", "reset_head_unstage"}:
        return None
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td) / "repo"
        repo.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "-c", "init.defaultBranch=main", "init"],
            cwd=repo,
            check=False,
            capture_output=True,
            text=True,
        )
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


class Command(BaseCommand):
    help = "Seed levels, theory blocks and task records with enriched GitMagic content."

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        created_tasks = 0
        created_assets = 0
        # Slugs are global; wipe all GitHub tasks before reordering levels.
        Task.objects.filter(platform=Task.Platform.GITHUB).delete()
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

            TheoryBlock.objects.update_or_create(
                level=level,
                defaults={
                    "title": f"Теория: {level_title}",
                    "content_md": THEORY_CONTENT[level_number],
                    "diagram_mermaid": LEVEL_DIAGRAMS[level_number],
                },
            )

            # Rebuild level tasks deterministically.
            Task.objects.filter(level=level, platform=Task.Platform.GITHUB).delete()
            for order, (slug, description, points) in enumerate(
                TASK_BLUEPRINTS.get(level_number, []), start=1
            ):
                task_hints = TASK_HINTS.get(slug) or LEVEL_SECTION_HINTS.get(
                    level_number,
                    (
                        "Проверь текущее состояние через git status и выполни шаги задачи последовательно.",
                        "Сверь результат через git log --oneline и git status --short перед проверкой.",
                    ),
                )
                metadata = task_metadata(level_number, slug, description)
                defaults = {
                    "slug": slug,
                    "title": slug.replace("_", " ").title(),
                    "description": description,
                    "platform": Task.Platform.GITHUB,
                    "level": level,
                    "order": order,
                    "points": points,
                    "validator_cmd": "python validator.py",
                    "success_message": "Отлично! Задача решена.",
                    "metadata": metadata,
                }
                task = Task.objects.create(
                    external_id=f"gh-{level_number}.{order}",
                    **defaults,
                )
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
                        "content": task_hints[0],
                    },
                )
                TaskAsset.objects.update_or_create(
                    task=task,
                    asset_type=TaskAsset.AssetType.HINT,
                    path="hints/hint2.txt",
                    defaults={
                        "sort_order": 2,
                        "content": task_hints[1],
                    },
                )
                created_tasks += 1
                created_assets += 3

        # Achievements are global definitions; bootstrap once during seed, not per profile request.
        from apps.achievements.services import bootstrap_default_achievements

        bootstrap_default_achievements()

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete: {len(LEVELS)} levels, {created_tasks} tasks, {created_assets} assets."
            )
        )
