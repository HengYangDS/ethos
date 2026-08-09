from __future__ import annotations

import pytest

from ethos.adapters.admission.shell import command_risk
from ethos.adapters.admission.shell import git_stash_policy


@pytest.mark.parametrize(
    ("command", "risky", "unclassifiable", "reason"),
    [
        ("", False, False, "observe_only_command"),
        ("command env LC_ALL=C git -C /tmp status", False, False, "observe_only_command"),
        ("git worktree --porcelain list", False, False, "observe_only_command"),
        ("git worktree add /tmp/wt", True, False, "command_text_matches_mutation_pattern"),
        ("git branch -- --literal", True, False, "command_text_matches_mutation_pattern"),
        ("git branch --format", True, False, "command_text_matches_mutation_pattern"),
        ("git branch --format=", True, False, "command_text_matches_mutation_pattern"),
        ("git branch --contains HEAD topic", True, False, "command_text_matches_mutation_pattern"),
        ("git tag -n5 --list v1", False, False, "observe_only_command"),
        ("git -C", True, False, "command_text_matches_mutation_pattern"),
        ("git --unknown status", True, False, "command_text_matches_mutation_pattern"),
        ("git", True, False, "command_text_matches_mutation_pattern"),
        ("cat 'unterminated", True, True, "shell_parse_failed"),
        ("cat README.md | tee copy", True, True, "shell_composition_unsupported"),
        ("cat $(pwd)/README.md", True, True, "shell_syntax_unsupported"),
    ],
)
def test_command_risk_fail_closed_shell_and_git_matrix(
    command: str, risky: object, unclassifiable: object, reason: str
) -> None:
    assert command_risk(command) == {
        "tracked_mutation_risk": risky,
        "unclassifiable": unclassifiable,
        "reason": reason,
    }


@pytest.mark.parametrize(
    ("command", "forbidden", "operation", "reason"),
    [
        ("sudo env LC_ALL=C git stash list", False, "list", "observe_only_stash_read"),
        ("command git --no-pager stash show", False, "show", "observe_only_stash_read"),
        ("git stash", True, "push", "stash_is_hidden_change_carrier"),
        ("git stash pop", True, "push", "stash_is_hidden_change_carrier"),
        ("git status", False, "", "not_git_stash"),
        ("git stash $(pwd)", False, "", "not_git_stash"),
    ],
)
def test_git_stash_policy_unwraps_observation_and_rejects_effects(
    command: str, forbidden: object, operation: str, reason: str
) -> None:
    assert git_stash_policy(command) == {
        "forbidden": forbidden,
        "operation": operation,
        "reason": reason,
    }
