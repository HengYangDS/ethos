"""Verify reviewed retirement preserves content and reports exact admission failures."""

from __future__ import annotations

import json
import os
import select
import shutil
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
from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.adapters.store.state.lease.projection import observe_lease
from ethos.adapters.store.state.schema import state_database
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import exact_lease
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.runtime_scenarios import install_fixture_hook_runtime


@pytest.fixture
def divergent_lane(tmp_path, monkeypatch):
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    lane = tmp_path / "repo-work-abandon"
    git(repo, "worktree", "add", "-b", "work/abandon", str(lane), "dev")
    for root, name in ((repo, "accepted"), (lane, "abandoned")):
        (root / f"{name}.txt").write_text(f"{name}\n", encoding="utf-8")
        commit_fixture(root, f"advance {name} independently")
    actor = "agent:test:case:abandonment-recovery"
    acquire_lease(state_database(repo), lease=exact_lease(branch="work/abandon", holder_ref=actor))
    monkeypatch.setenv("ETHOS_ACTOR", actor)
    return repo, lane


def _derive(
    repo: Path,
    *,
    review_content: bool = False,
    branch: str = "work/abandon",
    path: Path | None = None,
    reason_code: str = "superseded-experiment",
    reason: str = "discard divergent experiment",
):
    return abandonment.derive_lane_abandonment(
        root=repo,
        branch="" if path else branch,
        path=str(path) if path else "",
        reason_code=reason_code,
        reason=reason,
        review_content=review_content,
    )


def _apply_receipt(repo, receipt):
    """Apply the exact reviewed receipt without replacing production admission."""
    return operation.execute_retirement_operation(
        root=repo,
        receipt_path=receipt["path"],
        receipt_sha256=receipt["sha256"],
        apply=True,
        authorized=True,
    )


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
    derived = _derive(repo, review_content=True, path=lane if detached else None)
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
            result = _apply_receipt(repo, receipt)
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
    reviewed = _derive(repo, review_content=True, path=lane if detached else None)
    assert reviewed["verdict"] == "pass", json.dumps(reviewed, indent=2)
    final_receipt = reviewed["receipt"]
    assert isinstance(final_receipt, dict)
    retired = operation.execute_retirement_operation(
        root=repo,
        receipt_path=final_receipt["path"],
        receipt_sha256=final_receipt["sha256"],
        apply=True,
        authorized=True,
    )
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
    derived = _derive(repo, review_content=True, path=lane if detached else None)
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
    result = _apply_receipt(repo, receipt)

    assert result["required_gaps"] == ["native_process_observer_unavailable"], result
    assert result["process_failure"] == error.evidence()
    assert lane.is_dir()
    assert (lane / "abandoned.txt").read_text() == "abandoned\n"
    assert git(repo, "show-ref") == before


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
        result = _derive(repo, review_content=True)
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

    result = _derive(repo, review_content=True)

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

    result = _derive(repo, review_content=True)

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

    result = _derive(repo, review_content=True)

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


