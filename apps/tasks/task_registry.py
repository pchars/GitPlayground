"""Single entry point for task content (conditions, hints, points)."""

from __future__ import annotations

from apps.tasks.task_descriptions import TASK_CONDITIONS
from apps.tasks.task_hints import TASK_HINTS

# slug -> points per level (source of truth for seed and coverage tests)
# Course arc: terminal intro → basics → hygiene → branches → merges → history → remotes → tags → diagnostics → platforms
# Points are intentionally lean vs hint costs so hints stay a scarce spend.
LEVEL_TASK_POINTS: dict[int, list[tuple[str, int]]] = {
    0: [
        ("sandbox_pwd", 2),
        ("sandbox_ls", 2),
        ("sandbox_whoami", 2),
        ("sandbox_mkdir", 3),
        ("sandbox_touch", 2),
        ("sandbox_echo_write", 3),
        ("sandbox_cat", 2),
        ("sandbox_echo_append", 3),
        ("sandbox_type_empty", 2),
        ("sandbox_head", 2),
        ("sandbox_tail", 2),
        ("sandbox_wc", 3),
        ("sandbox_cp", 3),
        ("sandbox_mv", 3),
        ("sandbox_find", 3),
        ("sandbox_rm", 3),
        ("sandbox_nano", 3),
        ("sandbox_clear", 2),
    ],
    1: [
        ("init_repo", 3),
        ("first_commit", 5),
        ("check_status", 3),
        ("stage_unstage", 4),
        ("view_diff", 3),
        ("commit_second", 5),
        ("amend_commit", 6),
        ("view_history", 3),
        ("grep_in_repo", 3),
        ("stage_tracked_only", 4),
        ("reset_head_unstage", 3),
        ("diff_cached_staged", 4),
    ],
    2: [
        ("setup_ignore", 4),
        ("ignore_node_modules", 3),
        ("untrack_cached", 5),
        ("keep_empty_dir", 3),
        ("ignore_exceptions", 5),
        ("clean_untracked", 4),
    ],
    3: [
        ("create_branch", 4),
        ("commit_on_branch", 5),
        ("switch_branch", 3),
        ("list_branches", 2),
        ("rename_branch", 4),
        ("branch_from_commit", 6),
        ("delete_branch", 3),
        ("branch_without_checkout", 3),
        ("rescue_detached_head", 5),
    ],
    4: [
        ("fast_forward_merge", 4),
        ("no_ff_merge", 6),
        ("resolve_conflict", 9),
        ("abort_merge", 5),
        ("squash_merge", 7),
        ("cherry_pick_hotfix", 6),
        ("revert_merge", 7),
        ("merge_base_ready", 5),
    ],
    5: [
        ("amend_message", 4),
        ("reorder_commits", 7),
        ("squash_commits", 7),
        ("edit_commit", 8),
        ("stash_workflow", 5),
        ("reset_modes", 7),
    ],
    6: [
        ("clone_local", 4),
        ("add_remote", 3),
        ("push_first", 4),
        ("fetch_merge", 6),
        ("pull_rebase", 6),
        ("push_conflict", 7),
        ("create_offline_bundle", 5),
    ],
    7: [
        ("create_lightweight_tag", 4),
        ("create_tag", 5),
        ("show_tag", 3),
        ("tag_old_commit", 5),
        ("push_tags", 5),
    ],
    8: [
        ("find_bisect", 8),
        ("reflog_recovery", 7),
        ("worktree", 5),
        ("inspect_objects", 7),
        ("custom_aliases_hooks", 6),
        ("filter_branch", 9),
        ("save_symbolic_head", 4),
        ("tree_list_root", 4),
        ("attach_git_note", 4),
        ("rev_parse_head_sha", 4),
        ("log_double_dot_range", 5),
        ("pickaxe_log_search", 5),
        ("triple_dot_log_range", 5),
    ],
    9: [
        ("export_format_patch", 5),
        ("git_mv_rename", 4),
        ("commit_signoff", 5),
        ("semantic_describe", 6),
        ("readme_first", 4),
        ("issue_close_message", 5),
        ("gh_pages_branch", 6),
        ("jekyll_post_front_matter", 5),
        ("write_git_blob", 6),
        ("mr_feature_branch", 4),
        ("add_gitlab_ci_yaml", 5),
        ("closes_issue_gitlab", 5),
        ("gitlab_md_issue_ref", 4),
    ],
}


def all_task_slugs() -> list[str]:
    slugs: list[str] = []
    for level in sorted(LEVEL_TASK_POINTS):
        slugs.extend(slug for slug, _ in LEVEL_TASK_POINTS[level])
    return slugs


def task_blueprint(slug: str, points: int) -> tuple[str, str, int]:
    return slug, TASK_CONDITIONS[slug], points


def blueprints_for_level(level: int) -> list[tuple[str, str, int]]:
    return [task_blueprint(slug, points) for slug, points in LEVEL_TASK_POINTS[level]]


def hints_for_slug(slug: str) -> tuple[str, str]:
    return TASK_HINTS[slug]
