"""Recover retirement under locks without replaying uncertain destructive effects."""

from __future__ import annotations

import json
import multiprocessing
import shlex
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest
from filelock import FileLock

import ethos.adapters.mutation.lane_retirement.operation as operation
from ethos.adapters.process import ProcessExecutionError
from ethos.contracts.retirement import RetirementObservation
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_test_profile
from tests.support.lane_scenarios import retirement_request

if TYPE_CHECKING:
    from multiprocessing.synchronize import Event
    from pathlib import Path


def _hold_retirement_lock(path: str, ready: Event, release: Event) -> None:
    with FileLock(path):
        ready.set()
        release.wait(60)


@pytest.mark.parametrize("entrypoint", ["apply", "recover"])
@pytest.mark.parametrize("apply", [False, True])
@pytest.mark.parametrize("termination", ["release", "kill"])
def test_lock_contention_preserves_request_and_recovers_after_owner_exit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    entrypoint: str,
    termination: str,
    *,
    apply: bool,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    request = retirement_request(repo)
    monkeypatch.setenv("ETHOS_ACTOR", request.authority["actor"])
    receipt = operation.persist_operation(repo, request)
    state = operation.local_state_root(repo)
    lock = state / "operations" / "lane-retirement.lock"
    lock.parent.mkdir(parents=True)
    before = {path: path.read_bytes() for path in repo.rglob("*") if path.is_file()}
    script = """import json, sys
from ethos.adapters.mutation.lane_retirement import operation
request, receipt, apply, entrypoint = json.load(sys.stdin)
request = operation.RetirementOperation.model_validate(request)
result = (operation.apply_operation(request, request_receipt=receipt, apply=apply)
          if entrypoint == 'apply' else operation.execute_retirement_operation(
              root=operation.Path(request.control_root), receipt_path=receipt['path'],
              receipt_sha256=receipt['sha256'], apply=apply, authorized=True))
print(json.dumps(result))
"""
    command = [sys.executable, "-B", "-c", script]
    payload = json.dumps([request.model_dump(mode="json"), receipt, apply, entrypoint])
    context = multiprocessing.get_context("spawn")
    ready, release = context.Event(), context.Event()
    owner = context.Process(target=_hold_retirement_lock, args=(str(lock), ready, release))
    owner.start()
    try:
        assert ready.wait(10), "lock owner did not become ready"
        result = subprocess.run(
            command,
            input=payload,
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        report = json.loads(result.stdout)
        assert report["verdict"] == "block"
        assert report["required_gaps"] == ["lane_retirement_in_progress"]
        assert all(report["receipt"][key] == receipt[key] for key in ("path", "sha256"))
        assert (
            not {"observed", "completed_effects", "remaining_effects", "progress_receipt"}
            & report.keys()
        )
        continuation = shlex.split(report["next_action"])
        assert continuation[:4] == ["ethos", "lane", "retire", "recover"]
        assert continuation[continuation.index("--receipt") + 1] == receipt["path"]
        assert continuation[continuation.index("--receipt-sha256") + 1] == receipt["sha256"]
        assert owner.is_alive()
        assert before == {
            path: path.read_bytes() for path in repo.rglob("*") if path.is_file() and path != lock
        }
    finally:
        if termination == "release":
            release.set()
            owner.join(timeout=10)
        if owner.is_alive():
            owner.kill()
            owner.join(timeout=10)
        assert not owner.is_alive()
        owner.close()
    recovered = subprocess.run(
        command, input=payload, cwd=repo, capture_output=True, text=True, timeout=10, check=False
    )
    assert recovered.returncode == 0, recovered.stderr
    # The synthetic receipt has no matching live refs: recovery must revalidate it.
    assert json.loads(recovered.stdout)["required_gaps"] == ["retirement_operation_state_drift"]


@pytest.mark.parametrize(
    ("completed", "remaining", "state"),
    [
        ((), ("remove_worktree", "delete_ref", "revoke_lease"), "ready"),
        (("remove_worktree",), ("delete_ref", "revoke_lease"), "partial_transition"),
        (("remove_worktree", "delete_ref"), ("revoke_lease",), "partial_transition"),
        (("remove_worktree", "delete_ref", "revoke_lease"), (), "terminal"),
    ],
)
def test_retirement_progress_is_a_pure_reduction(tmp_path, completed, remaining, state):
    request = retirement_request(tmp_path)
    observed = RetirementObservation.model_validate(
        dict(
            zip(
                ("worktree_state", "ref_state", "lease_state"),
                ("absent" if effect in completed else "expected" for effect in request.effects),
                strict=True,
            )
        )
    )
    progress = operation.reduce_progress(request, observed)
    assert (progress.completed_effects, progress.remaining_effects, progress.state) == (
        completed,
        remaining,
        state,
    )


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
    request = retirement_request(tmp_path).model_copy(update=updates)
    observation = RetirementObservation.model_validate(
        {
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
    request = retirement_request(tmp_path).model_copy(
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


@pytest.mark.parametrize("failure", [False, True])
@pytest.mark.parametrize("worktree_state", ["expected", "absent"])
def test_preflight_failure_and_dry_run_never_start_destructive_effects(
    tmp_path, monkeypatch, failure, worktree_state
):
    request = retirement_request(tmp_path)
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
        return operation.reduce_progress(
            request,
            RetirementObservation(
                worktree_state=worktree_state, ref_state="expected", lease_state="expected"
            ),
        )

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
    report = operation.apply_operation(request, request_receipt={"path": "/receipt"}, apply=failure)
    partial = not failure and worktree_state == "absent"
    assert report["state"] == (
        "blocked" if failure else "partial_transition" if partial else "ready"
    )
    assert report["completed_effects"] == (["remove_worktree"] if partial else [])
    assert report["remaining_effects"] == (
        ([] if partial else ["remove_worktree"]) + ["delete_ref", "revoke_lease"]
    )
    assert report["required_gaps"] == (
        ["git_process_spawn_failed"] if failure else ["lane_retirement_partial"] if partial else []
    )


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
    request = retirement_request(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", actor)
    monkeypatch.setattr(operation, "load_operation", lambda *_args: request)
    monkeypatch.setattr(
        operation,
        "apply_operation",
        lambda *_a, **_k: pytest.fail("unauthorized recovery executed"),
    )
    report = operation.execute_retirement_operation(
        root=tmp_path,
        receipt_path="/receipt",
        receipt_sha256="sha256:" + "d" * 64,
        apply=True,
        authorized=authorized,
    )
    assert report["state"] == "blocked"
    assert report["required_gaps"] == [gap]


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
    request = retirement_request(repo).model_copy(update={"accepted_head": head})
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


@pytest.mark.parametrize("role", ["control", "execution"])
@pytest.mark.parametrize("fault", ["nested", "junction", "foreign"])
def test_preflight_requires_exact_native_repository_roots(tmp_path, monkeypatch, role, fault):
    repo = init_git_repo(tmp_path / "repo")
    write_test_profile(repo)
    head = commit_fixture(repo, "declare identity")
    if fault == "foreign":
        selected = init_git_repo(tmp_path / "foreign")
    else:
        selected = repo / "nested" if fault == "nested" else repo
        selected.mkdir(exist_ok=True)
    request = retirement_request(repo).model_copy(
        update={"accepted_head": head, f"{role}_root": str(selected)}
    )
    monkeypatch.setenv("ETHOS_ACTOR", request.authority["actor"])
    if fault == "junction":
        monkeypatch.setattr(operation, "is_junction", lambda path: path == selected)
    monkeypatch.setattr(
        operation,
        "observe_operation",
        lambda *_args: pytest.fail("invalid root reached carrier observation"),
    )
    gap = (
        "lane_retirement_receipt_repository_mismatch"
        if fault == "foreign" and role == "control"
        else f"retirement_{'control' if fault == 'junction' else role}_root_unavailable"
    )
    with pytest.raises(ValueError, match=gap):
        operation.preflight_operation(repo, request)
    assert git(repo, "rev-parse", "HEAD") == head
    assert git(repo, "status", "--porcelain") == ""


@pytest.mark.parametrize("process_error", [False, True])
def test_unobservable_failure_does_not_invent_progress(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, process_error: bool
) -> None:
    request = retirement_request(init_git_repo(tmp_path / "repo"))
    monkeypatch.setenv("ETHOS_ACTOR", request.authority["actor"])
    monkeypatch.setattr(operation, "local_state_root", lambda _root: tmp_path / "state")
    failure = (
        ProcessExecutionError(
            "native_process_observer_unavailable",
            reason="process_creation_failed",
            command=("/native/observer",),
            cwd=tmp_path.as_posix(),
            cause="permission denied",
        )
        if process_error
        else OSError("observation failed")
    )
    monkeypatch.setattr(
        operation,
        "observe_operation",
        lambda *_args: (_ for _ in ()).throw(failure),
    )

    report = operation.apply_operation(request, request_receipt={"path": "/receipt"})

    assert report["state"] == "blocked"
    assert report["required_gaps"] == [str(failure)]
    if isinstance(failure, ProcessExecutionError):
        assert report["process_failure"] == failure.evidence()
    else:
        assert "process_failure" not in report
    assert "observed" not in report
    assert "completed_effects" not in report
    assert "remaining_effects" not in report
