"""Accepted closeout renames legacy role refs to the names the paradigm fixes."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.admission.git_admission as git_admission
import ethos.adapters.mutation.accepted.legacy_roles as legacy_roles
from ethos.adapters.admission.ref_intent import write_ref_intent
from ethos.adapters.admission.role_rename import ROLE_RENAME_OPERATION
from ethos.adapters.admission.role_rename import legacy_role_renames
from ethos.adapters.admission.role_rename import role_rename_ref_report
from ethos.adapters.repo.git_effect_observation import compile_observed_git_effect
from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.adapters.store.state.lease.projection import observe_lease
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.coordination import LaneLease
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import git_effect_from_plan
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import canonical_json_digest
from ethos.contracts.value import mutable_json
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


def test_closeout_renames_a_legacy_release_ref_with_its_worktree(tmp_path: Path) -> None:
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


def test_closeout_refuses_a_legacy_release_rename_onto_an_existing_name(tmp_path: Path) -> None:
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
    bind = legacy_roles.bind_renamed_worktrees
    monkeypatch.setattr(legacy_roles, "bind_renamed_worktrees", lambda *_args: None)
    run_ethos(*_closeout(head, "--apply", "--authorize"), cwd=repo)
    assert git(repo, "symbolic-ref", "HEAD") == "refs/heads/accepted/train"

    monkeypatch.setattr(legacy_roles, "bind_renamed_worktrees", bind)
    resumed = run_ethos(*_closeout(head, "--apply", "--authorize"), cwd=repo)

    assert resumed["state"] == "branch_roles_renamed"
    assert git(repo, "branch", "--show-current") == "dev"
    assert git(candidate, "branch", "--show-current") == "candidate/dev"


@pytest.mark.parametrize(
    ("change", "gap"),
    [
        ("unauthorized", "authorization_required"),
        ("stale", "expected_head_mismatch"),
        ("target", "legacy_role_rename_target_exists:dev"),
        ("topic", "expected_state_required"),
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


def _commit_unreadable_table(repo: Path) -> str:
    """Commit a branch_roles table that the strict reader rejects and return its head."""
    workspace = repo / ".ethos/workspace.toml"
    workspace.write_text("[branch_roles]\naccepted_branch = 7\n")
    git(repo, "add", workspace.as_posix())
    git(repo, "commit", "-m", "chore: declare an unreadable role table")
    return git(repo, "rev-parse", "HEAD")


def test_an_unreadable_committed_table_renames_and_protects_nothing(tmp_path: Path) -> None:
    """An unreadable table names no legacy role, so it neither renames nor protects a ref."""
    repo, _candidate = start_adopted_candidate(tmp_path)
    head = _commit_unreadable_table(repo)
    zero = "0" * len(head)

    renamed = legacy_roles.rename_legacy_roles(
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

    report = run_ethos(*_closeout("0" * 40, "--authorize"), cwd=repo)

    assert report["verdict"] == "block"
    assert git(repo, "symbolic-ref", "HEAD") == "refs/heads/accepted/missing"


def test_committed_role_names_bind_retained_topics_at_unchanged_heads(tmp_path: Path) -> None:
    """A declared retired topic prefix identifies its unchanged standard destination."""
    repo, _candidate, head = _legacy_repository(tmp_path)
    git(repo, "branch", "submit/review", head)

    renames = legacy_role_renames(repo, head)

    assert renames["refs/heads/submit/review"] == ("refs/heads/proposal/review", head)


def _retained_topic(tmp_path: Path) -> tuple[Path, Path, str]:
    """Keep a signed topic with distinct committed, staged and working bytes."""
    repo, _candidate, _head = _legacy_repository(tmp_path)
    table = repo / ".ethos/workspace.toml"
    table.write_text(table.read_text() + 'work_branch_prefix = "task/"\n')
    git(repo, "add", table.as_posix())
    git(repo, "commit", "-m", "chore: retain legacy work topics")
    head = git(repo, "rev-parse", "HEAD")
    topic = tmp_path / "retained-topic"
    git(repo, "worktree", "add", "-b", "task/retained", topic.as_posix(), head)
    source = topic / "retained.txt"
    source.write_bytes(b"committed\n")
    git(topic, "add", "retained.txt")
    git(topic, "commit", "-m", "feat: preserve unique topic history")
    source.write_bytes(b"staged\n")
    git(topic, "add", "retained.txt")
    source.write_bytes(b"working\n")
    source.chmod(0o755)
    (topic / "new.txt").write_bytes(b"untracked\xff\x00")
    acquire_lease(
        state_database(repo),
        lease=LaneLease(
            lane_ref="task/retained",
            holder_ref="agent:test:case:agent-test",
            generation=7,
            expires_at=datetime.now(UTC) + timedelta(days=1),
        ),
    )
    return repo, topic, head


@pytest.mark.parametrize("name", ["retained-topic", 'retained "topic"\n非ASCII'])
def test_retained_topic_migration_preserves_index_bytes_and_holder(
    tmp_path: Path, name: str
) -> None:
    """A prefix transition must not clean, stage, rewrite history or acquire another holder."""
    repo, topic, head = _retained_topic(tmp_path)
    if name != topic.name:
        destination = tmp_path / name
        git(repo, "worktree", "move", topic.as_posix(), destination.as_posix())
        topic = destination
    topic_head = git(topic, "rev-parse", "HEAD")
    index = topic / git(topic, "rev-parse", "--git-path", "index")
    before_index = index.read_bytes()
    before_lease = observe_lease(state_database(repo), "task/retained").record()

    preview = run_ethos(*_closeout(head, "--authorize"), cwd=repo, full_payload=True)
    assert preview["state"] == "ready_to_rename", preview
    state = preview["data"]["branch_role_rename"]["state_digest"]
    renamed = run_ethos(
        *_closeout(head, "--apply", "--authorize", "--expect-state", state), cwd=repo
    )

    assert renamed["state"] == "branch_roles_renamed", renamed
    assert git(topic, "branch", "--show-current") == "work/retained"
    assert git(topic, "rev-parse", "HEAD") == topic_head
    assert not git(repo, "branch", "--list", "task/retained")
    assert index.read_bytes() == before_index
    assert (topic / "retained.txt").read_bytes() == b"working\n"
    assert (topic / "retained.txt").stat().st_mode & 0o777 == 0o755
    assert (topic / "new.txt").read_bytes() == b"untracked\xff\x00"
    assert git(topic, "show", ":retained.txt") == "staged"
    lease = observe_lease(state_database(repo), "work/retained").record()
    assert lease["holder_ref"] == before_lease["holder_ref"]
    assert lease["expires_at"] == before_lease["expires_at"]
    assert lease["generation"] == 8
    assert observe_lease(state_database(repo), "task/retained").state == "missing"
    replay = run_ethos(
        *_closeout(head, "--apply", "--authorize", "--expect-state", state), cwd=repo
    )
    assert replay["state"] == "branch_roles_renamed", replay
    assert observe_lease(state_database(repo), "work/retained").record()["generation"] == 8
    assert index.read_bytes() == before_index


@pytest.mark.parametrize("changed", ["refs", "binding", "lease"])
def test_completed_topic_migration_replay_requires_complete_poststate(
    tmp_path: Path, changed: str
) -> None:
    """A terminal receipt cannot report completion after any coordinate is rolled back."""
    repo, topic, head = _retained_topic(tmp_path)
    topic_head = git(topic, "rev-parse", "HEAD")
    preview = run_ethos(*_closeout(head, "--authorize"), cwd=repo, full_payload=True)
    state = preview["data"]["branch_role_rename"]["state_digest"]
    migrated = run_ethos(
        *_closeout(head, "--apply", "--authorize", "--expect-state", state), cwd=repo
    )
    assert migrated["state"] == "branch_roles_renamed", migrated
    if changed == "refs":
        for source, target, value in (
            ("accepted/train", "dev", head),
            ("candidate/train", "candidate/dev", head),
            ("task/retained", "work/retained", topic_head),
            ("submit/retained", "proposal/retained", head),
        ):
            git(repo, "-c", "core.hooksPath=/dev/null", "update-ref", f"refs/heads/{source}", value)
            git(repo, "-c", "core.hooksPath=/dev/null", "update-ref", "-d", f"refs/heads/{target}")
    elif changed == "binding":
        git(topic, "symbolic-ref", "HEAD", "refs/heads/task/retained")
    else:
        with closing(sqlite3.connect(state_database(repo))) as connection, connection:
            connection.execute(
                "update leases set lane_ref = 'task/retained', generation = 7 "
                "where lane_ref = 'work/retained'"
            )
    binding = git(topic, "symbolic-ref", "HEAD")
    index = (topic / git(topic, "rev-parse", "--git-path", "index")).read_bytes()

    blocked = run_ethos(*_closeout(head, "--authorize", "--expect-state", state), cwd=repo)

    assert blocked["verdict"] == "block", blocked
    assert "legacy_role_rename_state_stale" in blocked["required_gaps"], blocked
    assert git(topic, "symbolic-ref", "HEAD") == binding
    assert (topic / git(topic, "rev-parse", "--git-path", "index")).read_bytes() == index


@pytest.mark.parametrize("changed", ["index", "bytes", "mode", "new-ref", "lease", "collision"])
def test_retained_topic_preview_refuses_changed_preimage(tmp_path: Path, changed: str) -> None:
    """An unchanged accepted HEAD cannot authorize changed content, refs or coordination."""
    repo, topic, head = _retained_topic(tmp_path)
    preview = run_ethos(*_closeout(head, "--authorize"), cwd=repo, full_payload=True)
    state = preview["data"]["branch_role_rename"]["state_digest"]
    if changed == "index":
        git(topic, "add", "retained.txt")
    elif changed == "bytes":
        (topic / "new.txt").write_bytes(b"changed\xff\x00")
    elif changed == "mode":
        (topic / "new.txt").chmod(0o755)
    elif changed == "new-ref":
        git(repo, "branch", "submit/another", head)
    elif changed == "collision":
        git(repo, "branch", "proposal/retained", head)
        git(repo, "branch", "work/retained", head)
    else:
        with closing(sqlite3.connect(state_database(repo))) as connection, connection:
            connection.execute(
                "update leases set holder_ref = 'agent:test:case:other' "
                "where lane_ref = 'task/retained'"
            )

    blocked = run_ethos_blocked(
        *_closeout(head, "--apply", "--authorize", "--expect-state", state), cwd=repo
    )

    gap = (
        "legacy_role_rename_target_exists:work/retained"
        if changed == "collision"
        else "legacy_role_rename_state_stale"
    )
    assert gap in blocked["required_gaps"], blocked
    assert git(repo, "branch", "--show-current") == "accepted/train"
    assert git(topic, "branch", "--show-current") == "task/retained"
    assert observe_lease(state_database(repo), "task/retained").record()["generation"] == 7


def test_topic_preview_binds_tracked_bytes_even_when_git_assumes_unchanged(tmp_path: Path) -> None:
    """Native diff selection must not hide changed tracked bytes from a migration preimage."""
    repo, topic, head = _retained_topic(tmp_path)
    git(topic, "update-index", "--assume-unchanged", "retained.txt")
    preview = run_ethos(*_closeout(head, "--authorize"), cwd=repo, full_payload=True)
    state = preview["data"]["branch_role_rename"]["state_digest"]
    (topic / "retained.txt").write_bytes(b"changed but hidden\n")

    blocked = run_ethos_blocked(
        *_closeout(head, "--apply", "--authorize", "--expect-state", state), cwd=repo
    )

    assert "legacy_role_rename_state_stale" in blocked["required_gaps"], blocked
    assert git(topic, "branch", "--show-current") == "task/retained"


def test_topic_migration_excludes_lease_writers_during_native_ref_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A concurrent holder transition cannot slip between admission and ref mutation."""
    repo, _topic, head = _retained_topic(tmp_path)
    preview = run_ethos(*_closeout(head, "--authorize"), cwd=repo, full_payload=True)
    state = preview["data"]["branch_role_rename"]["state_digest"]
    execute = legacy_roles.execute_git_effect

    def competing_writer(*args, **kwargs):
        connection = sqlite3.connect(state_database(repo), timeout=0)
        try:
            with pytest.raises(sqlite3.OperationalError, match="locked"):
                connection.execute(
                    "update leases set generation = 99 where lane_ref = 'task/retained'"
                )
        finally:
            connection.close()
        return execute(*args, **kwargs)

    monkeypatch.setattr(legacy_roles, "execute_git_effect", competing_writer)
    migrated = run_ethos(
        *_closeout(head, "--apply", "--authorize", "--expect-state", state), cwd=repo
    )

    assert migrated["state"] == "branch_roles_renamed", migrated
    assert observe_lease(state_database(repo), "work/retained").record()["generation"] == 8


