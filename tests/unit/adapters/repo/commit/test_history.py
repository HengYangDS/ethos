"""Exact history repair preserves source bytes and validates every rewritten edge."""

from __future__ import annotations

import pytest

import ethos.adapters.repo.trust_anchor.verification as verification
from ethos.adapters.repo.commit.history import history_repair_coordinates
from ethos.adapters.repo.commit.history import history_repair_scope
from ethos.adapters.repo.commit.history import prepare_history_repair
from ethos.adapters.repo.commit.history import validate_history_repair
from ethos.adapters.repo.git import run_git
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.signature import configure_signer


def _history(tmp_path):
    repo = init_git_repo(tmp_path / "repo")
    configure_signer(repo, tmp_path)
    before = git(repo, "rev-parse", "HEAD")
    (repo / "value").write_text("preserved\n")
    git(repo, "add", "value")
    tree = git(repo, "write-tree")
    selected = run_git(
        repo,
        "commit-tree",
        tree,
        "-p",
        before,
        "-m",
        "fix: wrong attribution",
        env={"GIT_AUTHOR_NAME": "Wrong", "GIT_AUTHOR_EMAIL": "wrong@example.invalid"},
    ).stdout.strip()
    old = git(repo, "commit-tree", tree, "-p", selected, "-m", "fix: descendant")
    corrections = {
        selected: {
            "author": {
                "expected": {"name": "Wrong", "email": "wrong@example.invalid"},
                "replacement": {"name": "ETHOS Test", "email": "test@example.invalid"},
            }
        }
    }
    return repo, old, selected, before, corrections


def test_history_repair_preserves_every_unchanged_field_and_parent(tmp_path):
    repo, old, selected, before, corrections = _history(tmp_path)
    original_refs = git(repo, "show-ref")
    result = prepare_history_repair(repo, old, corrections=corrections)
    assert result["replacement"] != old
    assert set(result["mapping"]) == {selected, old}
    assert before not in result["mapping"]
    validate_history_repair(repo, old, result["replacement"], corrections=corrections)
    assert git(repo, "show-ref") == original_refs
    assert git(repo, "rev-parse", f"{old}^{{tree}}") == git(
        repo, "rev-parse", f"{result['replacement']}^{{tree}}"
    )
    for replacement in result["mapping"].values():
        git(repo, "verify-commit", replacement)


@pytest.mark.parametrize(
    "case", ["wrong_expected", "unreachable", "changed_tree", "changed_message"]
)
def test_history_repair_rejects_unselected_or_changed_semantics(tmp_path, case):
    repo, old, selected, _before, corrections = _history(tmp_path)
    if case == "wrong_expected":
        corrections[selected]["author"]["expected"]["name"] = "Not the original"
    if case == "unreachable":
        corrections = {"0" * 40: corrections[selected]}
    if case in {"wrong_expected", "unreachable"}:
        with pytest.raises(ValueError, match="history_repair_"):
            prepare_history_repair(repo, old, corrections=corrections)
        return
    result = prepare_history_repair(repo, old, corrections=corrections)
    tree = git(repo, "rev-parse", f"{old}^{{tree}}")
    if case == "changed_tree":
        (repo / "value").write_text("not-preserved\n")
        git(repo, "add", "value")
        tree = git(repo, "write-tree")
    invalid = git(
        repo,
        "commit-tree",
        "-S",
        tree,
        "-p",
        result["mapping"][selected],
        "-m",
        "fix: changed message" if case == "changed_message" else "fix: descendant",
    )
    with pytest.raises(ValueError, match="history_repair_"):
        validate_history_repair(repo, old, invalid, corrections=corrections)


@pytest.mark.parametrize("damaged", [False, True])
def test_backup_must_restore_objects_without_borrowing_original_repository(tmp_path, damaged):
    repo, old, _selected, _before, corrections = _history(tmp_path)
    git(repo, "update-ref", "refs/heads/dev", old)
    backup = tmp_path / "original.bundle"
    git(repo, "bundle", "create", str(backup), "refs/heads/dev")
    if damaged:
        backup.write_bytes(backup.read_bytes()[:-10])
        # Header/prerequisite validation alone accepts a damaged pack.
        assert run_git(repo, "bundle", "verify", str(backup), check=False).returncode == 0
        with pytest.raises(ValueError, match="history_repair_backup_not_recoverable"):
            history_repair_coordinates(
                repo, old, corrections=corrections, reason="repair", backup=backup
            )
    else:
        observed = history_repair_coordinates(
            repo, old, corrections=corrections, reason="repair", backup=backup
        )
        assert observed["affected_count"] == 2
    assert not list((repo / ".git").glob("ethos-history-restore-*"))


def test_resigning_with_the_same_trusted_key_is_rejected_before_object_creation(tmp_path):
    repo, old, _selected, _before, corrections = _history(tmp_path)
    signed = prepare_history_repair(repo, old, corrections=corrections)["replacement"]
    before = git(repo, "count-objects", "-v"), git(repo, "show-ref")
    with pytest.raises(ValueError, match="history_repair_no_effect"):
        history_repair_scope(repo, signed, corrections={signed: {"resign": True}})
    assert (git(repo, "count-objects", "-v"), git(repo, "show-ref")) == before


def test_history_validation_rejects_trust_change_after_native_batch(tmp_path, monkeypatch):
    """History verification must not bypass the current native trust owner in its batch loop."""
    repo, old, _selected, _before, corrections = _history(tmp_path)
    prepared = prepare_history_repair(repo, old, corrections=corrections)
    before = git(repo, "show-ref")
    native = verification.run_git
    verified = []

    def revoke_after_batch(root, *args, **kwargs):
        result = native(root, *args, **kwargs)
        if "verify-commit" in args:
            assert result.returncode == 0, result.stderr
            verified.append(True)
            (tmp_path / "trust/allowed-signers").write_bytes(b"")
        return result

    monkeypatch.setattr(verification, "run_git", revoke_after_batch)
    with pytest.raises(ValueError, match="history_repair_signature_untrusted"):
        validate_history_repair(repo, old, prepared["replacement"], corrections=corrections)
    assert verified
    assert git(repo, "show-ref") == before
