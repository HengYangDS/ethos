"""Exact history repair preserves source bytes and validates every rewritten edge."""

from __future__ import annotations

import pytest

import ethos.adapters.repo.trust_anchor.verification as verification
from ethos.adapters.repo.commit.creation import create_signed_payload
from ethos.adapters.repo.commit.history import history_repair_coordinates
from ethos.adapters.repo.commit.history import history_repair_scope
from ethos.adapters.repo.commit.history import prepare_history_repair
from ethos.adapters.repo.commit.history import validate_history_repair
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_object import unsigned_commit_payload
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


@pytest.mark.parametrize("selected_first", [False, True])
def test_history_repair_preserves_merge_parent_order_and_rejects_permutation(
    tmp_path, selected_first
):
    """A valid repair preserves each merge edge and every non-selected payload byte."""
    repo, descendant, selected, before, corrections = _history(tmp_path)
    tree = git(repo, "rev-parse", f"{descendant}^{{tree}}")
    side = git(repo, "commit-tree", tree, "-p", before, "-m", "fix: independent side")
    parents = (descendant, side) if selected_first else (side, descendant)
    old = git(repo, "commit-tree", tree, "-p", parents[0], "-p", parents[1], "-m", "fix: merge")
    originals = {
        oid: run_git(repo, "cat-file", "commit", oid, text=False).stdout
        for oid in (before, selected, descendant, side, old)
    }
    refs = git(repo, "show-ref")
    prepared = prepare_history_repair(repo, old, corrections=corrections)
    mapping = prepared["mapping"]
    assert set(mapping) == {selected, descendant, old}
    for previous, current in mapping.items():
        expected = originals[previous]
        for source, target in mapping.items():
            expected = expected.replace(
                f"parent {source}\n".encode(), f"parent {target}\n".encode()
            )
        if previous == selected:
            expected = expected.replace(
                b"author Wrong <wrong@example.invalid> ",
                b"author ETHOS Test <test@example.invalid> ",
                1,
            )
        actual = run_git(repo, "cat-file", "commit", current, text=False).stdout
        assert unsigned_commit_payload(actual) == expected
        git(repo, "verify-commit", current)
    mapped = tuple(mapping.get(parent, parent) for parent in parents)
    assert git(repo, "show", "-s", "--format=%P", prepared["replacement"]).split() == list(mapped)
    merge = unsigned_commit_payload(
        run_git(repo, "cat-file", "commit", prepared["replacement"], text=False).stdout
    )
    invalid = create_signed_payload(
        repo,
        merge.replace(
            f"parent {mapped[0]}\nparent {mapped[1]}\n".encode(),
            f"parent {mapped[1]}\nparent {mapped[0]}\n".encode(),
            1,
        ),
    )
    with pytest.raises(ValueError, match="history_repair_"):
        validate_history_repair(repo, old, invalid, corrections=corrections)
    assert git(repo, "show-ref") == refs
    assert {
        oid: run_git(repo, "cat-file", "commit", oid, text=False).stdout for oid in originals
    } == originals
