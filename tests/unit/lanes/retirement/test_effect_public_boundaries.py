from __future__ import annotations

import json
import sqlite3
import subprocess
from contextlib import closing
from pathlib import Path

import pytest

import ethos.adapters.mutation.lane_retirement.effects as effects
from ethos.adapters.mutation.lane_retirement.linked import LinkedRetirementRequest
from ethos.adapters.mutation.lane_retirement.linked import retire_linked_work_lane
from ethos.adapters.repo.hook.activation import install_hook_launchers
from ethos.adapters.repo.hook.binding import hook_runtime_binding
from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.adapters.store.state.lease.projection import observe_lease
from ethos.contracts.branch.roles import BranchRolePolicy
from tests.support.governed_repository import exact_lease
from tests.support.governed_repository import git
from tests.support.lane_scenarios import superseded_work_lane
from tests.support.lifecycle_cases import assert_public_decision

BRANCH = "work/superseded"


def _retirement_request(
    head: str, absorbed_by: str, *, apply: bool = False
) -> LinkedRetirementRequest:
    return LinkedRetirementRequest(
        branch=BRANCH,
        expect_head=head,
        absorbed_by=absorbed_by,
        reason="accepted tree contains the obsolete delta",
        authorize=True,
        apply=apply,
    )


def _assert_retired(repo: Path, source: Path, database: Path) -> None:
    assert (
        source.exists(),
        git(repo, "branch", "--list", BRANCH),
        observe_lease(database, BRANCH).state,
    ) == (False, "", "missing")


def _lane(
    *,
    branch: str = "work/source",
    path: str = "/lane",
    head: str = "a" * 40,
    holder: str = "agent:test:holder",
) -> dict[str, object]:
    return {
        "branch": branch,
        "path": path,
        "head": head,
        "lease_state": "valid",
        "lease": {
            "lease_id": "lease:test",
            "epoch": 1,
            "holder_ref": holder,
            "expires_at": "2026-08-11T00:00:00+00:00",
            "payload_sha256": "b" * 64,
        },
    }


@pytest.mark.parametrize(
    ("error", "terminal", "expected"),
    [
        (OSError("uncertain"), True, {"observed": {"terminal": True}}),
        (
            sqlite3.OperationalError("uncertain"),
            False,
            {
                "verdict": "block",
                "state": "blocked",
                "required_gaps": ["lease_cleanup_failed"],
                "stderr": "uncertain",
                "observed": {"terminal": False},
            },
        ),
        (None, True, {"observed": {"terminal": True}}),
        (
            None,
            False,
            {
                "verdict": "block",
                "state": "blocked",
                "required_gaps": ["retirement_postcondition_not_terminal"],
                "observed": {"terminal": False},
            },
        ),
    ],
)
def test_retirement_result_distinguishes_uncertain_success_from_failure(
    monkeypatch: pytest.MonkeyPatch,
    error: OSError | sqlite3.Error | None,
    terminal: int,
    expected: dict[str, object],
) -> None:
    observed = {"terminal": bool(terminal)}
    monkeypatch.setattr(effects, "retirement_observation", lambda *_args: observed)
    monkeypatch.setattr(effects, "retirement_terminal", lambda _observed: bool(terminal))

    assert (
        effects.retirement_result(Path("/repo"), Path("/control"), _lane(), result={}, error=error)
        == expected
    )


@pytest.mark.parametrize(
    ("accepted_state", "authority_state", "source_state", "restored", "gaps"),
    [
        (
            "expected",
            "moved",
            "moved",
            False,
            {
                "authority_ref_changed_after_worktree_removed",
                "retirement_ref_moved_after_worktree_removed",
            },
        ),
        (
            "expected",
            "unavailable",
            "absent",
            False,
            {
                "authority_ref_state_unavailable_after_worktree_removed",
                "retirement_ref_absent_after_failed_delete",
            },
        ),
        (
            "expected",
            "expected",
            "expected",
            False,
            {"worktree_restore_failed_after_ref_transition"},
        ),
    ],
)
def test_failed_ref_transition_reports_each_preservation_failure(
    monkeypatch: pytest.MonkeyPatch,
    accepted_state: str,
    authority_state: str,
    source_state: str,
    restored: int,
    gaps: set[str],
) -> None:
    def outcome(_root: Path, branch: str, _head: str) -> str:
        return {
            "dev": accepted_state,
            "work/authority": authority_state,
            "work/source": source_state,
        }[branch]

    monkeypatch.setattr(effects, "ref_outcome", outcome)
    monkeypatch.setattr(
        effects,
        "restore_worktree",
        lambda *_args: {"state": "recognized" if restored else "blocked"},
    )

    report = effects.failed_ref_transition(
        Path("/control"),
        lane=_lane(),
        target=("work/source", "a" * 40),
        accepted=("dev", "b" * 40),
        authority=("work/authority", "c" * 40),
        stderr="effect rejected",
    )

    assert gaps <= set(report["required_gaps"])
    assert report["ref_state"] == source_state
    assert report["ref_preserved"] is (source_state == "expected")


