"""Public merge effects bind native state and preserve work under real hooks."""

import base64
import json
import shlex
import sqlite3
from contextlib import closing
from pathlib import Path
from unittest.mock import Mock

import pytest
from filelock import FileLock

import ethos.adapters.admission.current.resolution as resolution_owner
import ethos.adapters.mutation.lane_lifecycle.merge as merge_admission
import ethos.adapters.repo.merge.effect as merge_effect
import ethos.adapters.repo.runtime.binding as runtime_binding_owner
from ethos.adapters.repo.merge.observation import observe_merge
from ethos.adapters.repo.merge.recovery import preserve_merge
from ethos.adapters.store.state.schema import state_database
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.openspec_lifecycle import killed_merge_effect
from tests.support.openspec_lifecycle import native_merge_fixture
from tests.support.runtime_scenarios import git_process


def _preview(work: Path, mode: str = "inspect") -> dict:
    """Read the public exact-state preview without performing an effect."""
    report = run_ethos(
        "lane", "refresh-base", "--strategy", "merge", "--mode", mode, "--json", cwd=work
    )
    assert report["verdict"] == "pass", json.dumps(report, indent=2)
    return report


def _apply(work: Path, preview: dict) -> dict:
    """Execute only the public next action returned by the owning command."""
    return run_ethos(*shlex.split(preview["next_action"])[1:], cwd=work)


def test_public_merge_abort_preserves_conflict_edits_and_native_state(tmp_path):
    work = native_merge_fixture(tmp_path)
    before = git(work, "rev-parse", "HEAD")
    (work / "README.md").write_text("# Valuable partial resolution\n")
    (work / "personal.txt").write_bytes(b"untracked unchanged\n")
    preview = _preview(work, "abort")
    assert preview["verdict"] == "pass", preview
    assert "--expect-state" in preview["next_action"]
    result = _apply(work, preview)
    assert result["verdict"] == "pass", result
    assert result["data"]["state"] == "merge_aborted"
    assert git(work, "rev-parse", "HEAD") == before
    assert (work / "personal.txt").read_bytes() == b"untracked unchanged\n"
    assert not Path(git(work, "rev-parse", "--git-path", "MERGE_HEAD")).exists()
    recovery = result["data"]["recovery"]
    payload = json.loads(Path(recovery["path"]).read_text())
    assert payload["observation"]["conflicts"] == ["README.md"]
    assert payload["files"]["README.md"]["content"]
    again = _apply(work, preview)
    assert again["verdict"] == "pass", again
    assert again["data"]["state"] == "merge_aborted"


def test_public_merge_continue_preserves_both_parents_and_untracked_work(tmp_path, monkeypatch):
    work = native_merge_fixture(tmp_path)
    ours, theirs = git(work, "rev-parse", "HEAD"), git(work, "rev-parse", "MERGE_HEAD")
    (work / "README.md").write_text("# Accepted combined resolution\n")
    git(work, "add", "README.md")
    (work / "personal.txt").write_text("not part of commit\n")
    official = Mock(wraps=merge_admission.openspec_governance_report)
    monkeypatch.setattr(merge_admission, "openspec_governance_report", official)
    monkeypatch.setattr(resolution_owner, "openspec_governance_report", official)
    preview = _preview(work, "continue")
    assert preview["verdict"] == "pass", preview
    result = _apply(work, preview)
    assert result["verdict"] == "pass", result
    head, *parents = git(work, "rev-list", "--parents", "-n", "1", "HEAD").split()
    assert parents == [ours, theirs]
    assert result["data"]["head"] == head
    assert git(work, "show", "HEAD:README.md") == "# Accepted combined resolution"
    assert (work / "personal.txt").read_text() == "not part of commit\n"
    assert _apply(work, preview)["verdict"] == "pass"
    assert official.call_count == 2  # Preview and effect each observe once; replay has no effect.


