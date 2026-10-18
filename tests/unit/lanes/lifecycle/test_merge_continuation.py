"""Public merge effects bind native state and preserve work under real hooks."""

import base64
import json
import shlex
import sqlite3
import sys
from contextlib import closing
from pathlib import Path
from unittest.mock import Mock

import pytest
from filelock import FileLock

import ethos.adapters.admission.current.resolution as resolution_owner
import ethos.adapters.mutation.lane_lifecycle.merge as merge_admission
import ethos.adapters.repo.git_effect_attestation as ref_evidence
import ethos.adapters.repo.merge.effect as merge_effect
import ethos.adapters.repo.runtime.binding as runtime_binding_owner
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.merge.observation import observe_merge
from ethos.adapters.repo.merge.recovery import preserve_merge
from ethos.adapters.store.state.schema import state_database
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import create_change_source_lane
from tests.support.governed_repository import git
from tests.support.governed_repository import start_adopted_candidate
from tests.support.governed_repository import write_active_commitment
from tests.support.openspec_lifecycle import HOLDER
from tests.support.openspec_lifecycle import killed_merge_effect
from tests.support.openspec_lifecycle import native_merge_fixture
from tests.support.runtime_scenarios import git_process
from tests.support.runtime_scenarios import install_fixture_hook_runtime


def _preview(work: Path, mode: str = "inspect", source: str | None = None) -> dict:
    """Read the public exact-state preview without performing an effect."""
    args = ("lane", "refresh-base", "--strategy", "merge", "--mode", mode, "--json")
    report = run_ethos(*args, *(("--source-ref", source) if source else ()), cwd=work)
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


def test_explicit_merge_intent_preserves_unchanged_incoming_change(tmp_path, monkeypatch):
    """Explicit authoring scope does not adopt the other parent's unchanged intent."""
    work = native_merge_fixture(tmp_path)
    monkeypatch.setenv("ETHOS_CHANGE", "publication")
    (work / "README.md").write_text("# Accepted combined resolution\n")
    git(work, "add", "README.md")
    incoming = git(work, "rev-parse", "MERGE_HEAD")
    path = "openspec/changes/static-delivery/tasks.md"
    before = git(work, "show", f":{path}")
    assert before == git(work, "show", f"{incoming}:{path}")
    preview = _preview(work, "continue")
    assert preview["data"]["observation"]["parents"] == [incoming]
    assert git(work, "show", f":{path}") == before
    assert git(work, "rev-parse", "MERGE_HEAD") == incoming


def test_merge_intent_preserves_native_composition_of_prior_change(tmp_path, monkeypatch):
    """Earlier contributions from both parents are not new continuation authoring."""
    repo, candidate = start_adopted_candidate(tmp_path)
    write_active_commitment(candidate, change_id="shared")
    commit_fixture(candidate, "feat: declare shared intent")
    work = create_change_source_lane(
        repo,
        tmp_path / "work",
        change_id="publication",
        holder_ref=HOLDER,
        base_ref="candidate/dev",
    )
    path = "openspec/changes/shared/design.md"
    own = work / path
    own.write_text(own.read_text().replace("Test-only governed fixture.", "Local contribution."))
    (work / "README.md").write_text("# Local contribution\n")
    commit_fixture(work, "feat: extend local design")
    other = candidate / path
    other.write_text(other.read_text().replace("Run focused lifecycle tests.", "Incoming proof."))
    (candidate / "README.md").write_text("# Incoming contribution\n")
    incoming = commit_fixture(candidate, "feat: extend incoming proof")
    assert git_process(work, "merge", "--no-ff", "--no-commit", incoming).returncode == 1
    (work / "README.md").write_text("# Accepted combined resolution\n")
    git(work, "add", "README.md")
    before = git(work, "show", f":{path}")
    assert "Local contribution." in before
    assert "Incoming proof." in before
    monkeypatch.setenv("ETHOS_CHANGE", "publication")
    preview = _preview(work, "continue")
    assert preview["data"]["observation"]["parents"] == [incoming]
    assert git(work, "show", f":{path}") == before


