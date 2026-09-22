"""Reviewed retirement inventory rejects foreign, replaced and unobservable content."""

from __future__ import annotations

import json
import os
import select
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import ethos.adapters.mutation.lane_retirement.abandonment as abandonment
import ethos.adapters.mutation.lane_retirement.content as content
import ethos.adapters.mutation.lane_retirement.operation as operation
import ethos.adapters.repo.worktree_effects as worktree_effects
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.repo.git import GitExecutionError
from ethos.adapters.store.state.lease.projection import observe_lease
from ethos.adapters.store.state.schema import state_database
from tests.support.ethos_cli_runner import run_ethos
from tests.support.governed_repository import git
from tests.support.lane_scenarios import apply_retirement_receipt
from tests.support.lane_scenarios import derive_abandonment


@pytest.mark.parametrize("boundary", ["root", "parent"])
def test_reviewed_inventory_never_opens_through_replaced_parent(
    divergent_lane, monkeypatch, boundary
):
    repo, lane = divergent_lane
    nested = lane / "nested"
    nested.mkdir()
    (nested / "material.txt").write_text("reviewed local bytes\n")
    selected = lane if boundary == "root" else nested
    retained = selected.with_name(f"{selected.name}-retained")
    external = repo.parent / "external"
    external_file = external / ("nested/material.txt" if boundary == "root" else "material.txt")
    external_file.parent.mkdir(parents=True)
    external_file.write_text("unrelated private bytes\n")
    external_identity = external_file.stat()
    native_open = os.open
    opened_external = []
    swapped = False

    def replace_before_open(path, flags, *args, **kwargs):
        nonlocal swapped
        if Path(path).name == "material.txt" and not swapped:
            selected.rename(retained)
            selected.symlink_to(external, target_is_directory=True)
            swapped = True
        descriptor = native_open(path, flags, *args, **kwargs)
        observed = os.fstat(descriptor)
        if (observed.st_dev, observed.st_ino) == (
            external_identity.st_dev,
            external_identity.st_ino,
        ):
            opened_external.append(str(path))
        return descriptor

    monkeypatch.setattr(content.os, "open", replace_before_open)
    before = git(repo, "show-ref")
    try:
        result = derive_abandonment(repo, review_content=True)
    finally:
        if swapped:
            selected.unlink()
            retained.rename(selected)

    assert swapped, "fault did not reach the content observer"
    assert not opened_external, opened_external
    assert result["verdict"] == "block", result
    assert result["required_gaps"] == ["retirement_content_drift"]
    assert external_file.read_text() == "unrelated private bytes\n"
    assert git(repo, "show-ref") == before
    assert not operation.operation_store(repo).exists()


@pytest.mark.parametrize("boundary", ["root", "directory", "file", "index"])
@pytest.mark.parametrize("coordinate", ["st_uid", "st_dev"])
def test_reviewed_inventory_rejects_foreign_native_nodes_before_reading(
    divergent_lane, monkeypatch, boundary, coordinate
):
    repo, lane = divergent_lane
    directory = lane / "nested"
    directory.mkdir()
    selected = {
        "root": lane,
        "directory": directory,
        "file": lane / "abandoned.txt",
        "index": Path(git(lane, "rev-parse", "--path-format=absolute", "--git-path", "index")),
    }[boundary]
    identity = selected.stat()
    native_stat, native_fstat, native_open = os.stat, os.fstat, os.open
    opened = []

    def observed(value):
        if (value.st_dev, value.st_ino) != (identity.st_dev, identity.st_ino):
            return value
        fields = {name: getattr(value, name) for name in dir(value) if name.startswith("st_")}
        fields[coordinate] += 1
        return SimpleNamespace(**fields)

    def observe_open(*args, **kwargs):
        descriptor = native_open(*args, **kwargs)
        value = native_fstat(descriptor)
        if (value.st_dev, value.st_ino) == (identity.st_dev, identity.st_ino):
            opened.append(descriptor)
        return descriptor

    monkeypatch.setattr(content.os, "stat", lambda *a, **kw: observed(native_stat(*a, **kw)))
    monkeypatch.setattr(content.os, "fstat", lambda fd: observed(native_fstat(fd)))
    monkeypatch.setattr(content.os, "open", observe_open)
    before = git(repo, "show-ref")

    result = derive_abandonment(repo, review_content=True)

    assert result["verdict"] == "block", result
    assert result["required_gaps"] == [
        "retirement_content_owner_mismatch"
        if coordinate == "st_uid"
        else "retirement_content_filesystem_mismatch"
    ]
    assert not opened, "the observer entered or read a foreign node"
    assert git(repo, "show-ref") == before
    assert (lane / "abandoned.txt").read_text() == "abandoned\n"
    assert not operation.operation_store(repo).exists()


