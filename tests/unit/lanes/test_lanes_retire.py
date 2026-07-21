from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
from functools import partial
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.dirty.core as repo_dirty
import ethos.adapters.store.state.lease.lifecycle.core as state
import ethos.adapters.store.state.lease.projection as state_read
from ethos.adapters.mutation.lane_retirement import core
from ethos.adapters.mutation.lane_retirement.core import LinkedRetirementRequest
from ethos.adapters.mutation.lanes import start_work_lane
from ethos.adapters.repo import coordination as repo_coordination
from ethos.adapters.repo.dirty.core import committed_change_paths
from ethos.adapters.repo.dirty.core import dirty_provenance
from ethos.adapters.repo.status.bindings import has_changed_paths
from ethos.adapters.repo.status.bindings import worktree_binding
from ethos.adapters.repo.status.core import workspace_status
from tests.support.contract_helpers import commit_fixture_file
from tests.support.lane_helpers import add_candidate_worktree
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo

type MonkeyPatch = pytest.MonkeyPatch


if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any
_LANDED_BRANCH = "work/landed"
_LEASE_HOLDER = "agent:test:case:agent-a"
_UNAVAILABLE_SUMMARY = dict.fromkeys(("tracked", "untracked", "deleted", "conflicted"), 0) | {
    "unavailable": 1
}
_NO_TEMPORARY_PROBES = {"count": 0, "paths": [], "truncated": False}
_UNKNOWN_FOREIGN_LANES = [
    {"branch": "work/unknown", "lease_state": "leased", "coordination_state": "unknown"}
]


def _landed_lane(tmp_path: Path, *, lease_holder: str = "") -> tuple[Path, Path, Path]:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    landed = tmp_path / "repo-work-landed"
    git(repo, "worktree", "add", "-b", _LANDED_BRANCH, landed.as_posix(), "dev")
    database = repo / ".ethos" / "state" / "state.sqlite"
    if lease_holder:
        state.acquire_lease(
            database,
            subject=_LANDED_BRANCH,
            holder_ref=lease_holder,
            ttl_seconds=3600,
            payload={"expected_head": git(landed, "rev-parse", "HEAD")},
        )
    return (repo, landed, database)


def _legacy_leases(repo: Path, landed: Path, *branches: tuple[str, str]) -> Path:
    path = repo / ".cache/local-state/worktree/leases.json"
    path.parent.mkdir(parents=True)
    leases = [
        {"branch": branch, "owner": owner, "expires_at": "2999-01-01T00:00:00Z"}
        for branch, owner in branches
    ]
    leases[0]["worktree_path"] = landed.as_posix()
    path.write_text(json.dumps({"schema_version": 1, "leases": leases}), encoding="utf-8")
    return path


def _assert_unavailable(report: dict[str, Any], error: str) -> None:
    assert (report["dirty"], report["state"], report["entries"], report["summary"]) == (
        True,
        "unavailable",
        [],
        _UNAVAILABLE_SUMMARY,
    )
    assert error in str(report["error"])


def _retire_landed(
    root: Path,
    *,
    branch: str | None = None,
    expect_head: str | None = None,
    apply: bool = False,
) -> dict[str, object]:
    return core.retire_linked_work_lane(
        root=root,
        mode="landed",
        request=LinkedRetirementRequest(
            branch=branch,
            expect_head=expect_head,
            apply=apply,
        ),
    )