@pytest.mark.parametrize("disposition", ["present", "absent"])
def test_merge_continue_preserves_exact_incoming_task_disposition(
    tmp_path, monkeypatch, disposition
):
    """Exact import or incoming deletion resolves a conflict without authoring progress."""
    repo, candidate = start_adopted_candidate(tmp_path)
    write_active_commitment(candidate, change_id="shared")
    commit_fixture(candidate, "feat: declare shared intent")
    work = create_change_source_lane(
        repo,
        tmp_path / "work",
        change_id="publication",
        holder_ref=HOLDER,
        base_ref="candidate/dev",
    )
    path = "openspec/changes/shared/tasks.md"
    own, other = work / path, candidate / path
    own.write_text(own.read_text().replace("fixture lifecycle", "local qualification"))
    (work / "README.md").write_text("# Local contribution\n")
    before = commit_fixture(work, "feat: extend local task")
    if disposition == "present":
        other.write_text(other.read_text().replace("fixture lifecycle", "incoming qualification"))
        imported = other.read_bytes()
    else:
        git(candidate, "rm", "-r", "--", "openspec/changes/shared")
        imported = None
    (candidate / "README.md").write_text("# Incoming contribution\n")
    incoming = commit_fixture(candidate, "feat: update incoming task disposition")
    assert git_process(work, "merge", "--no-ff", "--no-commit", incoming).returncode == 1
    assert path in git(work, "diff", "--name-only", "--diff-filter=U").splitlines()
    if imported is None:
        git(work, "rm", "--", path)
    else:
        own.write_bytes(imported)
        git(work, "add", path)
    (work / "README.md").write_text("# Accepted combined resolution\n")
    git(work, "add", "README.md")
    monkeypatch.setenv("ETHOS_CHANGE", "publication")
    result = _apply(work, _preview(work, "continue"))
    assert result["verdict"] == "pass", result
    assert git(work, "rev-list", "--parents", "-n", "1", "HEAD").split()[1:] == [before, incoming]
    if imported is None:
        assert not own.exists()
        assert git_process(work, "cat-file", "-e", f"HEAD:{path}").returncode != 0
    else:
        assert own.read_bytes() == imported
        assert git(work, "show", f"HEAD:{path}") == git(work, "show", f"{incoming}:{path}")


@pytest.mark.parametrize("movement", ["before-preview", "before-apply"])
def test_public_merge_continuation_uses_pending_parent_when_candidate_advances(tmp_path, movement):
    """Candidate integration is separate from finishing an exact pending native merge."""
    work = native_merge_fixture(tmp_path)
    ours, incoming = (git(work, "rev-parse", "HEAD"), git(work, "rev-parse", "MERGE_HEAD"))
    (work / "README.md").write_text("# Accepted combined resolution\n")
    git(work, "add", "README.md")
    candidate = tmp_path / "repo-candidate-dev"
    preview = _preview(work, "continue") if movement == "before-apply" else None
    (candidate / "later.txt").write_text("Unrelated candidate progress\n")
    advanced = commit_fixture(candidate, "fix: advance candidate independently")
    preview = preview or _preview(work, "continue")
    result = _apply(work, preview)
    assert result["verdict"] == "pass", result
    head, *parents = git(work, "rev-list", "--parents", "-n", "1", "HEAD").split()
    assert parents == [ours, incoming]
    assert result["data"]["head"] == head
    assert git(work, "rev-parse", "candidate/dev") == advanced
    assert not (work / "later.txt").exists()
    assert not Path(git(work, "rev-parse", "--git-path", "MERGE_HEAD")).exists()


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


