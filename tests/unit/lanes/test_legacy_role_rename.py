"""Accepted closeout renames legacy role refs to the names the paradigm fixes."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import ethos.adapters.admission.git_admission as git_admission
import ethos.adapters.mutation.accepted.legacy_roles as legacy_roles
from ethos.adapters.admission.ref_intent import write_ref_intent
from ethos.adapters.admission.role_rename import ROLE_RENAME_OPERATION
from ethos.adapters.admission.role_rename import role_rename_ref_report
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.semantic import canonical_json_digest
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import git
from tests.support.governed_repository import start_adopted_candidate

if TYPE_CHECKING:
    from pathlib import Path

_LEGACY = (
    'accepted_branch = "accepted/train"\n'
    'candidate_branch = "candidate/train"\n'
    'proposal_branch_prefix = "submit/"\n'
)

# After the rename, the next step is the Work Lane that removes the legacy declarations.
_LEGACY_DECLARATIONS = [
    f"repository_paradigm_branch_roles:.ethos/workspace.toml:branch_roles.{field}"
    for field in ("accepted_branch", "candidate_branch", "proposal_branch_prefix")
]


def _legacy_repository(tmp_path: Path) -> tuple[Path, Path, str]:
    """Adopt a repository whose committed table and refs still use legacy role names."""
    repo, candidate = start_adopted_candidate(tmp_path)
    workspace = repo / ".ethos/workspace.toml"
    workspace.write_text(f"[branch_roles]\n{_LEGACY}")
    git(repo, "add", workspace.as_posix())
    git(repo, "commit", "-m", "chore: declare legacy branch roles")
    git(repo, "branch", "-m", "dev", "accepted/train")
    git(repo, "branch", "-m", "candidate/dev", "candidate/train")
    head = git(repo, "rev-parse", "HEAD")
    git(candidate, "reset", "--hard", head)
    return repo, candidate, head


def _closeout(head: str, *extra: str) -> list[str]:
    return ["land", "--closeout", *extra, "--expect-head", head, "--json"]


def test_closeout_renames_legacy_role_refs_without_moving_content(tmp_path: Path) -> None:
    repo, candidate, head = _legacy_repository(tmp_path)

    preview = run_ethos(*_closeout(head, "--authorize"), cwd=repo)
    assert preview["state"] == "ready_to_rename", preview
    assert git(repo, "branch", "--show-current") == "accepted/train"

    renamed = run_ethos(*_closeout(head, "--apply", "--authorize"), cwd=repo)

    assert renamed["state"] == "branch_roles_renamed", renamed
    assert git(repo, "rev-parse", "dev") == head == git(repo, "rev-parse", "candidate/dev")
    assert not git(repo, "branch", "--list", "accepted/train", "candidate/train")
    assert git(repo, "branch", "--show-current") == "dev"
    assert git(candidate, "branch", "--show-current") == "candidate/dev"
    rerun = run_ethos_blocked(*_closeout(head, "--apply", "--authorize"), cwd=repo)
    assert rerun["required_gaps"] == _LEGACY_DECLARATIONS


def test_closeout_finishes_an_interrupted_worktree_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, candidate, head = _legacy_repository(tmp_path)
    bind = legacy_roles.bind_renamed_worktrees
    monkeypatch.setattr(legacy_roles, "bind_renamed_worktrees", lambda *_args: None)
    run_ethos(*_closeout(head, "--apply", "--authorize"), cwd=repo)
    assert git(repo, "symbolic-ref", "HEAD") == "refs/heads/accepted/train"

    monkeypatch.setattr(legacy_roles, "bind_renamed_worktrees", bind)
    resumed = run_ethos_blocked(*_closeout(head, "--apply", "--authorize"), cwd=repo)

    assert resumed["required_gaps"] == _LEGACY_DECLARATIONS
    assert git(repo, "branch", "--show-current") == "dev"
    assert git(candidate, "branch", "--show-current") == "candidate/dev"


@pytest.mark.parametrize(
    ("change", "gap"),
    [
        ("unauthorized", "authorization_required"),
        ("stale", "expected_head_mismatch"),
        ("target", "legacy_role_rename_target_exists:dev"),
        ("topic", "legacy_role_rename_topic_refs_present:submit/"),
    ],
)
def test_closeout_refuses_a_rename_it_cannot_complete_exactly(
    tmp_path: Path, change: str, gap: str
) -> None:
    repo, _candidate, head = _legacy_repository(tmp_path)
    flags = ["--apply"] if change == "unauthorized" else ["--apply", "--authorize"]
    expect = "0" * len(head) if change == "stale" else head
    if change == "target":
        git(repo, "branch", "dev", head)
    elif change == "topic":
        git(repo, "branch", "submit/review", head)

    report = run_ethos_blocked(*_closeout(expect, *flags), cwd=repo)

    assert gap in report["required_gaps"], report
    assert git(repo, "rev-parse", "accepted/train") == head


def test_git_admission_protects_legacy_role_refs_until_their_rename(tmp_path: Path) -> None:
    repo, _candidate, head = _legacy_repository(tmp_path)
    zero = "0" * len(head)

    moved = git_admission.ref_move_admission_report(
        root=repo, ref_name="refs/heads/accepted/train", old_value=head, new_value=zero
    )
    assert moved["required_gaps"] == ["legacy_role_ref_protected"]
    assert role_rename_ref_report(repo, "refs/heads/work/other", head, zero) is None

    write_ref_intent(
        root=repo,
        ref_name="refs/heads/dev",
        update=GitRefUpdate(expected=zero, desired=head),
        operation=ROLE_RENAME_OPERATION,
        plan_digest=canonical_json_digest({"rename": "partial"}),
    )
    partial = role_rename_ref_report(repo, "refs/heads/dev", zero, head)
    assert partial is not None
    assert partial["required_gaps"] == ["legacy_role_rename_shape_invalid"]
