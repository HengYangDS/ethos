from __future__ import annotations

import hashlib
import pathlib
import subprocess
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.lane_retirement.operation as operation
from ethos.contracts.retirement import RetirementObservation
from ethos.contracts.retirement import RetirementOperation
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_test_profile

if TYPE_CHECKING:
    from pathlib import Path


def _request(tmp_path: Path) -> RetirementOperation:
    return RetirementOperation(
        repository_common_dir=(tmp_path / ".git").as_posix(),
        control_root=tmp_path.as_posix(),
        mode="abandon",
        branch="work/source",
        head="a" * 40,
        tree="b" * 40,
        accepted_branch="dev",
        accepted_head="c" * 40,
        worktree_path=(tmp_path / "lane").as_posix(),
        worktree_initial="linked",
        lease_state="valid",
        lease={
            "holder_ref": "agent:test:case:holder",
            "generation": 1,
            "expires_at": "2026-09-03T00:00:00+00:00",
        },
        authority={"kind": "owner", "actor": "agent:test:case:holder"},
        reason={"code": "duplicate-empty-lane", "summary": "duplicate empty lane"},
        git_plan={"digest": "d" * 64},
    )


@pytest.mark.parametrize(
    ("states", "completed", "remaining", "state"),
    [
        (
            ("expected", "expected", "expected"),
            (),
            ("remove_worktree", "delete_ref", "revoke_lease"),
            "ready",
        ),
        (
            ("absent", "expected", "expected"),
            ("remove_worktree",),
            ("delete_ref", "revoke_lease"),
            "partial_transition",
        ),
        (
            ("absent", "absent", "expected"),
            ("remove_worktree", "delete_ref"),
            ("revoke_lease",),
            "partial_transition",
        ),
        (
            ("absent", "absent", "absent"),
            ("remove_worktree", "delete_ref", "revoke_lease"),
            (),
            "terminal",
        ),
    ],
)
def test_retirement_progress_is_a_pure_reduction(tmp_path, states, completed, remaining, state):
    observed = RetirementObservation(
        **dict(zip(("worktree_state", "ref_state", "lease_state"), states, strict=True))
    )
    progress = operation.reduce_progress(_request(tmp_path), observed)
    assert progress.completed_effects == completed
    assert progress.remaining_effects == remaining
    assert progress.state == state


@pytest.mark.parametrize(
    ("updates", "observed"),
    [
        ({}, {"worktree_state": "absent", "ref_state": "moved"}),
        ({}, {"ref_state": "absent"}),
        ({}, {"lease_state": "absent"}),
        ({}, {"accepted_state": "moved"}),
        ({}, {"worktree_state": "unavailable"}),
        ({"worktree_initial": "unbound", "worktree_path": ""}, {}),
        ({"lease_state": "missing", "lease": {}}, {}),
    ],
)
def test_retirement_progress_rejects_non_monotonic_or_ambiguous_carriers(
    tmp_path, updates, observed
):
    request = _request(tmp_path).model_copy(update=updates)
    observation = RetirementObservation(
        **{
            "worktree_state": "expected",
            "ref_state": "expected",
            "lease_state": "expected",
            **observed,
        }
    )
    with pytest.raises(ValueError, match="retirement_operation_state_drift"):
        operation.reduce_progress(request, observation)


