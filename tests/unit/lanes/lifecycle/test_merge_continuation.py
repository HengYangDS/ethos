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
from ethos.adapters.repo.merge.observation import observe_merge
from ethos.adapters.repo.merge.recovery import preserve_merge
from ethos.adapters.store.state.schema import state_database
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.openspec_lifecycle import apply_merge
from tests.support.openspec_lifecycle import killed_merge_effect
from tests.support.openspec_lifecycle import native_merge_fixture
from tests.support.openspec_lifecycle import preview_merge
from tests.support.runtime_scenarios import git_process


def test_public_merge_abort_preserves_conflict_edits_and_native_state(tmp_path):
    work = native_merge_fixture(tmp_path)
    before = git(work, "rev-parse", "HEAD")
    (work / "README.md").write_text("# Valuable partial resolution\n")
    (work / "personal.txt").write_bytes(b"untracked unchanged\n")
    preview = preview_merge(work, "abort")
    assert preview["verdict"] == "pass", preview
    assert "--expect-state" in preview["next_action"]
    result = apply_merge(work, preview)
    assert result["verdict"] == "pass", result
    assert result["data"]["state"] == "merge_aborted"
    assert git(work, "rev-parse", "HEAD") == before
    assert (work / "personal.txt").read_bytes() == b"untracked unchanged\n"
    assert not Path(git(work, "rev-parse", "--git-path", "MERGE_HEAD")).exists()
    recovery = result["data"]["recovery"]
    payload = json.loads(Path(recovery["path"]).read_text())
    assert payload["observation"]["conflicts"] == ["README.md"]
    assert payload["files"]["README.md"]["content"]
    again = apply_merge(work, preview)
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
    preview = preview_merge(work, "continue")
    assert preview["verdict"] == "pass", preview
    result = apply_merge(work, preview)
    assert result["verdict"] == "pass", result
    head, *parents = git(work, "rev-list", "--parents", "-n", "1", "HEAD").split()
    assert parents == [ours, theirs]
    assert result["data"]["head"] == head
    assert git(work, "show", "HEAD:README.md") == "# Accepted combined resolution"
    assert (work / "personal.txt").read_text() == "not part of commit\n"
    assert apply_merge(work, preview)["verdict"] == "pass"
    assert official.call_count == 2  # Preview and effect each observe once; replay has no effect.


@pytest.mark.parametrize("movement", ["before-preview", "before-apply"])
def test_public_merge_continuation_uses_pending_parent_when_candidate_advances(tmp_path, movement):
    """Candidate integration is separate from finishing an exact pending native merge."""
    work = native_merge_fixture(tmp_path)
    ours, incoming = git(work, "rev-parse", "HEAD"), git(work, "rev-parse", "MERGE_HEAD")
    (work / "README.md").write_text("# Accepted combined resolution\n")
    git(work, "add", "README.md")
    candidate = tmp_path / "repo-candidate-dev"
    preview = preview_merge(work, "continue") if movement == "before-apply" else None
    (candidate / "later.txt").write_text("Unrelated candidate progress\n")
    advanced = commit_fixture(candidate, "fix: advance candidate independently")
    preview = preview or preview_merge(work, "continue")
    result = apply_merge(work, preview)
    assert result["verdict"] == "pass", result
    head, *parents = git(work, "rev-list", "--parents", "-n", "1", "HEAD").split()
    assert parents == [ours, incoming]
    assert result["data"]["head"] == head
    assert git(work, "rev-parse", "candidate/dev") == advanced
    assert not (work / "later.txt").exists()
    assert not Path(git(work, "rev-parse", "--git-path", "MERGE_HEAD")).exists()