def test_public_merge_preparation_is_explicit_and_conflicts_remain_recoverable(tmp_path):
    work = native_merge_fixture(tmp_path, pending=False)
    before = git(work, "rev-parse", "HEAD")
    preview = _preview(work, "start")
    assert preview["verdict"] == "pass", preview
    result = _apply(work, preview)
    assert result["data"]["state"] == "merge_pending", result
    assert git(work, "rev-parse", "HEAD") == before
    assert git(work, "diff", "--name-only", "--diff-filter=U") == "README.md"
    assert _preview(work, "abort")["verdict"] == "pass"


@pytest.mark.parametrize("fault", ["content", "index", "holder"])
def test_public_merge_apply_rejects_changed_observation(tmp_path, monkeypatch, fault):
    work = native_merge_fixture(tmp_path)
    preview = _preview(work, "abort")
    before = git(work, "rev-parse", "HEAD")
    if fault == "holder":
        monkeypatch.setenv("ETHOS_ACTOR", "agent:other")
    else:
        (work / "README.md").write_text("# Later resolution\n")
        if fault == "index":
            git(work, "add", "README.md")
    with pytest.raises(AssertionError, match=r"lease_holder_mismatch|merge_state_stale"):
        _apply(work, preview)
    assert git(work, "rev-parse", "HEAD") == before
    assert git(work, "rev-parse", "MERGE_HEAD")


def test_completed_abort_does_not_recognize_a_new_merge_at_same_head(tmp_path):
    """Equal branch HEAD alone does not prove the old operation is still current."""
    work = native_merge_fixture(tmp_path)
    preview = _preview(work, "abort")
    _apply(work, preview)
    incoming = git(work, "rev-parse", "candidate/dev")
    assert git_process(work, "merge", "--no-ff", "--no-commit", incoming).returncode == 1
    with pytest.raises(AssertionError, match="merge_result_stale"):
        _apply(work, preview)
    assert git(work, "rev-parse", "MERGE_HEAD") == incoming


@pytest.mark.parametrize("mode", ["abort", "continue"])
def test_lost_result_ack_is_recognized_without_repeating_effect(tmp_path, monkeypatch, mode):
    """The prepared observation bridges a lost result write after the native effect."""
    work = native_merge_fixture(tmp_path)
    if mode == "continue":
        (work / "README.md").write_text("# Resolved before interruption\n")
        git(work, "add", "README.md")
    preview = _preview(work, mode)
    record = merge_effect.record_attestations

    def lost_result(root, attestations):
        if any(item.predicate == "effect:git-merge" for item in attestations):
            message = "lost result acknowledgement"
            raise OSError(message)
        return record(root, attestations)

    monkeypatch.setattr(merge_effect, "record_attestations", lost_result)
    with pytest.raises(AssertionError, match="lost result acknowledgement"):
        _apply(work, preview)
    after = git(work, "rev-parse", "HEAD")
    monkeypatch.setattr(merge_effect, "record_attestations", record)
    recovered = _apply(work, preview)
    assert recovered["verdict"] == "pass", recovered
    assert git(work, "rev-parse", "HEAD") == after


def test_merge_start_cannot_overwrite_ignored_local_content(tmp_path):
    """An ignored path is not permission for Git's merge checkout to overwrite it."""
    work = native_merge_fixture(tmp_path, pending=False)
    candidate = next(
        Path(row.split(" ", 1)[1])
        for row in git(work, "worktree", "list", "--porcelain").splitlines()
        if row.startswith("worktree ")
        and Path(row.split(" ", 1)[1]).name != "work"
        and git(Path(row.split(" ", 1)[1]), "branch", "--show-current") == "candidate/dev"
    )
    (candidate / "personal-cache.bin").write_bytes(b"incoming tracked data\n")
    commit_fixture(candidate, "feat: add incoming tracked data")
    exclude = Path(git(work, "rev-parse", "--path-format=absolute", "--git-path", "info/exclude"))
    exclude.parent.mkdir(exist_ok=True)
    with exclude.open("a") as stream:
        stream.write("\npersonal-cache.bin\n")
    local = work / "personal-cache.bin"
    local.write_bytes(b"valuable ignored local data\n")
    preview = run_ethos(
        "lane", "refresh-base", "--strategy", "merge", "--mode", "start", "--json", cwd=work
    )
    assert preview["required_gaps"] == ["merge_ignored_content_collision:personal-cache.bin"]
    assert local.read_bytes() == b"valuable ignored local data\n"