def test_retained_topic_recovers_binding_and_lease_without_repeating_ref_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A ref result alone is not completion; recovery preserves the original staged bytes."""
    repo, topic, head = _retained_topic(tmp_path)
    preview = run_ethos(*_closeout(head, "--authorize"), cwd=repo, full_payload=True)
    state = preview["data"]["branch_role_rename"]["state_digest"]
    bind = legacy_roles.bind_renamed_worktrees

    def interrupted(*_args: object) -> None:
        message = "interrupted binding"
        raise OSError(message)

    monkeypatch.setattr(legacy_roles, "bind_renamed_worktrees", interrupted)
    with pytest.raises(OSError, match="interrupted binding"):
        run_ethos(*_closeout(head, "--apply", "--authorize", "--expect-state", state), cwd=repo)
    assert git(repo, "rev-parse", "dev") == head
    assert git(topic, "symbolic-ref", "HEAD") == "refs/heads/task/retained"
    assert observe_lease(state_database(repo), "task/retained").record()["generation"] == 7

    monkeypatch.setattr(legacy_roles, "bind_renamed_worktrees", bind)
    recovered = run_ethos(
        *_closeout(head, "--apply", "--authorize", "--expect-state", state), cwd=repo
    )

    assert recovered["state"] == "branch_roles_renamed", recovered
    assert git(topic, "branch", "--show-current") == "work/retained"
    assert git(topic, "show", ":retained.txt") == "staged"
    assert observe_lease(state_database(repo), "work/retained").record()["generation"] == 8


@pytest.mark.parametrize("phase", ["partial-binding", "terminal"])
def test_topic_migration_recovers_partial_completion_read_only_before_apply(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    """Recover after the accepted binding or Lease commit, never replaying the ref effect."""
    repo, topic, head = _retained_topic(tmp_path)
    preview = run_ethos(*_closeout(head, "--authorize"), cwd=repo, full_payload=True)
    state = preview["data"]["branch_role_rename"]["state_digest"]
    bind, record = legacy_roles.bind_renamed_worktrees, legacy_roles.record_attestations
    before_index = (topic / git(topic, "rev-parse", "--git-path", "index")).read_bytes()

    def partial_binding(root, _targets):
        bind(root, {"refs/heads/accepted/train": "refs/heads/dev"})
        message = "partial binding interruption"
        raise OSError(message)

    def terminal_failure(root, members):
        if members[0].predicate == "effect:branch-roles-rename":
            message = "terminal interruption"
            raise OSError(message)
        return record(root, members)

    monkeypatch.setattr(
        legacy_roles,
        "bind_renamed_worktrees",
        partial_binding if phase == "partial-binding" else bind,
    )
    monkeypatch.setattr(legacy_roles, "record_attestations", terminal_failure)
    with pytest.raises(OSError, match="interruption"):
        run_ethos(*_closeout(head, "--apply", "--authorize", "--expect-state", state), cwd=repo)
    monkeypatch.setattr(legacy_roles, "bind_renamed_worktrees", bind)
    monkeypatch.setattr(legacy_roles, "record_attestations", record)
    original_binding = git(topic, "symbolic-ref", "HEAD")
    resumed = run_ethos(*_closeout(head, "--authorize", "--expect-state", state), cwd=repo)
    assert resumed["state"] == "ready_to_resume_rename", resumed
    assert git(topic, "symbolic-ref", "HEAD") == original_binding

    def no_repeated_ref_transaction(*_args, **_kwargs):
        pytest.fail("recovery attempted the completed native ref transaction")

    monkeypatch.setattr(
        "ethos.adapters.repo.git_effects._apply_git_ref_transaction", no_repeated_ref_transaction
    )
    recovered = run_ethos(
        *_closeout(head, "--apply", "--authorize", "--expect-state", state), cwd=repo
    )
    assert recovered["state"] == "branch_roles_renamed", recovered
    assert git(topic, "rev-parse", "HEAD") == git(repo, "rev-parse", "work/retained")
    assert observe_lease(state_database(repo), "work/retained").record()["generation"] == 8
    assert (topic / git(topic, "rev-parse", "--git-path", "index")).read_bytes() == before_index


def test_recovery_refuses_preparation_omitting_selected_topic_lease(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Digest-valid custody cannot omit coordination from the selected ref transition."""
    repo, topic, head = _retained_topic(tmp_path)
    preview = run_ethos(*_closeout(head, "--authorize"), cwd=repo, full_payload=True)
    state = preview["data"]["branch_role_rename"]["state_digest"]
    record = legacy_roles.record_attestations

    def preparation_interruption(root, members):
        result = record(root, members)
        if members[0].predicate == "observation:branch-roles-rename":
            message = "prepared interruption"
            raise OSError(message)
        return result

    monkeypatch.setattr(legacy_roles, "record_attestations", preparation_interruption)
    with pytest.raises(OSError, match="prepared interruption"):
        run_ethos(*_closeout(head, "--apply", "--authorize", "--expect-state", state), cwd=repo)
    monkeypatch.setattr(legacy_roles, "record_attestations", record)
    token, members = legacy_roles.read_attestation_set(repo)
    prepared = next(item for item in members if item.predicate == "observation:branch-roles-rename")
    body = mutable_json(prepared.payload.body)
    plan = TransitionPlan.model_validate(body["plan"])
    effect = git_effect_from_plan(plan)
    values = mutable_json(plan.facts["values"])
    values["role_rename_snapshot"]["leases"] = {}
    paired = {
        source: (target, effect.updates[source].expected)
        for source, target in values["role_renames"].items()
    }
    state = canonical_json_digest(
        {"head": head, "renames": paired, "snapshot": values["role_rename_snapshot"]}
    )
    values["role_rename_state"] = state
    body.update(
        state_digest=state,
        plan=compile_observed_git_effect(
            repo,
            None,
            effect,
            head=head,
            policy={"operation": ROLE_RENAME_OPERATION},
            values=values,
        ).model_dump(mode="json"),
    )
    replacement = Attestation.issue(
        {
            **prepared.model_dump(exclude={"id"}),
            "subject": f"branch-roles:{state}",
            "payload": {"kind": "observation:native", "body": body},
            "effect_digest": state,
            "plan_digest": body["plan"]["digest"],
        }
    )
    monkeypatch.setattr(legacy_roles, "read_attestation_set", lambda _root: (token, (replacement,)))

    blocked = run_ethos(*_closeout(head, "--authorize", "--expect-state", state), cwd=repo)

    assert blocked["verdict"] == "block", blocked
    assert "legacy_role_rename_preparation_invalid" in blocked["required_gaps"], blocked
    assert git(topic, "branch", "--show-current") == "task/retained"
    assert observe_lease(state_database(repo), "task/retained").record()["generation"] == 7