@pytest.mark.parametrize(
    ("lease_state", "reacquired"),
    [
        ("missing", False),
        ("expired", False),
        ("valid", False),
        ("missing", True),
        ("expired", True),
    ],
)
@pytest.mark.parametrize("historical", [False, True])
def test_reviewed_retirement_uses_current_coordination_not_historical_ownership(
    divergent_lane, monkeypatch, lease_state, reacquired, historical
):
    repo, lane = divergent_lane
    initial = _derive(repo)["receipt"]
    original = operation.load_operation(repo, initial["path"], initial["sha256"])
    operation.revoke_operation_lease(repo, original)
    if lease_state != "missing":
        acquire_lease(
            state_database(repo),
            lease=exact_lease(
                branch="work/abandon",
                holder_ref="agent:test:case:former",
                ttl_seconds=-1 if lease_state == "expired" else 86_400,
            ),
        )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:cleanup")
    if historical:
        git(lane, "reset", "--hard", git(repo, "rev-list", "--max-parents=0", "HEAD"))
    else:
        git(repo, "reset", "--hard", git(lane, "rev-parse", "HEAD"))
    assert install_fixture_hook_runtime(repo)["current"]
    target = lane / "reviewed.txt"
    target.write_text("adjudicated residual\n")
    admin = Path(git(lane, "rev-parse", "--absolute-git-dir"))
    before = (git(repo, "show-ref"), (admin / "index").read_bytes(), target.read_bytes())
    result = run_ethos_raw(
        "lane",
        "retire",
        "abandon",
        "--branch",
        "work/abandon",
        "--reason-code",
        "absorbed-content",
        "--reason",
        "current owner covers these bytes",
        "--review-content",
        "--json",
        cwd=repo,
    )
    report = json.loads(result.stdout)
    if lease_state == "valid":
        assert report["required_gaps"] == ["foreign_work_lane_retire_authority_required"]
    else:
        assert report["verdict"] == "pass", report["required_gaps"]
        receipt = report["data"]["receipt"]
        request = operation.load_operation(repo, receipt["path"], receipt["sha256"])
        assert request.lease_state == lease_state
        if reacquired:
            if lease_state == "expired":
                operation.revoke_operation_lease(repo, request)
            acquire_lease(
                state_database(repo),
                lease=exact_lease(branch="work/abandon", holder_ref="agent:test:case:new-owner"),
            )
        result = run_ethos_raw(
            "lane",
            "retire",
            "abandon",
            "--receipt",
            receipt["path"],
            "--receipt-sha256",
            receipt["sha256"],
            "--authorize",
            "--apply",
            "--json",
            cwd=repo,
        )
        report = json.loads(result.stdout)
        if not reacquired:
            assert report["state"] == "retired", report["required_gaps"]
            assert not lane.exists()
            assert not admin.exists()
            assert git(repo, "branch", "--list", "work/abandon") == ""
            assert observe_lease(state_database(repo), "work/abandon").state == "missing"
            return
        assert report["required_gaps"] == ["retirement_operation_state_drift"]
        assert observe_lease(state_database(repo), "work/abandon").state == "valid"
    assert report["verdict"] == "block"
    assert before == (git(repo, "show-ref"), (admin / "index").read_bytes(), target.read_bytes())


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
    rejected = operation.execute_retirement_operation(
        root=repo,
        receipt_path=receipt["path"],
        receipt_sha256=receipt["sha256"],
        authorized=True,
        apply=True,
    )
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

    result = _derive(repo, review_content=True, path=lane if detached else None)

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


@pytest.mark.parametrize("fault", ["symlink", "locked", "reattached", "head"])
def test_retirement_observes_replaced_or_locked_root_as_drift(divergent_lane, fault):
    repo, lane = divergent_lane
    detached = fault in {"reattached", "head"}
    if detached:
        git(lane, "switch", "--detach")
    derived = _derive(repo, review_content=detached, path=lane if detached else None)
    receipt = derived["receipt"]
    request = operation.load_operation(repo, receipt["path"], receipt["sha256"])
    retained = lane
    if fault == "symlink":
        retained = lane.with_name("relocated")
        lane.rename(retained)
        lane.symlink_to(retained, target_is_directory=True)
    elif fault == "locked":
        git(repo, "worktree", "lock", lane.as_posix())
    else:
        git(lane, "switch", "work/abandon") if fault == "reattached" else git(
            lane, "reset", "--soft", "HEAD^"
        )
    before = git(repo, "show-ref")

    assert operation.observe_operation(repo, request).worktree_state == "moved"
    report = _apply_receipt(repo, receipt)

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["retirement_operation_state_drift"]
    assert git(repo, "show-ref") == before
    assert (retained / "abandoned.txt").read_text() == "abandoned\n"
    assert observe_lease(state_database(repo), "work/abandon").state == "valid"


