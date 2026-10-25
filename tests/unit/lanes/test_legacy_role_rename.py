"""Accepted closeout renames legacy role refs to the names the paradigm fixes."""

from __future__ import annotations

from pathlib import Path

import pytest

import ethos.adapters.admission.git_admission as git_admission
import ethos.adapters.mutation.branch_roles as branch_roles
from ethos.adapters.admission.ref_intent import write_ref_intent
from ethos.adapters.admission.role_rename import ROLE_RENAME_OPERATION
from ethos.adapters.admission.role_rename import role_rename_ref_report
from ethos.adapters.store.state.lease.lifecycle.transitions import apply_lease_operation
from ethos.adapters.store.state.lease.projection import observe_lease
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.coordination import LeaseOperationRequest
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.semantic import canonical_json_digest
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import create_change_source_lane
from tests.support.governed_repository import git
from tests.support.governed_repository import start_adopted_candidate

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


def _legacy_repository(tmp_path: Path, *, release: str = "") -> tuple[Path, Path, str]:
    """Adopt a repository whose committed table and refs still use legacy role names."""
    repo, candidate = start_adopted_candidate(tmp_path)
    workspace = repo / ".ethos/workspace.toml"
    declared = f'release_branch = "{release}"\n' if release else ""
    workspace.write_text(f"[branch_roles]\n{declared}{_LEGACY}")
    git(repo, "add", workspace.as_posix())
    git(repo, "commit", "-m", "chore: declare legacy branch roles")
    git(repo, "branch", "-m", "dev", "accepted/train")
    git(repo, "branch", "-m", "candidate/dev", "candidate/train")
    head = git(repo, "rev-parse", "HEAD")
    git(candidate, "reset", "--hard", head)
    return repo, candidate, head


def _closeout(head: str, *extra: str) -> list[str]:
    return ["land", "--closeout", *extra, "--expect-head", head, "--json"]


def test_closeout_renames_legacy_role_refs_without_moving_content(
    tmp_path: Path,
) -> None:
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


def test_closeout_renames_a_legacy_release_ref_with_its_worktree(
    tmp_path: Path,
) -> None:
    """A declared legacy release name renames to the fixed name, and its worktree follows."""
    repo, _candidate, head = _legacy_repository(tmp_path, release="master")
    release = tmp_path / "repo-master"
    git(repo, "branch", "master", head)
    git(repo, "worktree", "add", release.as_posix(), "master")

    renamed = run_ethos(*_closeout(head, "--apply", "--authorize"), cwd=repo)

    assert renamed["state"] == "branch_roles_renamed", renamed
    assert git(repo, "rev-parse", "main") == head
    assert not git(repo, "branch", "--list", "master")
    assert git(release, "branch", "--show-current") == "main"


def test_closeout_renames_a_lone_legacy_release_ref_from_the_standard_accepted_root(
    tmp_path: Path,
) -> None:
    """A table that names only its release branch under a legacy name still renames it."""
    repo, candidate = start_adopted_candidate(tmp_path)
    workspace = repo / ".ethos/workspace.toml"
    workspace.write_text('[branch_roles]\nrelease_branch = "master"\n')
    git(repo, "add", workspace.as_posix())
    git(repo, "commit", "-m", "chore: declare a legacy release name")
    head = git(repo, "rev-parse", "HEAD")
    git(candidate, "reset", "--hard", head)
    git(repo, "branch", "master", head)

    renamed = run_ethos(*_closeout(head, "--apply", "--authorize"), cwd=repo)

    assert renamed["state"] == "branch_roles_renamed", renamed
    assert git(repo, "rev-parse", "main") == head
    assert not git(repo, "branch", "--list", "master")
    assert git(repo, "branch", "--show-current") == "dev"


def test_closeout_refuses_a_legacy_release_rename_onto_an_existing_name(
    tmp_path: Path,
) -> None:
    """The release rename never overwrites a live ref that already holds the fixed name."""
    repo, _candidate, head = _legacy_repository(tmp_path, release="master")
    git(repo, "branch", "master", head)
    git(repo, "branch", "main", head)

    blocked = run_ethos_blocked(*_closeout(head, "--apply", "--authorize"), cwd=repo)

    assert "legacy_role_rename_target_exists:main" in blocked["required_gaps"], blocked
    assert git(repo, "rev-parse", "master") == head


def test_closeout_finishes_an_interrupted_worktree_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, candidate, head = _legacy_repository(tmp_path)
    bind = branch_roles.bind_renamed_worktrees
    monkeypatch.setattr(branch_roles, "bind_renamed_worktrees", lambda *_args: None)
    run_ethos(*_closeout(head, "--apply", "--authorize"), cwd=repo)
    assert git(repo, "symbolic-ref", "HEAD") == "refs/heads/accepted/train"

    monkeypatch.setattr(branch_roles, "bind_renamed_worktrees", bind)
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