def test_recovery_preview_refuses_changed_ref_before_restoring_bindings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A carried ref receipt cannot authorize bindings after its target has moved."""
    repo, topic, head = _retained_topic(tmp_path)
    preview = run_ethos(*_closeout(head, "--authorize"), cwd=repo, full_payload=True)
    state = preview["data"]["branch_role_rename"]["state_digest"]
    bind = legacy_roles.bind_renamed_worktrees

    def interrupted(*_args: object) -> None:
        message = "interrupted binding"
        raise OSError(message)

    monkeypatch.setattr(legacy_roles, "bind_renamed_worktrees", interrupted)
    with pytest.raises(OSError, match="interrupted binding"):
        run_ethos(*_closeout(head, "--apply", "--authorize", "--expect-state", state), cwd=repo)
    monkeypatch.setattr(legacy_roles, "bind_renamed_worktrees", bind)
    git(repo, "-c", "core.hooksPath=/dev/null", "update-ref", "refs/heads/work/retained", head)

    blocked = run_ethos(*_closeout(head, "--authorize", "--expect-state", state), cwd=repo)

    assert blocked["verdict"] == "block", blocked
    assert "legacy_role_rename_state_stale" in blocked["required_gaps"], blocked
    assert git(topic, "symbolic-ref", "HEAD") == "refs/heads/task/retained"
    assert observe_lease(state_database(repo), "task/retained").record()["generation"] == 7