def test_default_refresh_routes_pending_merge_to_its_owner(tmp_path):
    """A pending native merge cannot be treated as an ordinary dirty rebase."""
    work = native_merge_fixture(tmp_path)
    report = run_ethos("lane", "refresh-base", "--json", cwd=work)
    assert "merge_in_progress" in report["required_gaps"], report
    assert report["next_action"].startswith("ethos lane refresh-base --strategy merge")


def test_abort_does_not_depend_on_an_existing_candidate_ref(tmp_path):
    """Rollback does not integrate the candidate and must not require its existence."""
    work = native_merge_fixture(tmp_path)
    git(work, "-c", "core.hooksPath=/dev/null", "update-ref", "-d", "refs/heads/candidate/dev")
    before = git(work, "rev-parse", "HEAD")
    result = _apply(work, _preview(work, "abort"))
    assert result["data"]["state"] == "merge_aborted"
    assert git(work, "rev-parse", "HEAD") == before


@pytest.mark.parametrize("boundary", ["continue", "abort"])
def test_real_kill_recovers_without_repeating_native_effect(tmp_path, boundary):
    """A dead process releases the lock; exact evidence recovers its completed effect."""
    work = native_merge_fixture(tmp_path)
    if boundary == "continue":
        (work / "README.md").write_text("# Resolution before killed effect\n")
        git(work, "add", "README.md")
    preview = _preview(work, boundary)
    killed_merge_effect(work, preview)
    after = git(work, "rev-parse", "HEAD")
    result = _apply(work, preview)
    assert result["verdict"] == "pass", result
    assert git(work, "rev-parse", "HEAD") == after


def test_abort_material_reconstructs_conflict_index_and_unique_staged_bytes(tmp_path):
    """Recovery contains executable bytes, not merely a receipt that says preserved."""
    work = native_merge_fixture(tmp_path)
    (work / "valuable.sh").write_bytes(b"#!/bin/sh\necho preserved\n")
    (work / "valuable.sh").chmod(0o755)
    git(work, "add", "valuable.sh")
    (work / "valuable.sh").write_bytes(b"#!/bin/sh\necho unstaged\n")
    stages = git(work, "ls-files", "--stage")
    preview = _preview(work, "abort")
    result = run_ethos_blocked(*shlex.split(preview["next_action"])[1:], cwd=work)
    # Native abort refuses staged + unstaged divergence; it must expose preservation.
    assert result["verdict"] == "unknown"
    saved = result["data"]["process_failure"]["observation"]["recovery"]
    recovery = json.loads(Path(saved["path"]).read_text())
    for oid, encoded in recovery["stage_blobs"].items():
        decoded = base64.b64decode(encoded)
        assert merge_effect.run_git(work, "cat-file", "blob", oid, text=False).stdout == decoded
    for relative, item in recovery["files"].items():
        target = work / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if item["kind"] == "file":
            target.write_bytes(base64.b64decode(item["content"]))
            target.chmod(item["mode"])
    for name, encoded in recovery["metadata"].items():
        native = Path(git(work, "rev-parse", "--path-format=absolute", "--git-path", name))
        native.write_bytes(base64.b64decode(encoded))
    assert git(work, "ls-files", "--stage") == stages
    assert git(work, "show", ":valuable.sh") == "#!/bin/sh\necho preserved"
    assert (work / "valuable.sh").read_bytes() == b"#!/bin/sh\necho unstaged\n"
    assert (work / "valuable.sh").stat().st_mode & 0o777 == 0o755