@pytest.mark.parametrize(
    ("merge_base", "changed", "returncode", "expected"),
    [
        (None, None, 0, False),
        ("base", None, 0, False),
        ("base", "", 1, True),
        ("base", "a\0", 1, False),
    ],
)
def test_absorbed_handles_unavailable_and_semantic_delta_results(
    monkeypatch: pytest.MonkeyPatch,
    merge_base: str | None,
    changed: str | None,
    returncode: int,
    expected: int,
) -> None:
    def output(_repo: Path, *args: str) -> str | None:
        return merge_base if args[0] == "merge-base" else changed

    monkeypatch.setattr(effects, "output", output)
    monkeypatch.setattr(
        effects,
        "run_git",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], returncode, "", ""),
    )

    assert effects.absorbed(Path("/repo"), "head", "accepted") is bool(expected)


@pytest.mark.parametrize(
    ("carrier", "ancestor", "paths", "archives", "blobs", "expected"),
    [
        ("README.md", True, (), (), {}, {}),
        ("openspec/changes/x/commitment.toml", False, (), (), {}, {}),
        ("openspec/changes/x/commitment.toml", True, ("src/x.py",), ("archive/x",), {}, {}),
        (
            "openspec/changes/x/commitment.toml",
            True,
            ("openspec/changes/x/commitment.toml",),
            (),
            {},
            {},
        ),
        (
            "openspec/changes/x/commitment.toml",
            True,
            ("openspec/changes/x/commitment.toml",),
            ("openspec/changes/archive/2026-08-10-x",),
            {"source": "blob-a", "target": "blob-b"},
            {},
        ),
    ],
)
def test_archive_absorption_rejects_ambiguous_or_nonidentical_carriers(
    monkeypatch: pytest.MonkeyPatch,
    carrier: str,
    ancestor: int,
    paths: tuple[str, ...],
    archives: tuple[str, ...],
    blobs: dict[str, str],
    expected: dict[str, object],
) -> None:
    monkeypatch.setattr(effects, "is_ancestor", lambda *_args: ancestor)
    monkeypatch.setattr(effects, "_carrier_delta_paths", lambda *_args: paths)
    monkeypatch.setattr(effects, "_archive_roots", lambda *_args: archives)

    def output(_repo: Path, _command: str, subject: str) -> str:
        return blobs.get("source" if subject.startswith("head:") else "target", "")

    monkeypatch.setattr(effects, "output", output)

    assert (
        effects.archived_carrier_absorption(
            Path("/repo"), head="head", accepted_head="accepted", carrier=carrier
        )
        == expected
    )


def test_effect_gaps_recheck_successor_checkout_and_archive_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lane = _lane()
    lane["archive_absorption"] = {"change": "x"}
    authority = _lane(branch="work/authority", path="/authority", head="c" * 40)
    policy = BranchRolePolicy()
    monkeypatch.setattr(
        effects,
        "output",
        lambda _root, *args: policy.accepted_branch if args[0] == "symbolic-ref" else "b" * 40,
    )
    monkeypatch.setattr(Path, "resolve", lambda self: self)
    monkeypatch.setattr(effects, "actor_ref", lambda: "agent:test:holder")

    gaps = effects.effect_gaps(
        Path("/wrong"),
        Path("/control"),
        policy=policy,
        lane=lane,
        authority_lane=authority,
        accepted_head="b" * 40,
    )
    assert gaps == ["retirement_authority_checkout_stale"]

    monkeypatch.setattr(
        effects,
        "output",
        lambda root, *args: (
            policy.accepted_branch
            if root == Path("/control") and args[0] == "symbolic-ref"
            else "work/authority"
            if args[0] == "symbolic-ref"
            else "b" * 40
        ),
    )
    monkeypatch.setattr(effects, "reobservation_gaps", lambda *_args: [])
    monkeypatch.setattr(effects, "archived_carrier_absorption", lambda *_args, **_kwargs: {})
    gaps = effects.effect_gaps(
        Path("/authority"),
        Path("/control"),
        policy=policy,
        lane=lane,
        authority_lane=authority,
        accepted_head="b" * 40,
    )
    assert gaps == ["retirement_archive_absorption_stale"]