@pytest.mark.parametrize(
    ("drift", "detached"),
    [
        (case, False)
        for case in ("ignored", "process-scan", "git-admission", "actor", "lease", "accepted")
    ]
    + [(case, True) for case in ("ignored", "process-scan", "actor", "accepted")],
)
def test_retirement_rechecks_after_native_worktree_observation(
    divergent_lane, monkeypatch, drift, detached
):
    repo, lane = divergent_lane
    if detached:
        git(lane, "switch", "--detach")
    (repo / ".git/info").mkdir(exist_ok=True)
    (repo / ".git/info/exclude").write_text("residual.txt\n")
    derived = _derive(repo, review_content=True, path=lane if detached else None)
    assert derived["verdict"] == "pass", derived
    receipt = derived["receipt"]
    assert isinstance(receipt, dict)
    assert isinstance(receipt["path"], str)
    assert isinstance(receipt["sha256"], str)
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
        elif drift == "ignored":
            (lane / "residual.txt").write_text("new unreviewed ignored data\n")
        elif drift == "actor":
            monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:foreign")
        elif drift == "lease":
            operation.revoke_operation_lease(repo, request)
        else:
            git(repo, "update-ref", "refs/heads/dev", request.head, request.accepted_head)
        return record

    monkeypatch.setattr(worktree_effects, "worktree_record", observe_then_drift)
    result = _apply_receipt(repo, receipt)

    assert lane.is_dir(), result
    assert (lane / "abandoned.txt").read_bytes() == original_bytes
    assert git(repo, "rev-parse", "refs/heads/work/abandon") == request.head
    assert result["verdict"] == "block", result
    assert result["required_gaps"] == [
        "retirement_content_drift"
        if drift in {"ignored", "process-scan", "git-admission"}
        else "foreign_work_lane_retire_authority_required"
        if drift == "actor"
        else "retirement_operation_state_drift"
    ]
    if drift in {"ignored", "process-scan", "git-admission"}:
        assert (lane / "residual.txt").read_text() == "new unreviewed ignored data\n"


@pytest.mark.parametrize(
    ("fault", "gap"),
    [
        ("branch", "lane_abandonment_branch_invalid"),
        ("missing", "lane_abandonment_coordinates_unavailable"),
        ("control", "retirement_control_root_unavailable"),
        ("absorbed", "lane_abandonment_divergence_required"),
        ("descendant", "lane_abandonment_divergence_required"),
        ("ambiguous", "lane_abandonment_worktree_ambiguous"),
        ("dirty", "lane_abandonment_worktree_not_clean"),
        ("lease", "work_lane_lease_missing"),
        ("actor", "invocation_actor_missing"),
        ("foreign", "foreign_work_lane_retire_authority_required"),
        ("code", "lane_abandonment_reason_invalid"),
        ("reason", "lane_abandonment_reason_invalid"),
        ("mode", "lane_retirement_receipt_mode_invalid"),
    ],
)
def test_abandonment_rejects_invalid_current_facts_without_effects(
    divergent_lane, monkeypatch, fault, gap
):
    repo, lane = divergent_lane
    valid = _derive(repo)
    assert valid["state"] == "derived", valid
    receipt = valid["receipt"]
    request = operation.load_operation(repo, receipt["path"], receipt["sha256"])
    arguments = {}
    if fault in {"branch", "missing"}:
        arguments["branch"] = "dev" if fault == "branch" else "work/missing"
    elif fault == "control":
        git(repo, "switch", "-c", "other")
    elif fault in {"absorbed", "descendant"}:
        target = (
            request.head if fault == "absorbed" else git(repo, "merge-base", "dev", request.head)
        )
        git(repo, "reset", "--hard", target)
    elif fault == "ambiguous":
        status = abandonment.workspace_status(repo)
        worktrees = status["worktrees"]
        assert isinstance(worktrees, list)
        row = next(row for row in worktrees if row["branch"] == "work/abandon")
        worktrees.append(dict(row))
        monkeypatch.setattr(abandonment, "workspace_status", lambda _root: status)
    elif fault == "dirty":
        (lane / "abandoned.txt").write_text("preserve uncommitted work\n", encoding="utf-8")
    elif fault == "lease":
        operation.revoke_operation_lease(repo, request)
    elif fault in {"actor", "foreign"}:
        monkeypatch.setenv("ETHOS_ACTOR", "" if fault == "actor" else "agent:test:case:foreign")
    elif fault in {"code", "reason"}:
        arguments["reason_code" if fault == "code" else "reason"] = (
            "INVALID" if fault == "code" else " "
        )
    else:
        receipt = operation.persist_operation(repo, request.model_copy(update={"mode": "landed"}))

    def state():
        return (
            git(repo, "show-ref"),
            git(repo, "worktree", "list", "--porcelain"),
            (lane / "abandoned.txt").read_bytes(),
            observe_lease(state_database(repo), "work/abandon"),
            tuple(sorted(operation.operation_store(repo).iterdir())),
        )

    before = state()
    receipt_path, receipt_sha256 = receipt["path"], receipt["sha256"]
    assert isinstance(receipt_path, str)
    assert isinstance(receipt_sha256, str)
    report = (
        operation.execute_retirement_operation(
            expected_mode="abandon",
            root=repo,
            receipt_path=receipt_path,
            receipt_sha256=receipt_sha256,
            apply=True,
            authorized=True,
        )
        if fault == "mode"
        else _derive(
            repo,
            branch=arguments.get("branch", "work/abandon"),
            reason_code=arguments.get("reason_code", "superseded-experiment"),
            reason=arguments.get("reason", "discard divergent experiment"),
        )
    )
    assert report["state"] == "blocked"
    assert report["required_gaps"] == [gap]
    assert state() == before