def test_reviewed_inventory_preserves_literal_link_without_opening_target(divergent_lane):
    repo, lane = divergent_lane
    external = repo.parent / "external.txt"
    external.write_text("unrelated data\n")
    literal = ".././external.txt"
    (lane / "external-link").symlink_to(literal)

    result = derive_abandonment(repo, review_content=True)

    assert result["verdict"] == "pass", result
    receipt = result["receipt"]
    assert isinstance(receipt, dict)
    request = operation.load_operation(repo, receipt["path"], receipt["sha256"])
    observed = request.reviewed_content["entries"]["external-link"]
    assert observed["kind"] == "symlink"
    assert observed["target"] == literal
    assert "sha256" not in observed
    assert external.read_text() == "unrelated data\n"


@pytest.mark.parametrize("fault", ["unavailable", "enumeration", "nested", "fifo"])
def test_reviewed_inventory_rejects_incomplete_or_unsafe_observation(
    divergent_lane, monkeypatch, fault
):
    repo, lane = divergent_lane
    if fault == "unavailable":
        monkeypatch.delattr(content.os, "fwalk")
    elif fault == "enumeration":

        def fail_walk(*_args, onerror, **_kwargs):
            onerror(PermissionError("selected_directory_unreadable"))
            return iter(())

        monkeypatch.setattr(content.os, "fwalk", fail_walk)
    elif fault == "nested":
        (lane / "nested/.git").mkdir(parents=True)
    else:
        os.mkfifo(lane / "pipe")
    before = git(repo, "show-ref")

    result = derive_abandonment(repo, review_content=True)

    assert result["verdict"] == "block", result
    assert result["required_gaps"] == [
        {
            "unavailable": "retirement_content_observation_unavailable",
            "enumeration": "selected_directory_unreadable",
            "nested": "retirement_nested_repository",
            "fifo": "retirement_content_unsafe",
        }[fault]
    ]
    assert git(repo, "show-ref") == before
    assert (lane / "abandoned.txt").read_text() == "abandoned\n"
    assert not operation.operation_store(repo).exists()