@pytest.mark.parametrize(
    ("path", "branch", "add_error", "expected"),
    [
        (
            "",
            "work/source",
            False,
            {"state": "blocked", "error": "worktree_restore_coordinates_missing"},
        ),
        (
            "/lane",
            "",
            False,
            {"state": "blocked", "error": "worktree_restore_coordinates_missing"},
        ),
        ("/lane", "work/source", True, {"state": "blocked", "error": "restore rejected"}),
        ("/lane", "work/source", False, {"state": "recognized"}),
    ],
)
def test_restore_worktree_reports_exact_compensation_outcome(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    branch: str,
    add_error: int,
    expected: dict[str, str],
) -> None:
    def add(*_args: object, **_kwargs: object) -> None:
        if add_error:
            message = "restore rejected"
            raise ValueError(message)

    monkeypatch.setattr(effects, "add_worktree", add)

    assert effects.restore_worktree(Path("/control"), _lane(path=path, branch=branch)) == expected


@pytest.mark.parametrize(
    ("returncode", "value", "gap"),
    [(1, "", "retirement_ref_unavailable"), (0, "other", "retirement_ref_stale")],
)
def test_reobservation_reports_unavailable_and_stale_native_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    returncode: int,
    value: str,
    gap: str,
) -> None:
    lane = tmp_path / "lane"
    lane.mkdir()
    monkeypatch.setattr(
        effects,
        "run_git",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], returncode, value, ""),
    )

    assert gap in effects.reobservation_gaps("work/source", lane.as_posix(), "a" * 40)


def test_archive_equivalent_superseded_retirement_passes_through_installed_hooks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    holder = "agent:test:case:archive-hook"
    repo, lane, _source_head, _, database = superseded_work_lane(
        tmp_path, holder_ref=holder, absorbed=False
    )
    active = lane / "openspec/changes/fixture-change"
    archive = repo / "openspec/changes/archive/2026-08-08-fixture-change"
    archive.mkdir(parents=True)
    for name in ("proposal.md", "commitment.toml"):
        (archive / name).write_bytes((active / name).read_bytes())
    git(repo, "add", archive.relative_to(repo).as_posix())
    git(repo, "commit", "-m", "archive fixture carrier")
    git(repo, "rm", "-r", "openspec/changes/fixture-change")
    git(repo, "commit", "-m", "retire active carrier")
    accepted = git(repo, "rev-parse", "HEAD")
    git(lane, "reset", "--hard", accepted)
    active.mkdir(parents=True)
    for name in ("proposal.md", "commitment.toml"):
        (active / name).write_bytes((archive / name).read_bytes())
    git(lane, "add", active.relative_to(lane).as_posix())
    git(lane, "commit", "-m", "reconstruct active carrier")
    source_head = git(lane, "rev-parse", "HEAD")
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("delete from leases where subject = ?", (BRANCH,))
    acquire_lease(
        database,
        lease=exact_lease(
            repo=lane,
            branch=BRANCH,
            holder_ref=holder,
            expected_head=source_head,
            carrier="openspec/changes/fixture-change/commitment.toml",
            change_id="fixture-change",
        ),
    )
    install_hook_launchers(repo)
    exclude = Path(git(repo, "rev-parse", "--path-format=absolute", "--git-path", "info/exclude"))
    exclude.parent.mkdir(parents=True, exist_ok=True)
    exclude.write_text("tools/\n", encoding="utf-8")
    monkeypatch.setenv("ETHOS_ACTOR", holder)

    request = _retirement_request(source_head, accepted)
    planned = retire_linked_work_lane(root=repo, mode="superseded", request=request)
    assert_public_decision(planned, verdict="pass", state="ready_to_retire_superseded", gaps=[])

    applied = retire_linked_work_lane(
        root=repo, mode="superseded", request=request.model_copy(update={"apply": True})
    )

    assert_public_decision(applied, verdict="pass", state="retired_superseded", gaps=[])
    _assert_retired(repo, lane, database)