def test_abandonment_apply_requires_authorization_before_loading_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        operation,
        "load_operation",
        lambda *_args: pytest.fail("unauthorized abandonment must not load or execute"),
    )

    report = operation.execute_retirement_operation(
        root=tmp_path,
        receipt_path="/receipt",
        receipt_sha256="sha256:" + "d" * 64,
        apply=True,
        authorized=False,
    )

    assert report["state"] == "blocked"
    assert report["required_gaps"] == ["authorization_required"]


@pytest.mark.parametrize("interrupted", ["", "first", "shared", ".git"])
@pytest.mark.parametrize("detached", [False, True])
def test_reviewed_disposal_preserves_shared_files_and_recovers_before_deregistration(
    divergent_lane, monkeypatch, interrupted, detached
):
    repo, lane = divergent_lane
    if detached:
        sibling = repo.parent / "same-head-sibling"
        git(lane, "switch", "--detach")
        git(repo, "worktree", "add", "--detach", str(sibling), git(lane, "rev-parse", "HEAD"))
    refs_before = git(repo, "show-ref")
    generated = lane / "generated"
    generated.mkdir()
    external = repo.parent / "shared-source"
    external.write_text("shared supply bytes\n")
    external.chmod(0o400)
    os.link(external, generated / "shared")
    os.link(external, generated / "shared-again")
    (generated / "link").symlink_to(external)
    (generated / "first").write_text("reviewed disposable bytes\n")
    generated.chmod(0o500)
    before = (external.read_bytes(), external.stat().st_mode, external.stat().st_ino)
    derived = _derive(repo, review_content=True, path=lane if detached else None)
    assert derived["verdict"] == "pass", derived
    receipt = derived["receipt"]
    admin = Path(git(lane, "rev-parse", "--absolute-git-dir"))
    original_index = (admin / "index").read_bytes()
    native_unlink = os.unlink

    def stop_after_first(path, *args, **kwargs):
        native_unlink(path, *args, **kwargs)
        if Path(path).name == interrupted:
            message = "injected removal interruption"
            raise OSError(message)

    if interrupted:
        monkeypatch.setattr(content.os, "unlink", stop_after_first)
    result = _apply_receipt(repo, receipt)
    if interrupted:
        assert result["verdict"] == "block", result
        assert not (generated / "first").exists(), result
        assert (admin / "index").read_bytes() == original_index
        assert (lane / ".git").is_file() == (interrupted != ".git")
        assert "ethos lane retire recover" in str(result["next_action"])
        monkeypatch.setattr(content.os, "unlink", native_unlink)
        result = _apply_receipt(repo, receipt)
    assert result["state"] == "retired", result
    assert not lane.exists()
    assert not admin.exists()
    if detached:
        assert git(repo, "show-ref") == refs_before
        assert (sibling / "abandoned.txt").read_text() == "abandoned\n"
    else:
        assert git(repo, "branch", "--list", "work/abandon") == ""
    assert observe_lease(state_database(repo), "work/abandon").state == (
        "valid" if detached else "missing"
    )
    assert (external.read_bytes(), external.stat().st_mode, external.stat().st_ino) == before
    _assert_terminal_recovery(repo, lane, receipt, detached)


def _assert_terminal_recovery(repo, lane, receipt, detached):
    """Recognize completion but never admit replacement content at a retired path."""
    assert _apply_receipt(repo, receipt)["state"] == "retired"
    if detached:
        lane.mkdir()
        (lane / "replacement").write_text("new unreviewed bytes\n")
        assert _apply_receipt(repo, receipt)["verdict"] == "block"
        assert (lane / "replacement").read_text() == "new unreviewed bytes\n"


