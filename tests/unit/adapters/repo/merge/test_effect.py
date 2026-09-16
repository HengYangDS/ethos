"""Exact native merge recovery cannot infer success from incomplete historical evidence."""

import shlex
from datetime import UTC
from datetime import datetime
from pathlib import Path

import pytest

import ethos.adapters.repo.merge.effect as effect
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.adapters.repo.merge.observation import observe_merge
from ethos.contracts.semantic import Attestation
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_test_profile
from tests.support.openspec_lifecycle import native_merge_fixture
from tests.support.runtime_scenarios import git_process


def _pending(tmp_path: Path) -> Path:
    """Build only the native conflict needed by the effect recovery owner."""
    root = init_git_repo(tmp_path / "repo")
    write_test_profile(root)
    commit_fixture(root, "chore: establish repository identity")
    git(root, "checkout", "-b", "incoming")
    (root / "README.md").write_text("incoming\n")
    commit_fixture(root, "feat: incoming")
    git(root, "checkout", "dev")
    (root / "README.md").write_text("local\n")
    commit_fixture(root, "feat: local")
    assert git_process(root, "merge", "--no-ff", "--no-commit", "incoming").returncode == 1
    return root


def _prepare(root: Path, mode: str):
    """Retain the same preparation that precedes an effect whose ACK can be lost."""
    before = observe_merge(root)
    checked = 0

    def interrupt_before_effect():
        nonlocal checked
        checked += 1
        if checked == 2:
            message = "interrupted after durable preparation"
            raise InterruptedError(message)

    with pytest.raises(InterruptedError, match="after durable preparation"):
        effect.apply_merge(
            root,
            before,
            mode=mode,
            incoming="",
            candidate_ref="",
            actor="agent:test",
            lease={},
            message="chore: recover merge",
            recheck=interrupt_before_effect,
            recheck_authority=lambda: None,
            state_digest=before.digest,
        )
    return before


def _recover(root: Path, before, mode: str, *, matches: bool = True):
    """Exercise result recognition independently of outer authority admission."""
    return effect.recognized_merge(
        root, before.digest, mode, recheck=lambda: None, request_matches=lambda _: matches
    )


def test_unchanged_preparation_does_not_claim_an_effect_happened(tmp_path: Path):
    """Prepared is not executed, even though its durable observation exists."""
    root = _pending(tmp_path)
    before = _prepare(root, "abort")
    records = read_attestation_set(root)[0]
    assert _recover(root, before, "abort") is None
    assert read_attestation_set(root)[0] == records
    assert observe_merge(root) == before


@pytest.mark.parametrize("completed", [False, True])
def test_recovery_rejects_a_different_request_even_with_matching_lookup(tmp_path, completed):
    """Result lookup cannot substitute for matching the original request coordinates."""
    root = _pending(tmp_path)
    before = _prepare(root, "abort")
    if completed:
        git(root, "merge", "--abort")
        result = _recover(root, before, "abort")
        assert result["state"] == "merge_aborted"
    current = observe_merge(root)
    with pytest.raises(ValueError, match="merge_request_stale"):
        _recover(root, before, "abort", matches=False)
    assert observe_merge(root) == current


def test_competing_preparations_do_not_select_an_arbitrary_recovery(tmp_path: Path):
    """Two distinct preparations for the same request require disambiguation."""
    root = _pending(tmp_path)
    before = _prepare(root, "abort")
    preparation = read_attestation_set(root)[1][0]
    value = preparation.model_dump(mode="python", exclude={"id"})
    value["issued_at"] = datetime.now(UTC)
    value["valid_from"] = value["issued_at"]
    record_attestations(root, (Attestation.issue(value),))
    with pytest.raises(ValueError, match="merge_preparation_ambiguous"):
        _recover(root, before, "abort")
    assert observe_merge(root) == before


@pytest.mark.parametrize("fault", ["competing", "untracked", "unstaged", "staged", "wrong-head"])
def test_lost_abort_ack_requires_exact_clean_native_rollback(tmp_path: Path, fault: str):
    """Unrelated subsequent state cannot be accepted as an acknowledged rollback."""
    root = _pending(tmp_path)
    before = _prepare(root, "abort")
    git(root, "merge", "--abort")
    if fault == "competing":
        effect.git_path(root, "CHERRY_PICK_HEAD").write_text(before.head + "\n")
    elif fault == "untracked":
        (root / "valuable").write_text("retain this\n")
    elif fault == "wrong-head":
        (root / "README.md").write_text("later committed content\n")
        commit_fixture(root, "chore: later commit")
    else:
        (root / "README.md").write_text("post-abort edit\n")
        if fault == "staged":
            git(root, "add", "README.md")
    current = observe_merge(root)
    with pytest.raises(ValueError, match="merge_outcome_unknown"):
        _recover(root, before, "abort")
    assert observe_merge(root) == current