def test_superseded_retirement_recovers_exact_unbound_lease_then_retires(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    holder = "agent:test:case:partial-recovery"
    repo, lane, head, accepted, database = superseded_work_lane(tmp_path, holder_ref=holder)
    install_hook_launchers(repo)
    git(repo, "worktree", "remove", lane.as_posix())
    monkeypatch.setenv("ETHOS_ACTOR", holder)
    request = _retirement_request(head, accepted).model_copy(update={"path": lane.as_posix()})

    planned = retire_linked_work_lane(root=repo, mode="superseded", request=request)

    assert_public_decision(
        planned,
        verdict="pass",
        state="ready_to_recover_and_retire_superseded",
        gaps=[],
    )
    assert planned["lane"]["recovery_required"] is True
    assert not lane.exists()

    applied = retire_linked_work_lane(
        root=repo,
        mode="superseded",
        request=request.model_copy(update={"apply": True}),
    )

    assert_public_decision(applied, verdict="pass", state="retired_superseded", gaps=[])
    assert applied["recovery"]["state"] == "recovered_for_retirement"
    assert not applied["recovery"]["hook_runtime"]["required_gaps"]
    _assert_retired(repo, lane, database)


def test_superseded_retirement_keeps_recovered_worktree_when_ref_effect_blocks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    holder = "agent:test:case:partial-recovery"
    repo, lane, head, accepted, database = superseded_work_lane(tmp_path, holder_ref=holder)
    install_hook_launchers(repo)
    git(repo, "worktree", "remove", lane.as_posix())
    monkeypatch.setenv("ETHOS_ACTOR", holder)
    monkeypatch.setattr(
        effects,
        "remove_linked_lane",
        lambda *_args, **_kwargs: effects.blocked(["git_effect_cas_rejected"]),
    )
    request = _retirement_request(head, accepted, apply=True).model_copy(
        update={"path": lane.as_posix()}
    )

    report = retire_linked_work_lane(root=repo, mode="superseded", request=request)

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["git_effect_cas_rejected"]
    assert (lane.exists(), git(lane, "rev-parse", "HEAD")) == (True, head)
    assert not hook_runtime_binding(lane)["required_gaps"]
    assert git(repo, "rev-parse", BRANCH) == head
    assert observe_lease(database, BRANCH).state == "valid"


@pytest.mark.parametrize(
    ("scenario", "gap"),
    [
        ("path-collision", "retirement_recovery_path_collision"),
        ("foreign-holder", "foreign_work_lane_retire_authority_required"),
        ("lease-tree-mismatch", "lease_expected_tree_mismatch"),
    ],
)
def test_superseded_retirement_partial_recovery_rejects_stale_exact_bindings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    scenario: str,
    gap: str,
) -> None:
    holder = "agent:test:case:partial-recovery"
    repo, lane, head, accepted, database = superseded_work_lane(
        tmp_path / scenario, holder_ref=holder
    )
    git(repo, "worktree", "remove", lane.as_posix())
    monkeypatch.setenv(
        "ETHOS_ACTOR",
        "agent:test:case:foreign" if scenario == "foreign-holder" else holder,
    )
    if scenario == "path-collision":
        lane.mkdir()
    elif scenario == "lease-tree-mismatch":
        with closing(sqlite3.connect(database)) as connection, connection:
            row = connection.execute(
                "select payload_json from leases where subject = ?", (BRANCH,)
            ).fetchone()
            payload = json.loads(str(row[0]))
            payload["expected_tree"] = "0" * 40
            connection.execute(
                "update leases set payload_json = ? where subject = ?",
                (json.dumps(payload, sort_keys=True, separators=(",", ":")), BRANCH),
            )
    request = _retirement_request(head, accepted).model_copy(update={"path": lane.as_posix()})

    report = retire_linked_work_lane(root=repo, mode="superseded", request=request)

    assert report["verdict"] == "block"
    assert gap in report["required_gaps"]
    assert git(repo, "rev-parse", BRANCH) == head
    assert observe_lease(database, BRANCH).state == "valid"