def _change_reviewed_survivor(
    repo: Path, nested: Path, survivor: Path, index: Path, drift: str
) -> Path:
    """Create one independently selected filesystem drift at either execution boundary."""
    if drift == "new":
        survivor = nested / "new"
        survivor.write_text("unreviewed new bytes\n")
    elif drift == "replacement":
        survivor.rename(repo.parent / "retained-file")
        survivor.write_text("reviewed surviving bytes\n")
    elif drift in {"bytes", "alias-bytes"}:
        survivor.write_text("unreviewed changed bytes\n")
    elif drift == "parent-link":
        nested.rename(repo.parent / "retained-directory")
        nested.symlink_to(repo.parent / "retained-directory", target_is_directory=True)
    elif drift == "alias-count":
        os.link(survivor, repo.parent / "unreviewed-alias")
    elif drift == "index":
        index.write_bytes(index.read_bytes() + b"changed after partial deletion")
    return survivor


@pytest.mark.parametrize("timing", ["recovery", "during"])
@pytest.mark.parametrize(
    "drift", ["new", "replacement", "bytes", "parent-link", "alias-bytes", "alias-count", "index"]
)
def test_partial_reviewed_disposal_preserves_unreviewed_survivors(
    divergent_lane, monkeypatch, drift, timing
):
    repo, lane = divergent_lane
    nested = lane / "nested"
    nested.mkdir()
    (nested / "first").write_text("reviewed disposable bytes\n")
    survivor = nested / "survivor"
    survivor.write_text("reviewed surviving bytes\n")
    if drift.startswith("alias-"):
        os.link(survivor, nested / "second")
    index = Path(git(lane, "rev-parse", "--git-path", "index"))
    derived = _derive(repo, review_content=True)
    receipt = derived["receipt"]
    native_unlink = os.unlink

    def interrupt(path, *args, **kwargs):
        nonlocal survivor
        native_unlink(path, *args, **kwargs)
        if Path(path).name == "first":
            if timing == "during":
                survivor = _change_reviewed_survivor(repo, nested, survivor, index, drift)
                return
            message = "injected removal interruption"
            raise OSError(message)

    monkeypatch.setattr(content.os, "unlink", interrupt)
    partial = _apply_receipt(repo, receipt)
    assert partial["verdict"] == "block", partial
    assert not (nested / "first").exists(), partial
    monkeypatch.setattr(content.os, "unlink", native_unlink)
    if timing == "recovery":
        survivor = _change_reviewed_survivor(repo, nested, survivor, index, drift)
    before = (git(repo, "show-ref"), survivor.read_bytes(), survivor.stat().st_ino)
    recovered = _apply_receipt(repo, receipt)
    assert recovered["verdict"] == "block", recovered
    assert recovered["required_gaps"] == ["retirement_content_drift"], recovered
    assert before == (git(repo, "show-ref"), survivor.read_bytes(), survivor.stat().st_ino)
    assert (lane / ".git").is_file()
    assert observe_lease(state_database(repo), "work/abandon").state == "valid"


@pytest.mark.parametrize("drift", ["bytes", "replacement", "symlink", "root"])
@pytest.mark.parametrize("detached", [False, True])
def test_reviewed_absent_recovery_preserves_changed_index_and_recreated_content(
    divergent_lane, drift, detached
):
    repo, lane = divergent_lane
    if detached:
        git(lane, "switch", "--detach")
    derived = _derive(repo, review_content=True, path=lane if detached else None)
    assert derived["verdict"] == "pass", derived
    receipt = derived["receipt"]
    admin = Path(git(lane, "rev-parse", "--absolute-git-dir"))
    index = admin / "index"
    shutil.rmtree(lane)
    if drift == "bytes":
        index.write_bytes(b"unreviewed index bytes")
    elif drift in {"replacement", "symlink"}:
        retained = repo.parent / "retained-index"
        index.rename(retained)
        if drift == "replacement":
            index.write_bytes(retained.read_bytes())
        else:
            index.symlink_to(retained)
    else:
        lane.mkdir()
        (lane / "new.txt").write_text("unreviewed new root\n")

    def index_state():
        observed = index.lstat()
        return (
            observed.st_dev,
            observed.st_ino,
            observed.st_mode,
            observed.st_uid,
            observed.st_size,
            observed.st_mtime_ns,
            observed.st_ctime_ns,
            index.read_bytes(),
        )

    before = (git(repo, "show-ref"), index_state())

    recovered = _apply_receipt(repo, receipt)

    assert recovered["verdict"] == "block", recovered
    assert recovered["required_gaps"], recovered
    assert admin.is_dir()
    assert before == (git(repo, "show-ref"), index_state())
    assert observe_lease(state_database(repo), "work/abandon").state == "valid"
    if drift == "root":
        assert (lane / "new.txt").read_text() == "unreviewed new root\n"


