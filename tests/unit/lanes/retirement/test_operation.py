from __future__ import annotations

import json
import pathlib
import subprocess
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.lane_retirement.operation as operation
from ethos.contracts.retirement import RetirementObservation
from ethos.contracts.retirement import RetirementOperation

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
    ("observed", "completed", "remaining", "state"),
    [
        (
            RetirementObservation(
                worktree_state="expected", ref_state="expected", lease_state="expected"
            ),
            (),
            ("remove_worktree", "delete_ref", "revoke_lease"),
            "ready",
        ),
        (
            RetirementObservation(
                worktree_state="absent", ref_state="expected", lease_state="expected"
            ),
            ("remove_worktree",),
            ("delete_ref", "revoke_lease"),
            "partial_transition",
        ),
        (
            RetirementObservation(
                worktree_state="absent", ref_state="absent", lease_state="expected"
            ),
            ("remove_worktree", "delete_ref"),
            ("revoke_lease",),
            "partial_transition",
        ),
        (
            RetirementObservation(
                worktree_state="absent", ref_state="absent", lease_state="absent"
            ),
            ("remove_worktree", "delete_ref", "revoke_lease"),
            (),
            "terminal",
        ),
    ],
)
def test_retirement_progress_is_a_pure_reduction(
    tmp_path: Path,
    observed: RetirementObservation,
    completed: tuple[str, ...],
    remaining: tuple[str, ...],
    state: str,
) -> None:
    progress = operation.reduce_progress(_request(tmp_path), observed)

    assert progress.completed_effects == completed
    assert progress.remaining_effects == remaining
    assert progress.state == state


def test_retirement_progress_rejects_non_monotonic_or_ambiguous_carriers(tmp_path: Path) -> None:
    request = _request(tmp_path)

    with pytest.raises(ValueError, match="retirement_operation_state_drift"):
        operation.reduce_progress(
            request,
            RetirementObservation(
                worktree_state="absent",
                ref_state="moved",
                lease_state="expected",
            ),
        )


def test_unbound_request_rejects_a_new_worktree_binding(tmp_path: Path) -> None:
    request = _request(tmp_path).model_copy(
        update={"worktree_initial": "unbound", "worktree_path": ""}
    )

    with pytest.raises(ValueError, match="retirement_operation_state_drift"):
        operation.reduce_progress(
            request,
            RetirementObservation(
                worktree_state="expected",
                ref_state="expected",
                lease_state="expected",
            ),
        )


def test_missing_lease_request_rejects_a_new_lease(tmp_path: Path) -> None:
    request = _request(tmp_path).model_copy(update={"lease_state": "missing", "lease": {}})

    with pytest.raises(ValueError, match="retirement_operation_state_drift"):
        operation.reduce_progress(
            request,
            RetirementObservation(
                worktree_state="expected",
                ref_state="expected",
                lease_state="expected",
            ),
        )


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


def test_preflight_failure_never_starts_a_destructive_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = _request(tmp_path)
    monkeypatch.setattr(operation, "local_state_root", lambda _root: tmp_path / "state")
    monkeypatch.setattr(
        operation,
        "observe_operation",
        lambda *_args: RetirementObservation(
            worktree_state="expected", ref_state="expected", lease_state="expected"
        ),
    )
    monkeypatch.setattr(
        operation,
        "preflight_operation",
        lambda *_args: (_ for _ in ()).throw(ValueError("git_process_spawn_failed")),
    )
    monkeypatch.setattr(
        operation,
        "remove_operation_worktree",
        lambda *_args: pytest.fail("preflight failure must precede destructive effects"),
    )

    report = operation.apply_operation(tmp_path, request, request_receipt={"path": "/receipt"})

    assert report["state"] == "blocked"
    assert report["completed_effects"] == []
    assert report["remaining_effects"] == [
        "remove_worktree",
        "delete_ref",
        "revoke_lease",
    ]
    assert report["required_gaps"] == ["git_process_spawn_failed"]


