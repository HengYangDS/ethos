from __future__ import annotations

import hashlib
import json
import multiprocessing
import pathlib
import shlex
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest
from filelock import FileLock

import ethos.adapters.mutation.lane_retirement.operation as operation
from ethos.adapters.process import ProcessExecutionError
from ethos.contracts.retirement import RetirementObservation
from ethos.contracts.retirement import RetirementOperation
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_test_profile

if TYPE_CHECKING:
    from multiprocessing.synchronize import Event
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
    request = _request(repo)
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


def test_empty_review_extension_preserves_historical_receipt_identity(tmp_path, monkeypatch):
    monkeypatch.setattr(operation, "local_state_root", lambda root: root / "state")
    historical = _request(tmp_path).model_dump(mode="json")
    historical.pop("reviewed_content", None)
    payload = json.dumps(historical, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(payload).hexdigest()
    path = operation.operation_store(tmp_path) / f"{digest}.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(payload)

    restored = operation.load_operation(tmp_path, str(path), digest)

    assert restored.digest() == digest
    assert restored.model_dump(mode="json") == historical
    assert operation.persist_operation(tmp_path, restored)["path"] == str(path)
    assert path.read_bytes() == payload


def test_reviewed_receipt_uses_the_same_identity_as_its_request(tmp_path, monkeypatch):
    monkeypatch.setattr(operation, "local_state_root", lambda root: root / "state")
    payload = _reviewed_request(tmp_path)
    content = payload["reviewed_content"]
    assert isinstance(content, dict)
    entries = content["entries"]
    entries["\ue000"] = entries["src/module.py"]
    entries["\U00010000"] = entries["src/module.py"]
    request = RetirementOperation.model_validate(payload)

    receipt = operation.persist_operation(tmp_path, request)
    path, digest = receipt["path"], receipt["sha256"]
    assert isinstance(path, str)
    assert isinstance(digest, str)
    raw = pathlib.Path(path).read_bytes()

    assert raw.index('"\U00010000"'.encode()) < raw.index('"\ue000"'.encode())
    assert digest == f"sha256:{request.digest()}"
    assert pathlib.Path(path).stem == request.digest()
    assert operation.load_operation(tmp_path, path, digest) == request


def _reviewed_request(tmp_path: Path) -> dict[str, object]:
    payload = _request(tmp_path).model_dump(mode="json")
    file = {"kind": "file", "identity": ["1"] * 8, "sha256": "a" * 64}
    directory = {"kind": "directory", "identity": ["2"] * 8}
    payload["reviewed_content"] = {
        "root": directory,
        "index_path": str(tmp_path / ".git/worktrees/lane/index"),
        "index": file,
        "entries": {".git": file, "src": directory, "src/module.py": file},
    }
    return json.loads(json.dumps(payload))


@pytest.mark.parametrize(
    "updates",
    [
        {"mode": "landed"},
        {"worktree_initial": "unbound"},
        {"reviewed_content": {}},
        {"lease_state": "valid"},
        {"lease": {"generation": 1}},
        {"git_plan": {"digest": "a" * 64}},
        {"effects": ["remove_worktree", "delete_ref"]},
    ],
)
def test_detached_receipt_rejects_invented_resources(tmp_path, updates):
    payload = _reviewed_request(tmp_path) | {
        "branch": "",
        "lease_state": "missing",
        "lease": {},
        "git_plan": {},
        "effects": ["remove_worktree"],
    }
    with pytest.raises(
        ValueError, match=r"retirement_(?:detached_resources|operation_effects)_invalid"
    ):
        RetirementOperation.model_validate(payload | updates)


@pytest.mark.parametrize(
    ("coordinate", "replacement"),
    [
        (("root", "kind"), "file"),
        (("index", "kind"), "symlink"),
        (("index_path",), "relative/index"),
        (("entries",), {}),
        (("entries", "src"), {"kind": "socket", "identity": ["1"] * 8}),
        (("entries", "src/module.py", "sha256"), "invalid"),
        (("entries", "src/module.py", "identity"), [1] * 8),
        (("entries", "src/module.py", "identity"), ["1"] * 7),
        (("entries", "src/module.py", "identity"), ["01"] * 8),
        (("entries", "src/module.py", "target"), "unexpected"),
    ],
)
def test_receipt_reader_rejects_malformed_reviewed_inventory(
    tmp_path, monkeypatch, coordinate, replacement
):
    monkeypatch.setattr(operation, "local_state_root", lambda root: root / "state")
    payload = _reviewed_request(tmp_path)
    content = payload["reviewed_content"]
    assert isinstance(content, dict)
    for key in coordinate[:-1]:
        content = content[key]
    content[coordinate[-1]] = replacement
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(raw).hexdigest()
    path = operation.operation_store(tmp_path) / f"{digest}.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(raw)

    with pytest.raises(ValueError, match="lane_retirement_receipt_invalid"):
        operation.load_operation(tmp_path, str(path), digest)
    assert path.read_bytes() == raw


@pytest.mark.parametrize(
    "path",
    ["../escape.py", "/absolute.py", "./alias.py", "src//alias.py", "missing/file.py", "src/.git"],
)
def test_reviewed_inventory_requires_exact_relative_tree(tmp_path, path):
    payload = _reviewed_request(tmp_path)
    content = payload["reviewed_content"]
    assert isinstance(content, dict)
    content["entries"][path] = content["entries"].pop("src/module.py")

    with pytest.raises(ValueError, match="retirement_content_tree_invalid"):
        RetirementOperation.model_validate(payload)


def test_reviewed_inventory_cannot_traverse_a_link(tmp_path):
    payload = _reviewed_request(tmp_path)
    content = payload["reviewed_content"]
    assert isinstance(content, dict)
    content["entries"]["src"] = {"kind": "symlink", "identity": ["3"] * 8, "target": "../external"}

    with pytest.raises(ValueError, match="retirement_content_tree_invalid"):
        RetirementOperation.model_validate(payload)


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
    request = _request(tmp_path)
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
    request = _request(tmp_path).model_copy(update=updates)
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


@pytest.mark.parametrize("failure", [False, True])
@pytest.mark.parametrize("worktree_state", ["expected", "absent"])
def test_preflight_failure_and_dry_run_never_start_destructive_effects(
    tmp_path, monkeypatch, failure, worktree_state
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
    request = _request(tmp_path)
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
    path_value, digest = receipt["path"], receipt["sha256"]
    assert isinstance(path_value, str)
    assert isinstance(digest, str)
    path = pathlib.Path(path_value)
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
    request = _request(repo).model_copy(
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
    request = _request(init_git_repo(tmp_path / "repo"))
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