@pytest.mark.parametrize("mode", ["abort", "continue"])
@pytest.mark.parametrize("fault", ["content", "index", "holder"])
def test_public_merge_apply_rejects_changed_observation(tmp_path, monkeypatch, fault, mode):
    work = native_merge_fixture(tmp_path)
    if mode == "continue":
        (work / "README.md").write_text("# Accepted combined resolution\n")
        git(work, "add", "README.md")
    preview = _preview(work, mode)
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


def _interrupt_merge_ack(work, preview, monkeypatch, boundary):
    """Exit at one native acknowledgement boundary and restore the real recorder."""
    record = merge_effect.record_attestations
    record_ref = ref_evidence.records

    def lost_result(root, attestations):
        if any(item.predicate == "effect:git-merge" for item in attestations):
            message = "lost result acknowledgement"
            raise OSError(message)
        return record(root, attestations)

    def lost_ref(root, plan, attestation=None, **kwargs):
        if attestation is not None:
            message = "lost reference acknowledgement"
            raise SystemExit(message)
        return record_ref(root, plan, attestation, **kwargs)

    with monkeypatch.context() as patch:
        if boundary == "ref":
            patch.setattr(ref_evidence, "records", lost_ref)
        else:
            patch.setattr(merge_effect, "record_attestations", lost_result)
        with pytest.raises(AssertionError):
            _apply(work, preview)


@pytest.mark.parametrize(
    ("boundary", "peer"),
    [("abort", False), ("ref", False), ("merge", False), ("ref", True), ("merge", True)],
)
@pytest.mark.parametrize("upgrade", [False, True])
def test_lost_ack_recovers_original_request_without_repeating_effect(
    tmp_path, monkeypatch, boundary, upgrade, peer
):
    """Original request custody survives either ACK loss and a valid runtime upgrade."""
    work = native_merge_fixture(tmp_path)
    mode = "abort" if boundary == "abort" else "continue"
    if mode == "continue":
        (work / "README.md").write_text("# Resolved before interruption\n")
        git(work, "add", "README.md")
    source = "refs/heads/work/peer" if peer else None
    if source:
        incoming = git(work, "rev-parse", "MERGE_HEAD")
        successor = git(
            work,
            "commit-tree",
            git(work, "rev-parse", f"{incoming}^{{tree}}"),
            "-p",
            incoming,
            "-m",
            "feat: later peer contribution",
        )
        git(work, "update-ref", source, successor)
    preview = _preview(work, mode, source)
    _interrupt_merge_ack(work, preview, monkeypatch, boundary)
    after = git(work, "rev-parse", "HEAD")
    if boundary == "ref":
        assert after != preview["summary"]["head"]
        assert not any(
            item.predicate == "effect:git-ref-update" for item in read_attestation_set(work)[1]
        )
    if upgrade:
        previous = merge_admission.hook_runtime_binding(work)["runtime_digest"]
        installed = install_fixture_hook_runtime(
            work, native_executables={"qualification": Path(sys.executable)}
        )
        assert installed["runtime_digest"] != previous
    if mode == "continue":
        before_inspect = observe_merge(work), git(work, "show-ref"), read_attestation_set(work)[0]
        recovery_preview = _preview(work)
        assert recovery_preview["next_action"] == preview["next_action"]
        assert (
            observe_merge(work),
            git(work, "show-ref"),
            read_attestation_set(work)[0],
        ) == before_inspect
    recovered = _apply(work, preview)
    assert recovered["verdict"] == "pass", recovered
    assert git(work, "rev-parse", "HEAD") == after
    assert not observe_merge(work).parents
    repeated = _apply(work, preview)
    assert repeated["verdict"] == "pass"
    assert repeated["data"]["state"] == recovered["data"]["state"]
    assert git(work, "rev-parse", "HEAD") == after
    if boundary == "ref":
        attestation = next(
            item
            for item in read_attestation_set(work)[1]
            if item.id == recovered["data"]["ref_attestation"]
        )
        assert attestation.payload.body["result"]["state"] == "recovered"
        assert attestation.payload.body["result"]["executed"] is False


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