@pytest.mark.parametrize("fault", ["expired", "generation", "busy", "runtime"])
def test_merge_apply_requires_fresh_lease_runtime_and_exclusive_effect(tmp_path, fault):
    """Exact prior permission cannot survive an authority or execution-boundary change."""
    work = native_merge_fixture(tmp_path)
    preview = _preview(work, "abort")
    before = git(work, "rev-parse", "HEAD")
    lock = FileLock(str(merge_effect.git_path(work, "ethos-merge.lock")), timeout=0)
    if fault in {"expired", "generation"}:
        with closing(sqlite3.connect(state_database(work))) as db, db:
            statement = (
                "update leases set expires_at = '2000-01-01T00:00:00+00:00'"
                if fault == "expired"
                else "update leases set generation = generation + 1"
            )
            db.execute(statement)
    elif fault == "runtime":
        common = Path(git(work, "rev-parse", "--path-format=absolute", "--git-common-dir"))
        (common / "ethos/runtime/CURRENT").write_text("0" * 64 + "\n")
    else:
        lock.acquire()
    try:
        report = run_ethos_blocked(*shlex.split(preview["next_action"])[1:], cwd=work)
    finally:
        if lock.is_locked:
            lock.release()
    assert report["required_gaps"], report
    assert git(work, "rev-parse", "HEAD") == before
    assert git(work, "rev-parse", "MERGE_HEAD")


def test_merge_continue_cannot_claim_incoming_task_completion(tmp_path):
    """A selected local Change does not own edits to the other parent's task state."""
    work = native_merge_fixture(tmp_path)
    (work / "README.md").write_text("# Local resolution\n")
    incoming = work / "openspec/changes/static-delivery/tasks.md"
    incoming.write_text(incoming.read_text().replace("[ ]", "[x]"))
    git(work, "add", "README.md", str(incoming))
    before = git(work, "rev-parse", "HEAD")
    report = run_ethos(
        "lane", "refresh-base", "--strategy", "merge", "--mode", "continue", "--json", cwd=work
    )
    assert report["verdict"] == "block", report
    assert any("incoming_change_modified" in gap for gap in report["required_gaps"])
    assert git(work, "rev-parse", "HEAD") == before


@pytest.mark.parametrize("case", ["absent", "symlink", "directory", "stale"])
def test_recovery_inventory_preserves_kinds_and_rejects_unsafe_or_stale_bytes(tmp_path, case):
    """Destructive preimages distinguish absence, link payload and unsupported file kinds."""
    work = native_merge_fixture(tmp_path)
    observed = observe_merge(work)
    path = work / "README.md"
    if case == "stale":
        path.write_text("changed after observation\n")
    else:
        path.unlink()
        if case == "symlink":
            path.symlink_to("unread-target")
        elif case == "directory":
            path.mkdir()
        observed = observe_merge(work)
    if case in {"directory", "stale"}:
        with pytest.raises(ValueError, match=r"merge_recovery_content_unsafe|merge_state_stale"):
            preserve_merge(work, observed)
    else:
        artifact = preserve_merge(work, observed)
        data = json.loads(Path(artifact["path"]).read_text())
        assert data["files"]["README.md"]["kind"] == ("absent" if case == "absent" else "symlink")
        assert preserve_merge(work, observed) == artifact


