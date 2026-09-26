"""Verify reviewed retirement preserves content and recovers exact effects."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest

import ethos.adapters.mutation.lane_retirement.content as content
import ethos.adapters.mutation.lane_retirement.operation as operation
from ethos.adapters.repo.git import GitExecutionError
from ethos.adapters.store.state.lease.projection import observe_lease
from ethos.adapters.store.state.schema import state_database
from tests.support.governed_repository import git
from tests.support.lane_scenarios import apply_retirement_receipt
from tests.support.lane_scenarios import derive_abandonment


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
    derived = derive_abandonment(repo, review_content=True, path=lane if detached else None)
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
    result = apply_retirement_receipt(repo, receipt)
    if interrupted:
        assert result["verdict"] == "block", result
        assert not (generated / "first").exists(), result
        assert (admin / "index").read_bytes() == original_index
        assert (lane / ".git").is_file() == (interrupted != ".git")
        assert "ethos lane retire recover" in str(result["next_action"])
        monkeypatch.setattr(content.os, "unlink", native_unlink)
        result = apply_retirement_receipt(repo, receipt)
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
    assert apply_retirement_receipt(repo, receipt)["state"] == "retired"
    if detached:
        lane.mkdir()
        (lane / "replacement").write_text("new unreviewed bytes\n")
        assert apply_retirement_receipt(repo, receipt)["verdict"] == "block"
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
    derived = derive_abandonment(repo, review_content=True)
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
    partial = apply_retirement_receipt(repo, receipt)
    assert partial["verdict"] == "block", partial
    assert not (nested / "first").exists(), partial
    monkeypatch.setattr(content.os, "unlink", native_unlink)
    if timing == "recovery":
        survivor = _change_reviewed_survivor(repo, nested, survivor, index, drift)
    before = (git(repo, "show-ref"), survivor.read_bytes(), survivor.stat().st_ino)
    recovered = apply_retirement_receipt(repo, receipt)
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
    derived = derive_abandonment(repo, review_content=True, path=lane if detached else None)
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

    recovered = apply_retirement_receipt(repo, receipt)

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
    derived = derive_abandonment(repo, review_content=review_content)
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

    partial = apply_retirement_receipt(repo, receipt)

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
        recovered = apply_retirement_receipt(repo, receipt)
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