def test_continue_without_ref_attestation_does_not_infer_cas_success(tmp_path: Path):
    """A native commit alone is not evidence of the admitted reference effect."""
    root = _pending(tmp_path)
    (root / "README.md").write_text("combined\n")
    git(root, "add", "README.md")
    before = _prepare(root, "continue")
    commit_fixture(root, "feat: native combined result")
    current = observe_merge(root)
    with pytest.raises(ValueError, match="merge_outcome_unknown"):
        _recover(root, before, "continue")
    assert observe_merge(root) == current


@pytest.mark.parametrize("fault", ["metadata", "index", "unstaged", "untracked", "competing"])
def test_metadata_finish_refuses_a_changed_post_cas_projection(tmp_path, monkeypatch, fault):
    """Metadata cleanup cannot consume edits or operations made after ref acceptance."""
    root = native_merge_fixture(tmp_path)
    (root / "README.md").write_text("combined\n")
    git(root, "add", "README.md")
    preview = run_ethos(
        "lane", "refresh-base", "--strategy", "merge", "--mode", "continue", "--json", cwd=root
    )
    assert preview["verdict"] == "pass"
    execute = effect.execute_git_effect
    changed = []

    def change_after_cas(*args, **kwargs):
        result = execute(*args, **kwargs)
        if fault == "metadata":
            effect.git_path(root, "MERGE_MSG").write_text("later message\n")
        elif fault == "competing":
            effect.git_path(root, "CHERRY_PICK_HEAD").write_text(
                git(root, "rev-parse", "HEAD") + "\n"
            )
        elif fault == "untracked":
            (root / "valuable").write_text("later content\n")
        else:
            (root / "README.md").write_text("later resolution\n")
            if fault == "index":
                git(root, "add", "README.md")
        changed.append(observe_merge(root))
        return result

    monkeypatch.setattr(effect, "execute_git_effect", change_after_cas)
    result = run_ethos_blocked(*shlex.split(preview["next_action"])[1:], cwd=root)
    assert "merge_projection_stale" in result["required_gaps"]
    assert observe_merge(root) == changed[0]
    assert git(root, "rev-parse", "MERGE_HEAD")


@pytest.mark.parametrize(
    ("boundary", "expected"),
    [
        ("pending-start", "merge_already_in_progress"),
        ("absent-continue", "merge_not_in_progress"),
        ("missing-candidate", "candidate_branch_missing"),
        ("current-base", "base_current"),
        ("invalid-intent", "openspec_status_incomplete:publication"),
    ],
)
def test_public_preview_distinguishes_operation_and_source_prerequisites(
    tmp_path, boundary, expected
):
    """A visible lane is not a pending operation or permission to invent one."""
    root = native_merge_fixture(tmp_path, pending=boundary in {"pending-start", "invalid-intent"})
    mode = "start" if boundary in {"pending-start", "current-base"} else "continue"
    if boundary == "missing-candidate":
        git(root, "update-ref", "-d", "refs/heads/candidate/dev")
    elif boundary == "current-base":
        git(root, "update-ref", "refs/heads/candidate/dev", git(root, "rev-parse", "HEAD"))
    elif boundary == "invalid-intent":
        (root / "README.md").write_text("resolved\n")
        (root / "openspec/changes/publication/tasks.md").unlink()
        git(root, "add", ".")
    before = observe_merge(root)
    report = run_ethos(
        "lane", "refresh-base", "--strategy", "merge", "--mode", mode, "--json", cwd=root
    )
    if boundary == "current-base":
        assert report["verdict"] == "pass"
        assert report["data"]["state"] == expected
    else:
        assert report["verdict"] == "block"
        assert report["required_gaps"] == [expected]
    assert observe_merge(root) == before


def test_merge_preview_never_grants_mutation_of_a_protected_root(tmp_path: Path):
    """The native mode cannot bypass the repository's branch-role boundary."""
    root = init_git_repo(tmp_path / "repo")
    before = observe_merge(root)
    report = run_ethos("lane", "refresh-base", "--strategy", "merge", "--json", cwd=root)
    assert report["required_gaps"] == ["protected_root_mutation"]
    assert observe_merge(root) == before
