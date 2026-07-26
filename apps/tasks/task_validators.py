"""Task VALIDATOR asset source strings for seed_initial_data."""

from apps.tasks.terminal_validators import TERMINAL_TASK_VALIDATORS


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
    if slug in TERMINAL_TASK_VALIDATORS:
        return TERMINAL_TASK_VALIDATORS[slug]
    if slug in {"list_branches"}:
        return "import subprocess, sys\nr=subprocess.run(['git','branch'],capture_output=True,text=True);sys.exit(0 if '*' in r.stdout else 1)"
    if slug in {"delete_branch"}:
        return "import subprocess, sys\nr=subprocess.run(['git','branch'],capture_output=True,text=True).stdout\nsys.exit(0 if 'feature-x' not in r else 1)"
    if slug in {"rename_branch"}:
        return "import subprocess, sys\nb=subprocess.run(['git','branch','--show-current'],capture_output=True,text=True).stdout.strip();sys.exit(0 if b and b!='main' else 1)"
    if slug in {"setup_ignore"}:
        return (
            "from pathlib import Path\n"
            "import subprocess, sys\n"
            "c = Path('.gitignore').read_text(encoding='utf-8') if Path('.gitignore').exists() else ''\n"
            "if not all(token in c for token in ('*.log', '.env', '__pycache__/')):\n"
            "    print('Expected *.log, .env and __pycache__/ in .gitignore')\n"
            "    sys.exit(1)\n"
            "for path in ('app.log', '.env', '__pycache__/module.pyc'):\n"
            "    ignored = subprocess.run(['git', 'check-ignore', '-q', path], capture_output=True)\n"
            "    if ignored.returncode != 0:\n"
            "        print(f'{path} should be ignored')\n"
            "        sys.exit(1)\n"
            "sys.exit(0)"
        )
    if slug == "ignore_node_modules":
        return (
            "from pathlib import Path\n"
            "import subprocess, sys\n"
            "c = Path('.gitignore').read_text(encoding='utf-8') if Path('.gitignore').exists() else ''\n"
            "if 'node_modules' not in c:\n"
            "    print('Add node_modules/ to .gitignore')\n"
            "    sys.exit(1)\n"
            "ignored = subprocess.run(['git', 'check-ignore', '-q', 'node_modules/dummy.js'], capture_output=True)\n"
            "if ignored.returncode != 0:\n"
            "    print('node_modules should be ignored')\n"
            "    sys.exit(1)\n"
            "sys.exit(0)"
        )
    if slug == "untrack_cached":
        return (
            "from pathlib import Path\n"
            "import subprocess, sys\n"
            "if not Path('secrets.env').is_file():\n"
            "    print('secrets.env must remain on disk')\n"
            "    sys.exit(1)\n"
            "tracked = subprocess.run(['git', 'ls-files', 'secrets.env'], capture_output=True, text=True)\n"
            "if tracked.stdout.strip():\n"
            "    print('secrets.env should no longer be tracked')\n"
            "    sys.exit(1)\n"
            "ignore = Path('.gitignore').read_text(encoding='utf-8') if Path('.gitignore').exists() else ''\n"
            "if 'secrets.env' not in ignore:\n"
            "    print('secrets.env should be listed in .gitignore')\n"
            "    sys.exit(1)\n"
            "sys.exit(0)"
        )
    if slug == "keep_empty_dir":
        return (
            "import subprocess, sys\n"
            "tracked = subprocess.run(['git', 'ls-files', 'notes/.gitkeep'], capture_output=True, text=True)\n"
            "if not tracked.stdout.strip():\n"
            "    print('notes/.gitkeep should be tracked in Git')\n"
            "    sys.exit(1)\n"
            "sys.exit(0)"
        )
    if slug == "ignore_exceptions":
        return (
            "import subprocess, sys\n"
            "important = subprocess.run(['git', 'check-ignore', '-q', 'important.log'], capture_output=True)\n"
            "debug = subprocess.run(['git', 'check-ignore', '-q', 'debug.log'], capture_output=True)\n"
            "if important.returncode == 0:\n"
            "    print('important.log must stay tracked (exception from *.log rule)')\n"
            "    sys.exit(1)\n"
            "if debug.returncode != 0:\n"
            "    print('debug.log should be ignored by *.log rule')\n"
            "    sys.exit(1)\n"
            "sys.exit(0)"
        )
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
import subprocess
from pathlib import Path
p = Path('grep-hit.txt')
if not p.exists():
    print('grep-hit.txt missing')
    sys.exit(1)
text = p.read_text(encoding='utf-8').strip()
grep = subprocess.run(['git', 'grep', 'Git'], capture_output=True, text=True, check=False)
if grep.returncode != 0:
    print('git grep Git should find a match in tracked files')
    sys.exit(1)
hits = [line.strip() for line in grep.stdout.splitlines() if line.strip()]
if not any(hit in text for hit in hits):
    print('grep-hit.txt should contain a line from git grep output')
    sys.exit(1)
if 'hello.txt' not in text or 'Git' not in text:
    print('grep-hit.txt should reference hello.txt and Git')
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