@pytest.mark.parametrize("mode", ["pending", "start", "advanced"])
def test_public_merge_accepts_exact_peer_ref_without_moving_candidate(tmp_path, mode):
    """One existing native executor accepts a selected peer with unchanged protected refs."""
    work = native_merge_fixture(tmp_path, pending=mode != "start")
    ours, theirs = git(work, "rev-parse", "HEAD"), git(work, "rev-parse", "candidate/dev")
    peer = "refs/heads/work/peer"
    git(work, "update-ref", peer, theirs)
    git(work, "update-ref", "refs/heads/candidate/dev", ours)
    if mode == "advanced":
        tree = git(work, "rev-parse", f"{theirs}^{{tree}}")
        successor = git(work, "commit-tree", tree, "-p", theirs, "-m", "feat: later peer")
        git(work, "update-ref", peer, successor)
    selection = ("--source-ref", peer)
    if mode == "start":
        preview = run_ethos(
            "lane",
            "refresh-base",
            "--strategy",
            "merge",
            "--mode",
            "start",
            *selection,
            "--json",
            cwd=work,
        )
        assert apply_merge(work, preview)["data"]["state"] == "merge_pending"
    (work / "README.md").write_text("# Qualified peer contribution\n")
    git(work, "add", "README.md")
    preview = run_ethos(
        "lane",
        "refresh-base",
        "--strategy",
        "merge",
        "--mode",
        "continue",
        *selection,
        "--json",
        cwd=work,
    )
    arguments = shlex.split(preview["next_action"])
    assert arguments[arguments.index("--source-ref") + 1] == peer
    result = apply_merge(work, preview)
    assert result["verdict"] == "pass", result
    assert git(work, "rev-list", "--parents", "-n", "1", "HEAD").split()[1:] == [ours, theirs]
    assert git(work, "rev-parse", "candidate/dev") == ours
    assert git(work, "rev-parse", peer) == (successor if mode == "advanced" else theirs)
    assert not Path(git(work, "rev-parse", "--git-path", "MERGE_HEAD")).exists()


@pytest.mark.parametrize("fault", ["advance", "diverge", "missing", "short", "protected", "rebase"])
def test_peer_merge_ref_selection_refuses_unbound_or_changed_source(tmp_path, fault):
    """The exact source snapshot fences effects without treating ancestry as permission."""
    work = native_merge_fixture(tmp_path)
    head, incoming = git(work, "rev-parse", "HEAD"), git(work, "rev-parse", "MERGE_HEAD")
    (work / "README.md").write_text("# Combined contribution\n")
    git(work, "add", "README.md")
    peer = "refs/heads/work/peer"
    git(work, "update-ref", peer, incoming)
    args = (
        "lane",
        "refresh-base",
        "--strategy",
        "merge",
        "--mode",
        "continue",
        "--source-ref",
        peer,
        "--json",
    )
    if fault == "advance":
        preview = run_ethos(*args, cwd=work)
        tree = git(work, "rev-parse", f"{incoming}^{{tree}}")
        successor = git(work, "commit-tree", tree, "-p", incoming, "-m", "feat: later peer")
        git(work, "update-ref", peer, successor)
        with pytest.raises(AssertionError, match="merge_state_stale"):
            apply_merge(work, preview)
    else:
        if fault == "diverge":
            git(work, "update-ref", peer, head)
        elif fault == "missing":
            git(work, "update-ref", "-d", peer)
        elif fault in {"short", "protected"}:
            args = (*args[:-2], "work/peer" if fault == "short" else "refs/heads/dev", "--json")
        elif fault == "rebase":
            args = (*args[:3], "rebase", *args[4:])
        report = run_ethos(*args, cwd=work)
        assert report["verdict"] == "block", report
        assert any(gap.startswith("merge_source_ref") for gap in report["required_gaps"])
    assert git(work, "rev-parse", "HEAD") == head
    assert git(work, "rev-parse", "MERGE_HEAD") == incoming


def test_public_merge_preparation_is_explicit_and_conflicts_remain_recoverable(tmp_path):
    work = native_merge_fixture(tmp_path, pending=False)
    before = git(work, "rev-parse", "HEAD")
    preview = preview_merge(work, "start")
    assert preview["verdict"] == "pass", preview
    result = apply_merge(work, preview)
    assert result["data"]["state"] == "merge_pending", result
    assert git(work, "rev-parse", "HEAD") == before
    assert git(work, "diff", "--name-only", "--diff-filter=U") == "README.md"
    assert preview_merge(work, "abort")["verdict"] == "pass"