def test_retire_plans_only_merged_lanes(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    landed = tmp_path / "repo-work-landed"
    active = tmp_path / "repo-work-active"
    git(repo, "worktree", "add", "-b", "work/landed", landed.as_posix(), "dev")
    git(repo, "worktree", "add", "-b", "work/active", active.as_posix(), "dev")
    commit_fixture_file(active, "README.md", "# active\n", "active work")
    report = _retire_landed(repo)
    assert (report["ok"], report["state"], report["required_gaps"]) == (True, "planned", [])
    lanes = {lane["branch"]: lane for lane in report["lanes"]}
    assert lanes["work/landed"]["retire_ready"] is True
    assert lanes["work/landed"]["required_gaps"] == []
    assert lanes["work/active"]["retire_ready"] is False
    assert lanes["work/active"]["required_gaps"] == ["work_lane_not_merged"]


def test_retire_rejects_legacy_owner_projection(monkeypatch, tmp_path: Path) -> None:
    repo, landed, _database = _landed_lane(tmp_path)
    _legacy_leases(repo, landed, (_LANDED_BRANCH, "agent-json"))
    monkeypatch.setenv("ETHOS_ACTOR", "agent-json")
    report = _retire_landed(repo, branch=_LANDED_BRANCH)
    assert (report["ok"], report["state"]) == (False, "blocked")
    assert report["required_gaps"] == ["foreign_work_lane_retire_authority_required"]
    selected = next(lane for lane in report["lanes"] if lane["branch"] == _LANDED_BRANCH)
    assert selected["lease"]["holder_ref"] == ""
    assert selected["lease_state"] == "missing"


def test_retire_preserves_unverified_json_projection(monkeypatch, tmp_path: Path) -> None:
    repo, landed, _database = _landed_lane(tmp_path)
    head = git(repo, "rev-parse", _LANDED_BRANCH)
    lease_path = _legacy_leases(
        repo,
        landed,
        (_LANDED_BRANCH, "agent-json"),
        ("work/other", "agent-other"),
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent-json")
    report = _retire_landed(repo, branch=_LANDED_BRANCH, expect_head=head, apply=True)
    assert (report["ok"], report["state"]) == (False, "blocked")
    assert report["required_gaps"] == ["foreign_work_lane_retire_authority_required"]
    assert landed.exists()
    assert git(repo, "branch", "--list", _LANDED_BRANCH) != ""
    leases = json.loads(lease_path.read_text(encoding="utf-8"))["leases"]
    assert [lease["branch"] for lease in leases] == [_LANDED_BRANCH, "work/other"]


def test_retire_block_explains_required_actor(monkeypatch, tmp_path: Path) -> None:
    repo, landed, _database = _landed_lane(tmp_path, lease_holder=_LEASE_HOLDER)
    landed_head = git(landed, "rev-parse", "HEAD")
    monkeypatch.delenv("ETHOS_ACTOR", raising=False)
    blocked = _retire_landed(repo, branch=_LANDED_BRANCH, expect_head=landed_head, apply=True)
    assert (blocked["ok"], blocked["required_gaps"]) == (
        False,
        ["foreign_work_lane_retire_authority_required"],
    )
    mutation = blocked["mutation"]
    request = mutation["request"]
    expected = mutation["decision"]["subject"]["expected_state"]
    assert (
        request["expect_head"],
        expected["ref"],
        expected["invocation_holder_ref"],
        expected["required_holder_ref"],
    ) == (
        landed_head,
        f"refs/heads/{_LANDED_BRANCH}",
        "",
        _LEASE_HOLDER,
    )
    assert mutation["decision"]["verdict"] == "block"
    assert blocked["next_action"] == "set ETHOS_ACTOR to the current holder_ref or obtain handoff"


def test_retire_requires_matching_owner(monkeypatch, tmp_path: Path) -> None:
    repo, landed, _database = _landed_lane(tmp_path, lease_holder=_LEASE_HOLDER)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-b")
    blocked = _retire_landed(repo, branch="work/landed")
    assert (blocked["ok"], blocked["state"]) == (False, "blocked")
    assert blocked["required_gaps"] == ["foreign_work_lane_retire_authority_required"]
    assert landed.exists()
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-a")
    allowed = _retire_landed(repo, branch=_LANDED_BRANCH)
    assert (allowed["ok"], allowed["state"], allowed["required_gaps"]) == (True, "planned", [])


def test_retire_apply_requires_branch(tmp_path: Path) -> None:
    repo, landed, _database = _landed_lane(tmp_path)
    report = _retire_landed(repo, apply=True)
    assert (report["ok"], report["required_gaps"]) == (False, ["retire_branch_required"])
    assert landed.exists()


def test_retire_reports_missing_branch(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    report = _retire_landed(repo, branch="work/missing")
    assert report["required_gaps"] == ["retire_branch_not_found"]


def test_retire_projects_removal_failure(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    repo, landed, _database = _landed_lane(tmp_path, lease_holder=_LEASE_HOLDER)
    head = git(landed, "rev-parse", "HEAD")
    monkeypatch.setenv("ETHOS_ACTOR", _LEASE_HOLDER)
    run_git = core.run_git

    def fail_remove(root: Path, *args: str, **kwargs):
        if args[:2] == ("worktree", "remove"):
            return subprocess.CompletedProcess(args, 128, stdout="", stderr="locked")
        return run_git(root, *args, **kwargs)

    monkeypatch.setattr(core, "run_git", fail_remove)
    report = _retire_landed(repo, branch=_LANDED_BRANCH, expect_head=head, apply=True)
    assert report["required_gaps"] == ["worktree_remove_failed"]


def test_retire_blocks_without_stable_control_root(monkeypatch, tmp_path: Path) -> None:
    repo, landed, _database = _landed_lane(tmp_path, lease_holder=_LEASE_HOLDER)
    head = git(landed, "rev-parse", "HEAD")
    status = workspace_status(repo)
    status["worktrees"] = [
        worktree for worktree in status["worktrees"] if worktree["role"] != "accepted_root"
    ]
    monkeypatch.setenv("ETHOS_ACTOR", _LEASE_HOLDER)
    monkeypatch.setattr(core, "workspace_status", lambda _root: status)
    report = _retire_landed(repo, branch=_LANDED_BRANCH, expect_head=head, apply=True)
    assert report["required_gaps"] == ["retirement_control_root_unavailable"]


@pytest.mark.parametrize(
    ("case", "gap"),
    [
        ("control-root", "retirement_control_root_stale"),
        ("actor", "foreign_work_lane_retire_authority_required"),
        ("missing-path", "retirement_worktree_path_unavailable"),
        ("git-unavailable", "retirement_ref_unavailable"),
        ("dirty", "work_lane_dirty"),
    ],
)
def test_retire_rechecks_effect_boundaries(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    case: str,
    gap: str,
) -> None:
    repo, landed, _database = _landed_lane(tmp_path / case, lease_holder=_LEASE_HOLDER)
    head = git(landed, "rev-parse", "HEAD")
    run_git = core.run_git
    holder_ref = core.current_holder_ref
    calls = 0

    def observe(root: Path, *args: str, **kwargs):
        if case == "control-root" and args == ("symbolic-ref", "--short", "HEAD"):
            return subprocess.CompletedProcess(args, 0, stdout="other\n", stderr="")
        if (
            case == "git-unavailable"
            and root == landed
            and args
            == (
                "rev-parse",
                f"refs/heads/{_LANDED_BRANCH}",
            )
        ):
            return subprocess.CompletedProcess(args, 128, stdout="", stderr="unavailable")
        return run_git(root, *args, **kwargs)

    def actor() -> str:
        nonlocal calls
        calls += 1
        return "agent:test:case:other" if case == "actor" and calls == 3 else holder_ref()

    if case in {"missing-path", "dirty"}:

        def actor_after_effect() -> str:
            nonlocal calls
            calls += 1
            if calls == 3:
                if case == "missing-path":
                    shutil.rmtree(landed)
                else:
                    (landed / "dirty.txt").write_text("dirty\n", encoding="utf-8")
            return holder_ref()

        actor = actor_after_effect
    monkeypatch.setenv("ETHOS_ACTOR", _LEASE_HOLDER)
    monkeypatch.setattr(core, "run_git", observe)
    monkeypatch.setattr(core, "current_holder_ref", actor)
    report = _retire_landed(repo, branch=_LANDED_BRANCH, expect_head=head, apply=True)
    assert report["required_gaps"] == [gap]


@pytest.mark.parametrize(
    ("expect_head", "required_gap"),
    [(None, "expect_head_required"), ("not-the-lane-head", "expect_head_mismatch")],
    ids=("missing", "mismatched"),
)
def test_retire_apply_requires_expected_head(
    monkeypatch, tmp_path: Path, expect_head: str | None, required_gap: str
) -> None:
    repo, landed, _database = _landed_lane(tmp_path, lease_holder=_LEASE_HOLDER)
    monkeypatch.setenv("ETHOS_ACTOR", _LEASE_HOLDER)
    report = _retire_landed(repo, branch=_LANDED_BRANCH, expect_head=expect_head, apply=True)
    assert report["ok"] is False
    assert report["required_gaps"] == [required_gap]
    assert landed.exists()
    assert git(repo, "branch", "--list", _LANDED_BRANCH) != ""


def test_retire_removes_own_clean_merged_lane(monkeypatch, tmp_path: Path) -> None:
    repo, landed, _database = _landed_lane(tmp_path, lease_holder=_LEASE_HOLDER)
    landed_head = git(landed, "rev-parse", "HEAD")
    monkeypatch.setenv("ETHOS_ACTOR", _LEASE_HOLDER)
    report = _retire_landed(landed, branch=_LANDED_BRANCH, expect_head=landed_head, apply=True)
    assert (report["ok"], report["state"]) == (True, "retired")
    assert report["mutation"]["request"]["expect_head"] == landed_head
    assert not landed.exists()
    assert git(repo, "branch", "--list", _LANDED_BRANCH) == ""


def test_retire_blocks_handoff_after_observation(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    repo, landed, database = _landed_lane(tmp_path, lease_holder=_LEASE_HOLDER)
    head = git(landed, "rev-parse", "HEAD")
    observed = state_read.active_leases(database)[0]
    holder_ref = core.current_holder_ref
    calls = 0

    def drift_after_observation() -> str:
        nonlocal calls
        calls += 1
        if calls != 2:
            return holder_ref()
        offer = state.offer_lease_handoff(
            database,
            subject=_LANDED_BRANCH,
            holder_ref=_LEASE_HOLDER,
            expected_lease_id=str(observed["lease_id"]),
            expected_epoch=int(observed["epoch"]),
            target_holder_ref="agent:test:case:agent-b",
            expected_head=head,
            expected_expires_at=str(observed["expires_at"]),
            expected_payload_sha256=str(observed["payload_sha256"]),
        )
        offered = state_read.active_leases(database)[0]
        state.accept_lease_handoff(
            database,
            subject=_LANDED_BRANCH,
            holder_ref=_LEASE_HOLDER,
            target_holder_ref="agent:test:case:agent-b",
            offer_id=str(offer["offer_id"]),
            expected_lease_id=str(observed["lease_id"]),
            expected_epoch=int(observed["epoch"]),
            expected_head=head,
            expected_expires_at=str(offered["expires_at"]),
            expected_payload_sha256=str(offered["payload_sha256"]),
            holder_quiesced=True,
        )
        return holder_ref()

    monkeypatch.setenv("ETHOS_ACTOR", _LEASE_HOLDER)
    monkeypatch.setattr(core, "current_holder_ref", drift_after_observation)
    report = _retire_landed(repo, branch=_LANDED_BRANCH, expect_head=head, apply=True)

    assert report["ok"] is False
    assert report["required_gaps"] == ["lease_holder_mismatch"]
    assert landed.exists()
    assert git(repo, "rev-parse", "--verify", _LANDED_BRANCH) == head


@pytest.mark.parametrize("mutation", ["renew", "offer"])
def test_retire_rejects_lease_payload_drift_after_planning(
    monkeypatch: MonkeyPatch, tmp_path: Path, mutation: str
) -> None:
    repo, landed, database = _landed_lane(tmp_path, lease_holder=_LEASE_HOLDER)
    head = git(landed, "rev-parse", "HEAD")
    lease = state_read.active_leases(database)[0]

    def mutate() -> None:
        if mutation == "renew":
            state.renew_lease(
                database,
                subject=_LANDED_BRANCH,
                holder_ref=_LEASE_HOLDER,
                expected_lease_id=str(lease["lease_id"]),
                expected_epoch=int(lease["epoch"]),
                expected_head=head,
                expected_expires_at=str(lease["expires_at"]),
                expected_payload_sha256=str(lease["payload_sha256"]),
                ttl_seconds=7200,
            )
        else:
            state.offer_lease_handoff(
                database,
                subject=_LANDED_BRANCH,
                holder_ref=_LEASE_HOLDER,
                expected_lease_id=str(lease["lease_id"]),
                expected_epoch=int(lease["epoch"]),
                target_holder_ref="agent:test:case:agent-b",
                expected_head=head,
                expected_expires_at=str(lease["expires_at"]),
                expected_payload_sha256=str(lease["payload_sha256"]),
            )

    apply_retirement = core._apply_retirement  # noqa: SLF001, RUF100 - exact plan/effect race injection

    def mutate_then_apply(*args, **kwargs):
        mutate()
        return apply_retirement(*args, **kwargs)

    monkeypatch.setenv("ETHOS_ACTOR", _LEASE_HOLDER)
    monkeypatch.setattr(core, "_apply_retirement", mutate_then_apply)
    report = _retire_landed(repo, branch=_LANDED_BRANCH, expect_head=head, apply=True)

    assert report["required_gaps"] == ["lease_maintenance_candidate_drift"]
    assert landed.exists()
    assert git(repo, "rev-parse", "--verify", _LANDED_BRANCH) == head
    assert state_read.active_leases(database)[0]["subject"] == _LANDED_BRANCH


def test_retire_preserves_branch_when_accepted_ref_moves_during_effect(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo, landed, _database = _landed_lane(tmp_path, lease_holder=_LEASE_HOLDER)
    head = git(landed, "rev-parse", "HEAD")
    accepted = git(repo, "rev-parse", "dev")
    tree = git(repo, "rev-parse", f"{accepted}^{{tree}}")
    replacement = core.run_git(
        repo, "commit-tree", tree, "-m", "replacement accepted root"
    ).stdout.strip()
    run_git = core.run_git
    moved = False

    def move_accepted(root: Path, *args: str, **kwargs):
        nonlocal moved
        if args[:2] == ("worktree", "remove") and not moved:
            moved = True
            run_git(
                repo,
                "update-ref",
                "refs/heads/dev",
                replacement,
                accepted,
            )
        return run_git(root, *args, **kwargs)

    monkeypatch.setenv("ETHOS_ACTOR", _LEASE_HOLDER)
    monkeypatch.setattr(core, "run_git", move_accepted)
    report = _retire_landed(repo, branch=_LANDED_BRANCH, expect_head=head, apply=True)

    assert report["ok"] is False
    assert report["required_gaps"] == ["accepted_ref_changed_after_worktree_removed"]
    assert report["mutation"]["decision"]["verdict"] == "block"
    assert report["lease_state"] == "retained"
    assert not landed.exists()
    assert git(repo, "rev-parse", "--verify", _LANDED_BRANCH) == head


@pytest.mark.parametrize(
    ("case", "expectation"),
    [
        ("sqlite", (["lease_cleanup_failed"], False, True, {})),
        (
            "ref-transaction",
            (
                ["branch_delete_failed_after_worktree_removed"],
                True,
                True,
                {"ref_preserved": True},
            ),
        ),
        (
            "ref-diagnostic-oserror",
            (
                ["branch_delete_failed_after_worktree_removed"],
                True,
                True,
                {"ref_preserved": True},
            ),
        ),
        (
            "commit",
            (
                ["lease_cleanup_failed_after_lane_removed"],
                True,
                True,
                {"ref_restored": True},
            ),
        ),
        (
            "restore",
            (
                [
                    "lease_cleanup_failed_after_lane_removed",
                    "branch_restore_failed_after_lease_cleanup",
                ],
                True,
                False,
                {"ref_restored": False},
            ),
        ),
        (
            "restore-oserror",
            (
                [
                    "lease_cleanup_failed_after_lane_removed",
                    "branch_restore_failed_after_lease_cleanup",
                ],
                True,
                False,
                {"ref_restored": False},
            ),
        ),
    ],
)
def test_retire_reports_transaction_failures(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    case: str,
    expectation: tuple[list[str], bool, bool, dict[str, bool]],
) -> None:
    gaps, removed, ref_present, effect_state = expectation
    repo, landed, database = _landed_lane(tmp_path, lease_holder=_LEASE_HOLDER)
    head = git(landed, "rev-parse", "HEAD")

    class CommitFailure(sqlite3.Connection):
        def commit(self) -> None:
            raise sqlite3.OperationalError

    if case == "sqlite":

        def connect_failure(_path: Path) -> sqlite3.Connection:
            message = "database unavailable"
            raise sqlite3.OperationalError(message)

        connect = connect_failure
    else:
        connect = (
            partial(sqlite3.connect, factory=CommitFailure)
            if case not in {"ref-transaction", "sqlite"}
            else sqlite3.connect
        )
    monkeypatch.setattr(core, "sqlite3", SimpleNamespace(connect=connect, Error=sqlite3.Error))
    run_git = core.run_git
    ref_transaction_failed = False

    def fail_git(root: Path, *args: str, **kwargs):
        nonlocal ref_transaction_failed
        if case == "ref-transaction" and args[:2] == ("update-ref", "--stdin"):
            message = "git unavailable"
            raise OSError(message)
        if case == "ref-diagnostic-oserror" and args[:2] == ("update-ref", "--stdin"):
            ref_transaction_failed = True
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="transaction failed")
        if ref_transaction_failed and args == ("rev-parse", "dev"):
            message = "git unavailable"
            raise OSError(message)
        if (
            case in {"restore", "restore-oserror"}
            and args[:1] == ("update-ref",)
            and args[:2]
            != (
                "update-ref",
                "--stdin",
            )
        ):
            if case == "restore-oserror":
                message = "git unavailable"
                raise OSError(message)
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="ref occupied")
        return run_git(root, *args, **kwargs)

    monkeypatch.setattr(core, "run_git", fail_git)
    monkeypatch.setenv("ETHOS_ACTOR", _LEASE_HOLDER)
    report = _retire_landed(repo, branch=_LANDED_BRANCH, expect_head=head, apply=True)

    assert report["required_gaps"] == gaps
    assert report["mutation"]["decision"]["verdict"] == "block"
    assert report.get("worktree_removed", False) is removed
    assert {key: report[key] for key in effect_state} == effect_state
    assert report.get("lease_state", "") == ("retained" if removed else "")
    assert landed.exists() is not removed
    assert (git(repo, "branch", "--list", _LANDED_BRANCH) != "") is ref_present
    assert state_read.active_leases(database)[0]["subject"] == _LANDED_BRANCH


def test_status_reports_candidate_behind_accepted(tmp_path: Path) -> None:
    """Candidate-train integrity: status surfaces how far candidate/dev is behind the
    accepted root (dev), so promotions that bypassed the lane->candidate->accepted
    train (e.g. a raw merge straight to accepted) are visible, not silent drift."""
    repo = init_repo(tmp_path / "repo")
    git(repo, "branch", "candidate/dev")
    for name in ("b.txt", "c.txt"):
        commit_fixture_file(repo, name, "x\n", f"add {name}")
    status = workspace_status(repo)
    assert status["candidate"]["behind_accepted"] == 2


def test_status_reports_dirty_provenance(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    git(repo, "worktree", "add", "-b", "work/feature", worktree.as_posix(), "dev")
    (worktree / "README.md").write_text("# edited\n", encoding="utf-8")
    (worktree / "new.txt").write_text("new\n", encoding="utf-8")
    status = workspace_status(worktree)
    provenance = status["dirty_provenance"]
    assert provenance["dirty"] is True
    assert provenance["summary"]["tracked"] == 1
    assert provenance["summary"]["untracked"] == 1
    entries = {entry["path"]: entry for entry in provenance["entries"]}
    assert entries["README.md"]["kind"] == "tracked"
    assert entries["new.txt"]["kind"] == "untracked"


def test_dirty_provenance_classifies_temp_probes(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    probe_dir = repo / "tests" / "unit" / "kernel"
    probe_dir.mkdir(parents=True)
    for index in range(17):
        (probe_dir / f"test_probe_{index:02d}.py").write_text("# TEMP PROBE\n", encoding="utf-8")
    provenance = dirty_provenance(repo)
    assert provenance["temporary_probes"] == {
        "count": 17,
        "paths": [f"tests/unit/kernel/test_probe_{index:02d}.py" for index in range(16)],
        "truncated": True,
    }


def test_dirty_provenance_ignores_ordinary_untracked(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    probe_dir = repo / "tests" / "unit"
    probe_dir.mkdir(parents=True)
    (probe_dir / "test_without_marker.py").write_text("def test_ok(): pass\n", encoding="utf-8")
    (probe_dir / "probe.py").write_text("# TEMP PROBE\n", encoding="utf-8")
    tracked = probe_dir / "test_tracked.py"
    tracked.write_text("# TEMP PROBE\n", encoding="utf-8")
    git(repo, "add", tracked.relative_to(repo).as_posix())
    provenance = dirty_provenance(repo)
    assert provenance["temporary_probes"] == _NO_TEMPORARY_PROBES


def test_temp_probe_ignores_unreadable_file(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    probe = repo / "tests" / "unit" / "test_missing_probe.py"
    probe.parent.mkdir(parents=True)
    probe.symlink_to("missing-probe-target.py")
    provenance = dirty_provenance(repo)
    assert provenance["temporary_probes"] == _NO_TEMPORARY_PROBES


def test_status_recommends_lane_migration(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    first = tmp_path / "repo-work-first"
    second = tmp_path / "repo-work-second"
    start = partial(start_work_lane, root=repo, apply=True)
    start(name="first", path=first, holder_ref="agent:test:case:agent-first")
    start(name="second", path=second, holder_ref="agent:test:case:agent-second")
    commit_fixture_file(first, "README.md", "# first\n", "first")
    commit_fixture_file(second, "README.md", "# second\n", "second")
    status = workspace_status(second)
    recommendations = status["coordination"]["migration_recommendations"]
    assert recommendations == [
        {
            "kind": "overlap_resolution",
            "overlapping_branch": "work/first",
            "holder_ref": "agent:test:case:agent-first",
            "recommendation": "preserve_legitimate_lane_and_replay_or_move_verified_head",
            "next_actions": [
                "do not land a temporary overlapping lane directly",
                "refresh or move the leased lane work/first after review",
                "delete the temporary lane after the legitimate lane carries the verified head",
            ],
        }
    ]


def test_committed_paths_empty_when_diff_fails(tmp_path: Path) -> None:
    assert committed_change_paths(init_repo(tmp_path / "repo"), "missing-candidate-ref") == ()


def test_dirty_provenance_reports_git_unavailable(monkeypatch, tmp_path: Path) -> None:

    def fail_git(_root: Path, *args: str) -> str:
        assert args == ("status", "--porcelain", "--untracked-files=all")
        raise subprocess.CalledProcessError(128, ["git", *args], stderr="fatal: not a git repo")

    monkeypatch.setattr(repo_dirty, "git_stdout_checked", fail_git)
    report = dirty_provenance(tmp_path)
    _assert_unavailable(report, "fatal: not a git repo")


def test_dirty_provenance_coarsens_untracked(monkeypatch, tmp_path: Path) -> None:

    def summarized_git(_root: Path, *args: str) -> str:
        assert args == ("status", "--porcelain", "--untracked-files=normal")
        return "?? build/\n"

    monkeypatch.setattr(repo_dirty, "git_stdout_checked", summarized_git)
    report = dirty_provenance(tmp_path, untracked_files="normal")
    assert report["entries"] == [
        {"path": "build/", "index": "?", "worktree": "?", "kind": "untracked"}
    ]
    assert report["summary"]["untracked"] == 1


def test_dirty_provenance_reports_missing_cwd(tmp_path: Path) -> None:
    _assert_unavailable(dirty_provenance(tmp_path / "missing-worktree"), "missing-worktree")


def test_changed_paths_fails_closed_for_missing_path(
    tmp_path: Path,
) -> None:
    assert has_changed_paths(tmp_path / "missing-candidate") is True


def test_worktree_binding_reports_absent(tmp_path: Path) -> None:
    assert worktree_binding("", current_path=tmp_path.resolve()) == "absent"


def test_coordination_reports_unknown_scope() -> None:
    assert (
        repo_coordination.coordination_state(
            current_role="work_lane",
            current_path_scope=("packages/ethos/src",),
            current_scope_state="bounded",
            foreign_path_scope=(),
            foreign_scope_state="unknown",
        )
        == "unknown"
    )
    required, advisory = repo_coordination.coordination_gaps(
        _UNKNOWN_FOREIGN_LANES,
        current_role="work_lane",
        current_scope_state="unknown",
    )
    assert required == ["coordination_gap:current_scope_unknown"]
    assert advisory == [
        "foreign_work_lane_present",
        "coordination_gap:foreign_scope_unknown:work/unknown",
    ]


def test_foreign_unknown_scope_is_advisory() -> None:
    required, advisory = repo_coordination.coordination_gaps(
        _UNKNOWN_FOREIGN_LANES,
        current_role="work_lane",
        current_scope_state="bounded",
    )
    assert required == []
    assert "coordination_gap:foreign_scope_unknown:work/unknown" in advisory


def test_retire_selected_ignores_missing_foreign(monkeypatch, tmp_path: Path) -> None:
    repo, owned, _database = _landed_lane(tmp_path, lease_holder="agent:test:case:owner")
    owned_head = git(owned, "rev-parse", "HEAD")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:owner")
    missing_foreign = tmp_path / "repo-work-missing-foreign"
    git(repo, "worktree", "add", "-b", "work/foreign", missing_foreign.as_posix(), "dev")
    shutil.rmtree(missing_foreign)
    report = _retire_landed(repo, branch=_LANDED_BRANCH, expect_head=owned_head, apply=True)
    assert report["ok"] is True
    assert report["state"] == "retired"
    assert not owned.exists()
    assert git(repo, "branch", "--list", _LANDED_BRANCH) == ""
    assert git(repo, "branch", "--list", "work/foreign") != ""


def test_retire_selected_missing_worktree_blocks(monkeypatch, tmp_path: Path) -> None:
    repo, missing, _database = _landed_lane(tmp_path, lease_holder="agent:test:case:owner")
    missing_head = git(missing, "rev-parse", "HEAD")
    shutil.rmtree(missing)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:owner")
    report = _retire_landed(repo, branch=_LANDED_BRANCH, expect_head=missing_head, apply=True)
    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["required_gaps"] == ["work_lane_dirty"]
    assert git(repo, "branch", "--list", _LANDED_BRANCH) != ""