def test_git_admission_protects_legacy_role_refs_until_their_rename(
    tmp_path: Path,
) -> None:
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


def _commit_unreadable_table(repo: Path) -> str:
    """Commit a branch_roles table that the strict reader rejects and return its head."""
    workspace = repo / ".ethos/workspace.toml"
    workspace.write_text("[branch_roles]\naccepted_branch = 7\n")
    git(repo, "add", workspace.as_posix())
    git(repo, "commit", "-m", "chore: declare an unreadable role table")
    return git(repo, "rev-parse", "HEAD")


def test_an_unreadable_committed_table_renames_and_protects_nothing(
    tmp_path: Path,
) -> None:
    """An unreadable table names no legacy role, so it neither renames nor protects a ref."""
    repo, _candidate = start_adopted_candidate(tmp_path)
    head = _commit_unreadable_table(repo)
    zero = "0" * len(head)

    renamed = branch_roles.rename_legacy_roles(
        repo, current_head=head, apply=True, authorized=True, expect_head=head
    )

    assert renamed is None
    assert role_rename_ref_report(repo, "refs/heads/dev", head, zero) is None
    write_ref_intent(
        root=repo,
        ref_name="refs/heads/dev",
        update=GitRefUpdate(expected=head, desired=zero),
        operation=ROLE_RENAME_OPERATION,
        plan_digest=canonical_json_digest({"rename": "unreadable"}),
    )
    unreadable = role_rename_ref_report(repo, "refs/heads/dev", head, zero)
    assert unreadable is not None
    assert unreadable["required_gaps"] == ["legacy_role_rename_policy_unavailable"]


def test_resume_keeps_a_binding_whose_own_table_is_unreadable(tmp_path: Path) -> None:
    """A worktree left on a missing ref keeps that binding when its own table is unreadable."""
    repo, _candidate = start_adopted_candidate(tmp_path)
    _commit_unreadable_table(repo)
    git(repo, "symbolic-ref", "HEAD", "refs/heads/accepted/missing")

    branch_roles.resume_renamed_bindings(repo)

    assert git(repo, "symbolic-ref", "HEAD") == "refs/heads/accepted/missing"


def _retained_topic(tmp_path: Path) -> tuple[Path, Path, str]:
    repo, _candidate, _head = _legacy_repository(tmp_path)
    workspace = repo / ".ethos/workspace.toml"
    workspace.write_text(workspace.read_text() + 'work_branch_prefix = "task/"\n')
    git(repo, "add", workspace.as_posix())
    git(repo, "commit", "-m", "chore: retain legacy authoring names")
    lane = create_change_source_lane(
        repo,
        tmp_path / "repo-work-retained",
        branch="task/retained",
        holder_ref="agent:test:case:agent-test",
        base_ref="accepted/train",
    )
    staged = lane / "retained.txt"
    staged.write_bytes(b"staged intent\n")
    git(lane, "add", "retained.txt")
    staged.write_bytes(b"unstaged intent\n")
    (lane / "local.txt").write_bytes(b"untracked user content\n")
    (lane / "README.md").unlink()
    return repo, lane, git(lane, "rev-parse", "HEAD")


def test_native_paradigm_repair_migrates_only_the_owned_retained_topic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, lane, head = _retained_topic(tmp_path)
    index = Path(git(lane, "rev-parse", "--path-format=absolute", "--git-path", "index"))
    before = (
        index.read_bytes(),
        git(lane, "status", "--porcelain"),
        {name: (lane / name).read_bytes() for name in ("retained.txt", "local.txt")},
    )
    lease = observe_lease(state_database(repo), "task/retained").record()
    protected = git(repo, "rev-parse", "accepted/train", "candidate/train")

    preview = run_ethos("lane", "repair-paradigm", "--json", cwd=lane)
    assert preview["state"] == "ready_to_rename", preview
    assert git(lane, "branch", "--show-current") == "task/retained"
    binding_reads = []
    native = branch_roles.run_git

    def observed(path, *arguments, **kwargs):
        if arguments[:2] == ("symbolic-ref", "--quiet"):
            binding_reads.append(path)
        return native(path, *arguments, **kwargs)

    monkeypatch.setattr(branch_roles, "run_git", observed)
    migrated = run_ethos("lane", "repair-paradigm", "--apply", "--json", cwd=lane)

    assert migrated["state"] == "topic_identity_migrated", migrated
    assert binding_reads == [lane]
    assert git(lane, "branch", "--show-current") == "work/retained"
    assert not git(repo, "branch", "--list", "task/retained")
    assert git(lane, "rev-parse", "HEAD") == head
    assert protected == git(repo, "rev-parse", "accepted/train", "candidate/train")
    assert before == (
        index.read_bytes(),
        git(lane, "status", "--porcelain"),
        {name: (lane / name).read_bytes() for name in ("retained.txt", "local.txt")},
    )
    assert not (lane / "README.md").exists()
    assert observe_lease(state_database(repo), "task/retained").state == "missing"
    renamed = observe_lease(state_database(repo), "work/retained").record()
    assert renamed["holder_ref"] == lease["holder_ref"]
    assert renamed["expires_at"] == lease["expires_at"]
    assert renamed["generation"] == lease["generation"] + 1