@pytest.mark.parametrize("content_absent", [False, True])
@pytest.mark.parametrize("review_content", [False, True])
def test_real_abandonment_recovers_after_worktree_removal_and_git_spawn_failure(
    divergent_lane, monkeypatch, content_absent, review_content
):
    repo, lane = divergent_lane
    head = git(lane, "rev-parse", "HEAD")
    derived = _derive(repo, review_content=review_content)
    assert derived["state"] == "derived", derived
    assert "ethos lane retire abandon" in derived["next_action"]
    receipt = derived["receipt"]
    request = operation.load_operation(repo, receipt["path"], receipt["sha256"])
    assert request.mode == "abandon"
    assert request.head == head
    assert request.tree == git(lane, "rev-parse", "HEAD^{tree}")
    admin = Path(git(lane, "rev-parse", "--absolute-git-dir"))
    if content_absent:
        index = (admin / "index").read_bytes()
        shutil.rmtree(lane)
        assert (admin / "index").read_bytes() == index
    written = []
    persist = operation.persist_progress

    def record(root, request, progress):
        written.append(progress.completed_effects)
        return persist(root, request, progress)

    monkeypatch.setattr(operation, "persist_progress", record)
    original = operation.delete_operation_ref
    failure = GitExecutionError(
        "git_process_spawn_failed",
        reason="process_creation_failed",
        command=("/native/git", "update-ref", "--stdin"),
        cwd=repo.as_posix(),
        cause="resource temporarily unavailable",
    )
    monkeypatch.setattr(
        operation, "delete_operation_ref", lambda *_args: (_ for _ in ()).throw(failure)
    )

    partial = operation.execute_retirement_operation(
        root=repo,
        receipt_path=str(receipt["path"]),
        receipt_sha256=str(receipt["sha256"]),
        apply=True,
        authorized=True,
    )

    assert written == [(), ("remove_worktree",), ("remove_worktree",)]
    assert partial["required_gaps"] == ["git_process_spawn_failed"]
    assert partial["process_failure"] == failure.evidence()
    assert "ethos lane retire recover" in str(partial["next_action"])
    assert partial["state"] == "partial_transition"
    assert partial["completed_effects"] == ["remove_worktree"]
    assert partial["remaining_effects"] == ["delete_ref", "revoke_lease"]
    assert not lane.exists()
    assert not admin.exists()
    assert git(repo, "rev-parse", "work/abandon") == head
    assert observe_lease(state_database(repo), "work/abandon").state == "valid"

    monkeypatch.setattr(operation, "delete_operation_ref", original)
    monkeypatch.setattr(
        operation,
        "remove_operation_worktree",
        lambda *_a: pytest.fail("recovery replays worktree removal"),
    )
    for _ in range(2):
        recovered = _apply_receipt(repo, receipt)
        assert recovered["state"] == "retired", recovered
        monkeypatch.setattr(
            operation,
            "delete_operation_ref",
            lambda *_a: pytest.fail("terminal recovery replays deletion"),
        )
        terminal = recovered["terminal_receipt"]
        assert isinstance(terminal, dict)
        payload = json.loads(Path(terminal["path"]).read_text())
        assert payload["kind"] == "lane-retirement-receipt"
        assert payload["request"] == request.model_dump(mode="json")
        assert payload["progress"]["completed_effects"] == [
            "remove_worktree",
            "delete_ref",
            "revoke_lease",
        ]
        assert payload["progress"]["remaining_effects"] == []
    operation.revoke_operation_lease(repo, request)
    assert git(repo, "branch", "--list", "work/abandon") == ""
    assert observe_lease(state_database(repo), "work/abandon").state == "missing"