@pytest.mark.skipif(os.name != "posix", reason="native POSIX process-reference observation")
@pytest.mark.parametrize("consumer", ["cwd", "file", "mapping", "hardlink", "writer"])
@pytest.mark.parametrize("detached", [False, True])
def test_reviewed_retirement_preserves_content_held_by_live_process(
    divergent_lane, consumer, detached
):
    repo, lane = divergent_lane
    if detached:
        git(lane, "switch", "--detach")
    selected = lane if consumer == "cwd" else lane / "abandoned.txt"
    if consumer == "hardlink":
        selected = repo.parent / "external-hardlink"
        os.link(lane / "abandoned.txt", selected)
    derived = derive_abandonment(repo, review_content=True, path=lane if detached else None)
    assert derived["verdict"] == "pass", json.dumps(derived, indent=2)
    receipt = derived["receipt"]
    assert isinstance(receipt, dict)
    script = """import json, mmap, os, sys
mode, path = json.loads(sys.stdin.readline())
if mode == 'cwd':
    os.chdir(path)
else:
    source = open(path, 'r+b' if mode == 'writer' else 'rb')
    if mode == 'mapping':
        mapped = mmap.mmap(source.fileno(), 0, access=mmap.ACCESS_READ)
        source.close()
print('ready', flush=True)
sys.stdin.read(1)
if mode == 'writer':
    source.write(b'stopped writer bytes\\n')
    source.flush()
    os.fsync(source.fileno())
"""
    before = (git(repo, "show-ref"), observe_lease(state_database(repo), "work/abandon"))
    with subprocess.Popen(
        [sys.executable, "-B", "-c", script],
        cwd=repo,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as child:
        assert child.stdin is not None
        assert child.stdout is not None
        try:
            child.stdin.write(json.dumps([consumer, str(selected)]) + "\n")
            child.stdin.flush()
            assert select.select([child.stdout], [], [], 10)[0], "consumer did not become ready"
            assert child.stdout.readline() == "ready\n"
            assert child.poll() is None
            result = apply_retirement_receipt(repo, receipt)
        finally:
            child.communicate("x", timeout=10)

    assert lane.is_dir(), json.dumps(result, indent=2)
    assert child.returncode == 0
    assert (lane / "abandoned.txt").read_text() == (
        "stopped writer bytes\n" if consumer == "writer" else "abandoned\n"
    )
    assert result["required_gaps"] == ["retirement_content_in_use"], json.dumps(result, indent=2)
    assert before == (git(repo, "show-ref"), observe_lease(state_database(repo), "work/abandon"))
    released = operation.execute_retirement_operation(
        root=repo,
        receipt_path=receipt["path"],
        receipt_sha256=receipt["sha256"],
        apply=False,
        authorized=False,
    )
    assert released["verdict"] == ("block" if consumer == "writer" else "pass"), json.dumps(
        released, indent=2
    )
    reviewed = derive_abandonment(repo, review_content=True, path=lane if detached else None)
    assert reviewed["verdict"] == "pass", json.dumps(reviewed, indent=2)
    final_receipt = reviewed["receipt"]
    assert isinstance(final_receipt, dict)
    retired = apply_retirement_receipt(repo, final_receipt)
    assert retired["state"] == "retired", json.dumps(retired, indent=2)
    assert not lane.exists()
    assert str(lane) not in git(repo, "worktree", "list", "--porcelain")
    if not detached:
        assert git(repo, "branch", "--list", "work/abandon") == ""
    assert observe_lease(state_database(repo), "work/abandon").state == (
        "valid" if detached else "missing"
    )


@pytest.mark.parametrize("error_type", [ProcessExecutionError, GitExecutionError])
@pytest.mark.parametrize("detached", [False, True])
def test_reviewed_retirement_rejects_unknown_process_references(
    divergent_lane, monkeypatch, error_type, detached
):
    repo, lane = divergent_lane
    if detached:
        git(lane, "switch", "--detach")
    derived = derive_abandonment(repo, review_content=True, path=lane if detached else None)
    assert derived["verdict"] == "pass", derived
    receipt = derived["receipt"]
    assert isinstance(receipt, dict)
    before = git(repo, "show-ref")

    error = error_type(
        "native_process_observer_unavailable",
        reason="file_references_unavailable",
        command=("/native/observer", "--files"),
        cwd=repo.as_posix(),
        cause="permission denied",
    )

    def unavailable(_root):
        raise error

    monkeypatch.setattr(operation, "process_file_identities", unavailable)
    result = apply_retirement_receipt(repo, receipt)

    assert result["required_gaps"] == ["native_process_observer_unavailable"], result
    assert result["process_failure"] == error.evidence()
    assert lane.is_dir()
    assert (lane / "abandoned.txt").read_text() == "abandoned\n"
    assert git(repo, "show-ref") == before


@pytest.mark.parametrize("dirty_kind", ["staged", "unstaged", "untracked", "ignored"])
@pytest.mark.parametrize("detached", [False, True])
def test_reviewed_absorbed_content_derives_exact_public_receipt(
    divergent_lane, dirty_kind, detached
):
    repo, lane = divergent_lane
    git(repo, "reset", "--hard", git(lane, "rev-parse", "HEAD"))
    if detached:
        git(lane, "switch", "--detach")
    target = lane / ("residual.txt" if dirty_kind in {"untracked", "ignored"} else "abandoned.txt")
    target.write_text("reviewed residual\n")
    if dirty_kind == "staged":
        git(lane, "add", target.name)
    if dirty_kind == "ignored":
        (lane / ".gitignore").write_text("residual.txt\n")
    before = (git(repo, "show-ref"), git(lane, "diff", "--cached"), target.read_bytes())

    result = run_ethos(
        "lane",
        "retire",
        "abandon",
        "--path" if detached else "--branch",
        str(lane) if detached else "work/abandon",
        "--reason-code",
        "absorbed-content",
        "--reason",
        "current tests preserve this obligation",
        "--review-content",
        "--json",
        cwd=repo,
    )

    assert result["verdict"] == "pass", result
    data = result["data"]
    receipt = data["receipt"]
    request = operation.load_operation(repo, receipt["path"], receipt["sha256"])
    assert request.reviewed_content["entries"][target.name]
    assert request.reviewed_content["index"]
    assert request.reviewed_content["root"]
    if detached:
        assert request.effects == ("remove_worktree",)
        assert (request.branch, request.git_plan, request.lease) == ("", {}, {})
    else:
        assert request.git_plan["facts"]["values"]["linked_worktree"]["clean"] is False
    assert (
        request.digest()
        == operation.load_operation(repo, receipt["path"], receipt["sha256"]).digest()
    )
    assert before == (git(repo, "show-ref"), git(lane, "diff", "--cached"), target.read_bytes())

    target.write_text("unreviewed replacement\n")
    rejected = apply_retirement_receipt(repo, receipt)
    assert rejected["verdict"] == "block"
    assert rejected["required_gaps"] == ["retirement_content_drift"]
    assert target.read_text() == "unreviewed replacement\n"
    assert git(repo, "show-ref") == before[0]
    assert observe_lease(state_database(repo), "work/abandon").state == "valid"


@pytest.mark.parametrize("fault", ["symlink", "unbound", "locked"])
@pytest.mark.parametrize("detached", [False, True])
def test_reviewed_derivation_rejects_unsafe_target_before_inventory(
    divergent_lane, monkeypatch, fault, detached
):
    repo, lane = divergent_lane
    if detached:
        git(lane, "switch", "--detach")
    if fault == "symlink":
        retained = lane.with_name("retained")
        lane.rename(retained)
        lane.symlink_to(retained, target_is_directory=True)
    elif fault == "unbound":
        git(repo, "worktree", "remove", str(lane))
    else:
        git(repo, "worktree", "lock", str(lane))
    before = (git(repo, "show-ref"), observe_lease(state_database(repo), "work/abandon"))
    monkeypatch.setattr(
        "ethos.adapters.mutation.lane_retirement.linked_effect.reviewed_content",
        lambda _root: pytest.fail("unsafe or absent target reached inventory observation"),
    )

    result = derive_abandonment(repo, review_content=True, path=lane if detached else None)

    assert result["verdict"] == "block", result
    assert result["required_gaps"] == [
        "retirement_reviewed_worktree_required"
        if fault == "unbound"
        else "retirement_content_unsafe"
        if fault == "symlink"
        else "retirement_worktree_locked"
    ]
    assert before == (git(repo, "show-ref"), observe_lease(state_database(repo), "work/abandon"))
    assert not operation.operation_store(repo).exists()


@pytest.mark.parametrize(
    ("drift", "detached"),
    [
        (case, False)
        for case in ("ignored", "process-scan", "git-admission", "actor", "lease", "accepted")
    ]
    + [(case, True) for case in ("ignored", "process-scan", "actor", "accepted")]
    + [("unreviewed", False)],
)
def test_retirement_rechecks_after_native_worktree_observation(
    divergent_lane, monkeypatch, drift, detached
):
    repo, lane = divergent_lane
    if detached:
        git(lane, "switch", "--detach")
    (repo / ".git/info").mkdir(exist_ok=True)
    (repo / ".git/info/exclude").write_text("residual.txt\n")
    reviewed = drift != "unreviewed"
    derived = derive_abandonment(repo, review_content=reviewed, path=lane if detached else None)
    assert derived["verdict"] == "pass", derived
    receipt = derived["receipt"]
    request = operation.load_operation(repo, receipt["path"], receipt["sha256"])
    native_observation = worktree_effects.worktree_record
    original_bytes = (lane / "abandoned.txt").read_bytes()

    def observe_then_drift(*args, **kwargs):
        record = native_observation(*args, **kwargs)
        monkeypatch.setattr(worktree_effects, "worktree_record", native_observation)
        if drift in {"process-scan", "git-admission"}:
            observer = "process_file_identities" if drift == "process-scan" else "admit_git_effect"
            native_admission_observation = getattr(operation, observer)

            def observe_then_write(*args, **kwargs):
                observed = native_admission_observation(*args, **kwargs)
                (lane / "residual.txt").write_text("new unreviewed ignored data\n")
                return observed

            monkeypatch.setattr(operation, observer, observe_then_write)
        elif drift in {"ignored", "unreviewed"}:
            (lane / "residual.txt").write_text("new unreviewed ignored data\n")
        elif drift == "actor":
            monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:foreign")
        elif drift == "lease":
            operation.revoke_operation_lease(repo, request)
        else:
            git(repo, "update-ref", "refs/heads/dev", request.head, request.accepted_head)
        return record

    monkeypatch.setattr(worktree_effects, "worktree_record", observe_then_drift)
    result = apply_retirement_receipt(repo, receipt)

    assert lane.is_dir(), result
    assert (lane / "abandoned.txt").read_bytes() == original_bytes
    assert git(repo, "rev-parse", "refs/heads/work/abandon") == request.head
    assert result["verdict"] == "block", result
    assert result["required_gaps"] == [
        "retirement_content_review_required"
        if drift == "unreviewed"
        else "retirement_content_drift"
        if drift in {"ignored", "process-scan", "git-admission"}
        else "foreign_work_lane_retire_authority_required"
        if drift == "actor"
        else "retirement_operation_state_drift"
    ]
    if drift in {"ignored", "unreviewed", "process-scan", "git-admission"}:
        assert (lane / "residual.txt").read_text() == "new unreviewed ignored data\n"


@pytest.mark.parametrize(
    ("path", "branch", "review", "gap"),
    [
        (".", "", True, "retirement_target_path_not_absolute"),
        ("lane", "work/abandon", True, "retirement_target_selection_invalid"),
        ("lane", "", False, "retirement_target_selection_invalid"),
        ("lane", "", True, "retirement_target_not_detached"),
        ("root", "", True, "retirement_target_not_detached"),
    ],
)
def test_detached_selection_rejects_ambiguous_or_bound_resources(
    divergent_lane, path, branch, review, gap
):
    repo, lane = divergent_lane
    before = (git(repo, "show-ref"), git(repo, "worktree", "list", "--porcelain"))
    result = abandonment.derive_lane_abandonment(
        root=repo,
        branch=branch,
        path={"lane": str(lane), "root": str(repo)}.get(path, path),
        reason_code="absorbed-content",
        reason="reviewed source",
        review_content=review,
    )
    assert result["required_gaps"] == [gap], result
    assert before == (git(repo, "show-ref"), git(repo, "worktree", "list", "--porcelain"))
    assert not operation.operation_store(repo).exists()