@pytest.mark.parametrize("obstacle", ["foreign-holder", "target-ref"])
def test_retained_topic_migration_refuses_without_changing_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, obstacle: str
) -> None:
    repo, lane, head = _retained_topic(tmp_path)
    before = observe_lease(state_database(repo), "task/retained").record()
    if obstacle == "foreign-holder":
        monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:other")
    else:
        git(repo, "branch", "work/retained", head)

    refused = run_ethos_blocked("lane", "repair-paradigm", "--apply", "--json", cwd=lane)

    assert refused["required_gaps"], refused
    assert git(lane, "branch", "--show-current") == "task/retained"
    assert git(lane, "rev-parse", "HEAD") == head
    assert observe_lease(state_database(repo), "task/retained").record() == before
    assert (lane / "retained.txt").read_bytes() == b"unstaged intent\n"
    assert (lane / "local.txt").read_bytes() == b"untracked user content\n"


@pytest.mark.parametrize("projection", ["worktree", "lease"])
def test_retained_topic_recovers_projection_forward_from_the_attested_ref_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, projection: str
) -> None:
    repo, lane, head = _retained_topic(tmp_path)
    operation = "bind_renamed_worktrees" if projection == "worktree" else "migrate_lease"
    project = getattr(branch_roles, operation)

    def interrupted(*_args, **_kwargs):
        msg = "interrupted worktree projection"
        raise OSError(msg)

    monkeypatch.setattr(branch_roles, operation, interrupted)
    partial = run_ethos_blocked("lane", "repair-paradigm", "--apply", "--json", cwd=lane)
    assert partial["state"] == "partial_transition", partial
    assert git(repo, "rev-parse", "work/retained") == head
    assert not git(repo, "branch", "--list", "task/retained")
    assert observe_lease(state_database(repo), "task/retained").state == "valid"

    monkeypatch.setattr(branch_roles, operation, project)
    resumed = run_ethos("lane", "repair-paradigm", "--apply", "--json", cwd=lane)

    assert resumed["state"] == "topic_identity_migrated", resumed
    assert git(lane, "branch", "--show-current") == "work/retained"
    assert git(lane, "rev-parse", "HEAD") == head
    assert observe_lease(state_database(repo), "work/retained").state == "valid"
    assert observe_lease(state_database(repo), "task/retained").state == "missing"
    assert (lane / "retained.txt").read_bytes() == b"unstaged intent\n"
    assert (lane / "local.txt").read_bytes() == b"untracked user content\n"


def test_retained_topic_recovery_requires_the_same_fresh_lease_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, lane, head = _retained_topic(tmp_path)
    row = observe_lease(state_database(repo), "task/retained").record()

    def interrupted(*_args):
        message = "interrupted worktree projection"
        raise OSError(message)

    with monkeypatch.context() as patch:
        patch.setattr(branch_roles, "bind_renamed_worktrees", interrupted)
        partial = run_ethos_blocked("lane", "repair-paradigm", "--apply", "--json", cwd=lane)
    assert partial["state"] == "partial_transition", partial
    renewed = apply_lease_operation(
        state_database(repo),
        request=LeaseOperationRequest(
            operation="renew",
            branch="task/retained",
            holder_ref=row["holder_ref"],
            generation=row["generation"],
            expires_at=row["expires_at"],
            apply=True,
        ),
    )

    refused = run_ethos_blocked("lane", "repair-paradigm", "--apply", "--json", cwd=lane)

    assert refused["required_gaps"] == ["retained_topic_recovery_binding_stale"], refused
    assert observe_lease(state_database(repo), "task/retained").record() == renewed
    assert observe_lease(state_database(repo), "work/retained").state == "missing"
    assert git(lane, "branch", "--show-current") == "task/retained"
    assert git(repo, "rev-parse", "work/retained") == head
    assert (lane / "retained.txt").read_bytes() == b"unstaged intent\n"