def test_dry_run_is_observation_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    request = _request(tmp_path)
    monkeypatch.setattr(operation, "local_state_root", lambda _root: tmp_path / "state")
    monkeypatch.setattr(
        operation,
        "observe_operation",
        lambda *_args: RetirementObservation(
            worktree_state="expected", ref_state="expected", lease_state="expected"
        ),
    )
    monkeypatch.setattr(operation, "preflight_operation", lambda *_args: None)
    monkeypatch.setattr(
        operation,
        "persist_progress",
        lambda *_args: pytest.fail("dry-run must not persist progress"),
    )
    monkeypatch.setattr(
        operation,
        "remove_operation_worktree",
        lambda *_args: pytest.fail("dry-run must not mutate carriers"),
    )

    report = operation.apply_operation(
        tmp_path,
        request,
        request_receipt={"path": "/receipt"},
        apply=False,
    )

    assert report["state"] == "ready"
    assert report["completed_effects"] == []
    assert report["remaining_effects"] == [
        "remove_worktree",
        "delete_ref",
        "revoke_lease",
    ]


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


def test_recovery_blocks_when_current_actor_is_not_the_receipt_owner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = _request(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:foreign")
    monkeypatch.setattr(operation, "load_operation", lambda *_args: request)

    report = operation.recover_retirement_operation(
        root=tmp_path,
        receipt_path="/receipt",
        receipt_sha256="sha256:" + "d" * 64,
        apply=True,
        authorized=True,
    )

    assert report["state"] == "blocked"
    assert report["required_gaps"] == ["foreign_work_lane_retire_authority_required"]


def test_recovery_requires_explicit_authorization_before_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = _request(tmp_path)
    monkeypatch.setattr(operation, "load_operation", lambda *_args: request)
    monkeypatch.setattr(
        operation,
        "apply_operation",
        lambda *_args, **_kwargs: pytest.fail("unauthorized recovery must not execute"),
    )

    report = operation.recover_retirement_operation(
        root=tmp_path,
        receipt_path="/receipt",
        receipt_sha256="sha256:" + "d" * 64,
        apply=True,
        authorized=False,
    )

    assert report["state"] == "blocked"
    assert report["required_gaps"] == ["authorization_required"]


def test_operation_receipt_is_repository_scoped_and_tamper_evident(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    monkeypatch.setattr(operation, "local_state_root", lambda root: root / "state")
    request = _request(first)
    receipt = operation.persist_operation(first, request)

    with pytest.raises(ValueError, match="lane_retirement_receipt_path_invalid"):
        operation.load_operation(second, str(receipt["path"]), str(receipt["sha256"]))

    pathlib.Path(str(receipt["path"])).write_text(json.dumps({"tampered": True}), encoding="utf-8")
    with pytest.raises(ValueError, match="lane_retirement_receipt_sha256_mismatch"):
        operation.load_operation(first, str(receipt["path"]), str(receipt["sha256"]))


def test_terminal_receipt_binds_request_and_observed_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(operation, "local_state_root", lambda root: root / "state")
    request = _request(tmp_path)
    progress = operation.reduce_progress(
        request,
        RetirementObservation(worktree_state="absent", ref_state="absent", lease_state="absent"),
    )

    receipt = operation.persist_terminal_receipt(tmp_path, request, progress)
    payload = json.loads(pathlib.Path(str(receipt["path"])).read_text(encoding="utf-8"))

    assert payload["kind"] == "lane-retirement-receipt"
    assert payload["request"]["reason"] == request.reason
    assert payload["request"]["head"] == request.head
    assert payload["progress"]["completed_effects"] == list(request.effects)
    assert payload["progress"]["remaining_effects"] == []


def test_preflight_rejects_execution_from_the_destructive_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = _request(tmp_path)
    pathlib.Path(request.worktree_path).mkdir()
    request = request.model_copy(update={"execution_root": request.worktree_path})
    monkeypatch.setattr(operation, "_current_actor", lambda _request: True)
    monkeypatch.setattr(operation, "git_common_dir", lambda _root: request.repository_common_dir)
    monkeypatch.setattr(operation, "repository_identity", lambda *_args, **_kwargs: "")
    monkeypatch.setattr(operation, "git_executable", lambda _environment: "/usr/bin/git")
    monkeypatch.setattr(
        operation,
        "run_git",
        lambda *_args, **_kwargs: type("Result", (), {"returncode": 0})(),
    )

    with pytest.raises(ValueError, match="retirement_execution_root_is_target"):
        operation.preflight_operation(tmp_path, request)


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