@pytest.mark.parametrize("mode", ["abort", "continue"])
@pytest.mark.parametrize("fault", ["content", "index", "holder"])
def test_public_merge_apply_rejects_changed_observation(tmp_path, monkeypatch, fault, mode):
    work = native_merge_fixture(tmp_path)
    if mode == "continue":
        (work / "README.md").write_text("# Accepted combined resolution\n")
        git(work, "add", "README.md")
    preview = preview_merge(work, mode)
    before = git(work, "rev-parse", "HEAD")
    if fault == "holder":
        monkeypatch.setenv("ETHOS_ACTOR", "agent:other")
    else:
        (work / "README.md").write_text("# Later resolution\n")
        if fault == "index":
            git(work, "add", "README.md")
    with pytest.raises(AssertionError, match=r"lease_holder_mismatch|merge_state_stale"):
        apply_merge(work, preview)
    assert git(work, "rev-parse", "HEAD") == before
    assert git(work, "rev-parse", "MERGE_HEAD")


def test_completed_abort_does_not_recognize_a_new_merge_at_same_head(tmp_path):
    """Equal branch HEAD alone does not prove the old operation is still current."""
    work = native_merge_fixture(tmp_path)
    preview = preview_merge(work, "abort")
    apply_merge(work, preview)
    incoming = git(work, "rev-parse", "candidate/dev")
    assert git_process(work, "merge", "--no-ff", "--no-commit", incoming).returncode == 1
    with pytest.raises(AssertionError, match="merge_result_stale"):
        apply_merge(work, preview)
    assert git(work, "rev-parse", "MERGE_HEAD") == incoming


@pytest.mark.parametrize("mode", ["abort", "continue"])
def test_lost_result_ack_is_recognized_without_repeating_effect(tmp_path, monkeypatch, mode):
    """The prepared observation bridges a lost result write after the native effect."""
    work = native_merge_fixture(tmp_path)
    if mode == "continue":
        (work / "README.md").write_text("# Resolved before interruption\n")
        git(work, "add", "README.md")
    preview = preview_merge(work, mode)
    record = merge_effect.record_attestations

    def lost_result(root, attestations):
        if any(item.predicate == "effect:git-merge" for item in attestations):
            message = "lost result acknowledgement"
            raise OSError(message)
        return record(root, attestations)

    monkeypatch.setattr(merge_effect, "record_attestations", lost_result)
    with pytest.raises(AssertionError, match="lost result acknowledgement"):
        apply_merge(work, preview)
    after = git(work, "rev-parse", "HEAD")
    monkeypatch.setattr(merge_effect, "record_attestations", record)
    recovered = apply_merge(work, preview)
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
    result = apply_merge(work, preview_merge(work, "abort"))
    assert result["data"]["state"] == "merge_aborted"
    assert git(work, "rev-parse", "HEAD") == before


@pytest.mark.parametrize("boundary", ["continue", "abort"])
def test_real_kill_recovers_without_repeating_native_effect(tmp_path, boundary):
    """A dead process releases the lock; exact evidence recovers its completed effect."""
    work = native_merge_fixture(tmp_path)
    if boundary == "continue":
        (work / "README.md").write_text("# Resolution before killed effect\n")
        git(work, "add", "README.md")
    preview = preview_merge(work, boundary)
    killed_merge_effect(work, preview)
    after = git(work, "rev-parse", "HEAD")
    result = apply_merge(work, preview)
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
    preview = preview_merge(work, "abort")
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
    preview = preview_merge(work, "abort")
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
        artifact_path = artifact["path"]
        assert isinstance(artifact_path, str)
        data = json.loads(Path(artifact_path).read_text())
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
    assert preview_merge(work, "abort")["verdict"] == "pass"


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
    preview = preview_merge(work, "continue")
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