@pytest.mark.parametrize(
    "case", ["unresolved", "unstaged", "autostash", "competing", "multi-parent"]
)
def test_native_unsupported_state_rejects_continue_without_side_effect(tmp_path, case):
    """Unsupported native protocols are explicit boundaries, not optimistic execution."""
    work = native_merge_fixture(tmp_path)
    if case == "unstaged":
        (work / "README.md").write_text("staged resolution\n")
        git(work, "add", "README.md")
        (work / "README.md").write_text("later unaccepted resolution\n")
    elif case == "autostash":
        merge_effect.git_path(work, "MERGE_AUTOSTASH").write_text(git(work, "rev-parse", "HEAD"))
    elif case == "competing":
        merge_effect.git_path(work, "CHERRY_PICK_HEAD").write_text(git(work, "rev-parse", "HEAD"))
    elif case == "multi-parent":
        parent_file = merge_effect.git_path(work, "MERGE_HEAD")
        parent_file.write_text(parent_file.read_text() + git(work, "rev-parse", "HEAD") + "\n")
    before = git(work, "rev-parse", "HEAD"), git(work, "ls-files", "--stage")
    report = run_ethos(
        "lane", "refresh-base", "--strategy", "merge", "--mode", "continue", "--json", cwd=work
    )
    expected = {
        "unresolved": "merge_unresolved_index",
        "unstaged": "merge_unstaged_resolution",
        "autostash": "merge_autostash_recovery_unsupported",
        "competing": "merge_competing_native_operation",
        "multi-parent": "merge_multiple_parents_unsupported",
    }
    assert report["required_gaps"] == [expected[case]], report
    assert (git(work, "rev-parse", "HEAD"), git(work, "ls-files", "--stage")) == before


def test_merge_apply_requires_explicit_exact_request_and_preserves_preview(tmp_path):
    work = native_merge_fixture(tmp_path)
    report = run_ethos_blocked(
        "lane",
        "refresh-base",
        "--strategy",
        "merge",
        "--mode",
        "abort",
        "--apply",
        "--json",
        cwd=work,
    )
    assert report["required_gaps"] == ["authorization_required"]
    report = run_ethos_blocked(
        "lane",
        "refresh-base",
        "--strategy",
        "merge",
        "--mode",
        "abort",
        "--apply",
        "--authorize",
        "--json",
        cwd=work,
    )
    assert report["required_gaps"] == ["merge_exact_request_required"]
    assert "--mode abort" in report["next_action"]
    assert "--apply" not in report["next_action"]
    assert _preview(work, "abort")["verdict"] == "pass"


def test_conflicted_inspection_selects_exact_prewrite_not_a_status_loop(tmp_path):
    work = native_merge_fixture(tmp_path)
    report = run_ethos("lane", "refresh-base", "--strategy", "merge", "--json", cwd=work)
    assert report["required_gaps"] == ["merge_unresolved_index"]
    assert shlex.split(report["next_action"])[:4] == ["ethos", "lane", "prewrite", "README.md"]
    assert report["data"]["observation"]["conflicts"] == ["README.md"]


def test_authority_changed_after_ref_cas_prevents_metadata_cleanup(tmp_path, monkeypatch):
    """An observed ref effect cannot grant the following cleanup current authority."""
    work = native_merge_fixture(tmp_path)
    (work / "README.md").write_text("accepted resolution\n")
    git(work, "add", "README.md")
    preview = _preview(work, "continue")
    before = git(work, "rev-parse", "HEAD")
    execute = merge_effect.execute_git_effect

    def changed_authority(*args, **kwargs):
        result = execute(*args, **kwargs)
        with closing(sqlite3.connect(state_database(work))) as db, db:
            db.execute("update leases set generation = generation + 1")
        return result

    monkeypatch.setattr(merge_effect, "execute_git_effect", changed_authority)
    report = run_ethos_blocked(*shlex.split(preview["next_action"])[1:], cwd=work)
    assert "merge_state_stale" in report["required_gaps"]
    assert git(work, "rev-parse", "HEAD") != before
    assert git(work, "rev-parse", "MERGE_HEAD")


def test_merge_preview_observes_runtime_once_per_admission(tmp_path, monkeypatch):
    """Reuse one observation within admission, never across effect boundaries."""
    work = native_merge_fixture(tmp_path)
    reads = []
    observe = merge_admission.hook_runtime_binding

    def counted(root, **kwargs):
        reads.append(root)
        return observe(root, **kwargs)

    monkeypatch.setattr(merge_admission, "hook_runtime_binding", counted)
    monkeypatch.setattr(runtime_binding_owner, "hook_runtime_binding", counted)
    assert _preview(work, "abort")["verdict"] == "pass"
    assert reads == [work]
