"""Single entry point for task content (conditions, hints, points)."""

from __future__ import annotations

from apps.tasks.task_descriptions import TASK_CONDITIONS
from apps.tasks.task_hints import TASK_HINTS

# slug -> points per level (source of truth for seed and coverage tests)
LEVEL_TASK_POINTS: dict[int, list[tuple[str, int]]] = {
    1: [
        ("init_repo", 6),
        ("first_commit", 10),
        ("check_status", 6),
        ("stage_unstage", 8),
        ("view_diff", 6),
        ("commit_second", 10),
        ("amend_commit", 12),
        ("view_history", 6),
        ("grep_in_repo", 7),
        ("stage_tracked_only", 9),
        ("reset_head_unstage", 7),
        ("diff_cached_staged", 8),
    ],
    2: [
        ("create_branch", 8),
        ("commit_on_branch", 10),
        ("switch_branch", 6),
        ("list_branches", 5),
        ("rename_branch", 8),
        ("branch_from_commit", 12),
        ("delete_branch", 7),
        ("branch_without_checkout", 7),
        ("rescue_detached_head", 10),
    ],
    3: [
        ("fast_forward_merge", 8),
        ("no_ff_merge", 12),
        ("resolve_conflict", 18),
        ("abort_merge", 10),
        ("squash_merge", 14),
        ("cherry_pick_hotfix", 12),
        ("revert_merge", 14),
        ("merge_base_ready", 10),
    ],
    4: [
        ("amend_message", 8),
        ("reorder_commits", 14),
        ("squash_commits", 14),
        ("edit_commit", 16),
        ("stash_workflow", 10),
        ("reset_modes", 14),
    ],
    5: [
        ("clone_local", 8),
        ("add_remote", 6),
        ("push_first", 9),
        ("fetch_merge", 12),
        ("pull_rebase", 12),
        ("push_conflict", 15),
        ("create_offline_bundle", 10),
    ],
    6: [
        ("find_bisect", 16),
        ("reflog_recovery", 14),
        ("worktree", 10),
        ("inspect_objects", 14),
        ("custom_aliases_hooks", 12),
        ("filter_branch", 18),
        ("save_symbolic_head", 8),
        ("tree_list_root", 8),
        ("attach_git_note", 9),
        ("rev_parse_head_sha", 8),
        ("log_double_dot_range", 10),
        ("pickaxe_log_search", 10),
        ("triple_dot_log_range", 10),
    ],
    7: [
        ("setup_ignore", 8),
        ("ignore_node_modules", 7),
        ("untrack_cached", 10),
        ("keep_empty_dir", 7),
        ("ignore_exceptions", 10),
        ("clean_untracked", 8),
    ],
    8: [
        ("create_lightweight_tag", 8),
        ("create_tag", 10),
        ("show_tag", 7),
        ("tag_old_commit", 10),
        ("push_tags", 10),
    ],
    9: [
        ("export_format_patch", 10),
        ("git_mv_rename", 8),
        ("commit_signoff", 10),
        ("semantic_describe", 12),
        ("readme_first", 8),
        ("issue_close_message", 10),
        ("gh_pages_branch", 12),
        ("jekyll_post_front_matter", 10),
        ("write_git_blob", 12),
        ("mr_feature_branch", 9),
        ("add_gitlab_ci_yaml", 10),
        ("closes_issue_gitlab", 10),
        ("gitlab_md_issue_ref", 8),
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