def test_unbound_request_detects_branch_rebound_at_another_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = _request(tmp_path).model_copy(
        update={
            "worktree_initial": "unbound",
            "worktree_path": "",
            "lease_state": "missing",
            "lease": {},
        }
    )
    monkeypatch.setattr(operation, "state_database", lambda _root: tmp_path / "state.sqlite")
    monkeypatch.setattr(
        operation,
        "observe_lease",
        lambda *_args: type("Lease", (), {"state": "missing"})(),
    )

    def observe_git(_root: Path, *args: str, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if args[:3] == ("worktree", "list", "--porcelain"):
            return subprocess.CompletedProcess(
                [],
                0,
                "\n".join(
                    (
                        f"worktree {tmp_path / 'other'}",
                        f"HEAD {request.head}",
                        f"branch refs/heads/{request.branch}",
                        "",
                    )
                ),
                "",
            )
        expected = (
            request.accepted_head if args[-1].endswith(request.accepted_branch) else request.head
        )
        return subprocess.CompletedProcess([], 0, expected, "")

    monkeypatch.setattr(
        operation,
        "run_git",
        observe_git,
    )

    assert operation.observe_operation(tmp_path, request).worktree_state == "moved"


def test_effect_failure_after_worktree_removal_returns_resumable_progress(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = _request(tmp_path)
    monkeypatch.setattr(operation, "local_state_root", lambda _root: tmp_path / "state")
    states = iter(
        (
            RetirementObservation(
                worktree_state="expected", ref_state="expected", lease_state="expected"
            ),
            RetirementObservation(
                worktree_state="absent", ref_state="expected", lease_state="expected"
            ),
            RetirementObservation(
                worktree_state="absent", ref_state="expected", lease_state="expected"
            ),
        )
    )
    monkeypatch.setattr(operation, "observe_operation", lambda *_args: next(states))
    monkeypatch.setattr(operation, "preflight_operation", lambda *_args: None)
    monkeypatch.setattr(operation, "remove_operation_worktree", lambda *_args: None)
    monkeypatch.setattr(
        operation,
        "delete_operation_ref",
        lambda *_args: (_ for _ in ()).throw(ValueError("git_process_spawn_failed")),
    )
    written: list[tuple[str, ...]] = []
    monkeypatch.setattr(
        operation,
        "persist_progress",
        lambda _root, _request, progress: written.append(progress.completed_effects) or {},
    )

    report = operation.apply_operation(tmp_path, request, request_receipt={"path": "/receipt"})

    assert report["state"] == "partial_transition"
    assert report["completed_effects"] == ["remove_worktree"]
    assert report["remaining_effects"] == ["delete_ref", "revoke_lease"]
    assert report["required_gaps"] == ["git_process_spawn_failed"]
    assert "ethos lane retire recover" in report["next_action"]
    assert written == [(), ("remove_worktree",), ("remove_worktree",)]


@pytest.mark.parametrize("failure", [False, True])
def test_preflight_failure_and_dry_run_never_start_destructive_effects(
    tmp_path, monkeypatch, failure
):
    request = _request(tmp_path)
    monkeypatch.setattr(operation, "local_state_root", lambda _root: tmp_path / "state")
    monkeypatch.setattr(
        operation,
        "observe_operation",
        lambda *_a: RetirementObservation(
            worktree_state="expected", ref_state="expected", lease_state="expected"
        ),
    )

    def preflight(*_args):
        if failure:
            message = "git_process_spawn_failed"
            raise ValueError(message)

    monkeypatch.setattr(operation, "preflight_operation", preflight)
    monkeypatch.setattr(
        operation,
        "remove_operation_worktree",
        lambda *_a: pytest.fail("preflight or dry-run mutated carriers"),
    )
    if not failure:
        monkeypatch.setattr(
            operation, "persist_progress", lambda *_a: pytest.fail("dry-run persisted progress")
        )
    report = operation.apply_operation(
        tmp_path, request, request_receipt={"path": "/receipt"}, apply=failure
    )
    assert report["state"] == ("blocked" if failure else "ready")
    assert report["completed_effects"] == []
    assert report["remaining_effects"] == ["remove_worktree", "delete_ref", "revoke_lease"]
    assert report["required_gaps"] == (["git_process_spawn_failed"] if failure else [])


def test_recovery_applies_only_remaining_effects_and_is_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = _request(tmp_path)
    monkeypatch.setattr(operation, "local_state_root", lambda _root: tmp_path / "state")
    state = {"worktree": "absent", "ref": "expected", "lease": "expected"}
    calls: list[str] = []

    def observe(*_args: object) -> RetirementObservation:
        return RetirementObservation(
            worktree_state=state["worktree"],
            ref_state=state["ref"],
            lease_state=state["lease"],
        )

    def delete_ref(*_args: object) -> None:
        calls.append("delete_ref")
        state["ref"] = "absent"

    def revoke(*_args: object) -> None:
        calls.append("revoke_lease")
        state["lease"] = "absent"

    monkeypatch.setattr(operation, "observe_operation", observe)
    monkeypatch.setattr(operation, "preflight_operation", lambda *_args: None)
    monkeypatch.setattr(operation, "delete_operation_ref", delete_ref)
    monkeypatch.setattr(operation, "revoke_operation_lease", revoke)
    monkeypatch.setattr(operation, "persist_progress", lambda *_args: {})
    monkeypatch.setattr(operation, "persist_terminal_receipt", lambda *_args: {})

    first = operation.apply_operation(tmp_path, request, request_receipt={"path": "/receipt"})
    second = operation.apply_operation(tmp_path, request, request_receipt={"path": "/receipt"})

    assert first["state"] == "retired"
    assert second["state"] == "retired"
    assert first["completed_effects"] == ["remove_worktree", "delete_ref", "revoke_lease"]
    assert calls == ["delete_ref", "revoke_lease"]


@pytest.mark.parametrize(
    ("authorized", "actor", "gap"),
    [
        (False, "agent:test:case:holder", "authorization_required"),
        (True, "agent:test:case:foreign", "foreign_work_lane_retire_authority_required"),
        (True, "", "foreign_work_lane_retire_authority_required"),
    ],
)
def test_recovery_requires_current_owner_and_explicit_authorization(
    tmp_path, monkeypatch, authorized, actor, gap
):
    request = _request(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", actor)
    monkeypatch.setattr(operation, "load_operation", lambda *_args: request)
    monkeypatch.setattr(
        operation,
        "apply_operation",
        lambda *_a, **_k: pytest.fail("unauthorized recovery executed"),
    )
    report = operation.recover_retirement_operation(
        root=tmp_path,
        receipt_path="/receipt",
        receipt_sha256="sha256:" + "d" * 64,
        apply=True,
        authorized=authorized,
    )
    assert report["state"] == "blocked"
    assert report["required_gaps"] == [gap]


@pytest.mark.parametrize(
    ("damage", "gap"),
    [
        ("repository", "path_invalid"),
        ("digest", "path_invalid"),
        ("missing", "missing"),
        ("tamper", "sha256_mismatch"),
        ("json", "invalid"),
        ("schema", "invalid"),
    ],
)
def test_operation_receipt_is_repository_scoped_and_tamper_evident(
    tmp_path, monkeypatch, damage, gap
):
    monkeypatch.setattr(operation, "local_state_root", lambda root: root / "state")
    request = _request(tmp_path)
    receipt = operation.persist_operation(tmp_path, request)
    path, digest = pathlib.Path(receipt["path"]), receipt["sha256"]
    assert operation.load_operation(tmp_path, str(path), digest) == request
    assert operation.persist_operation(tmp_path, request) == receipt
    if damage == "repository":
        tmp_path = tmp_path / "other"
    elif damage == "digest":
        digest = "invalid"
    elif damage == "missing":
        path.unlink()
    elif damage == "tamper":
        path.write_bytes(b"tampered")
    else:
        content = b"{" if damage == "json" else b"{}"
        digest = hashlib.sha256(content).hexdigest()
        path = path.with_name(f"{digest}.json")
        path.write_bytes(content)
    before = path.read_bytes() if path.exists() else None
    with pytest.raises(ValueError, match=f"lane_retirement_receipt_{gap}"):
        operation.load_operation(tmp_path, str(path), digest)
    assert (path.read_bytes() if path.exists() else None) == before


@pytest.mark.parametrize(
    ("fault", "gap"),
    [
        ("actor", "foreign_work_lane_retire_authority_required"),
        ("control", "retirement_control_root_unavailable"),
        ("common", "lane_retirement_receipt_repository_mismatch"),
        ("identity", "lane_retirement_receipt_repository_mismatch"),
        ("git", "retirement_control_root_unavailable"),
        ("target", "retirement_execution_root_is_target"),
        ("execution", "retirement_execution_root_unavailable"),
    ],
)
def test_preflight_rejects_stale_authority_before_destructive_admission(
    tmp_path, monkeypatch, fault, gap
):
    repo = init_git_repo(tmp_path / "repo")
    write_test_profile(repo)
    head = commit_fixture(repo, "declare identity")
    request = _request(repo).model_copy(update={"accepted_head": head})
    monkeypatch.setenv("ETHOS_ACTOR", "foreign" if fault == "actor" else request.authority["actor"])
    updates = {
        "control": {"control_root": str(repo / "missing")},
        "common": {"repository_common_dir": str(tmp_path / "other")},
        "identity": {"repository_identity": "repository:foreign"},
        "target": {"execution_root": request.worktree_path},
        "execution": {"execution_root": str(repo / "missing")},
    }
    request = request.model_copy(update=updates.get(fault, {}))
    if fault == "git":
        monkeypatch.setattr(
            operation, "run_git", lambda *_a, **_k: subprocess.CompletedProcess((), 1, "", "failed")
        )
    monkeypatch.setattr(
        operation,
        "admit_git_effect",
        lambda *_a: pytest.fail("invalid preflight admitted deletion"),
    )
    with pytest.raises(ValueError, match=gap):
        operation.preflight_operation(repo, request)
    assert git(repo, "rev-parse", "HEAD") == head
    assert git(repo, "status", "--porcelain") == ""


def test_unobservable_failure_does_not_invent_progress(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = _request(tmp_path)
    monkeypatch.setattr(operation, "local_state_root", lambda _root: tmp_path / "state")
    monkeypatch.setattr(
        operation,
        "observe_operation",
        lambda *_args: (_ for _ in ()).throw(OSError("observation failed")),
    )

    report = operation.apply_operation(tmp_path, request, request_receipt={"path": "/receipt"})

    assert report["state"] == "blocked"
    assert report["required_gaps"] == ["observation failed"]
    assert "observed" not in report
    assert "completed_effects" not in report
    assert "remaining_effects" not in report
