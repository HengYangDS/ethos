from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.openspec.commitment import load_openspec_commitment
from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.adapters.repo.commitment import load_repository_commitment
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


def _repository_commitment(root: Path, *, subject: str = "repository:test") -> None:
    (root / ".ethos").mkdir(exist_ok=True)
    (root / ".ethos" / "commitment.toml").write_text(
        'schema_version = 1\nid = "repository:test"\nintent = "Govern the repository."\n'
        f'subjects = ["{subject}"]\n',
        encoding="utf-8",
    )


def test_generic_commitment_loader_uses_profile_selected_carrier(tmp_path: Path) -> None:
    _repository_commitment(tmp_path)
    (tmp_path / ".ethos" / "profile.toml").write_text(
        'profile_id = "sample"\ncommitment = "governance/commitment.toml"\n',
        encoding="utf-8",
    )
    carrier = tmp_path / "governance"
    carrier.mkdir(parents=True)
    (carrier / "commitment.toml").write_text(
        """schema_version = 1
id = "change:terminal-convergence"
intent = "Converge the repository."
subjects = ["repository:self"]
scope = ["src/**"]
acceptance = ["terminal_state_proven"]
authority_refs = ["user_instruction"]
permissions = ["repository.read"]
dependencies = []
""",
        encoding="utf-8",
    )

    commitment = load_commitment(tmp_path)

    assert commitment.id == "change:terminal-convergence"
    assert commitment.subjects == ("repository:test",)
    assert commitment.scope == ("src/**",)


def test_explicit_commitment_carrier_does_not_require_openspec(
    tmp_path: Path,
) -> None:
    _repository_commitment(tmp_path)
    carrier = tmp_path / "intent"
    carrier.mkdir(parents=True)
    (carrier / "commitment.toml").write_text(
        """schema_version = 1
id = "change:semantic-kernel"
intent = "Converge the kernel."
subjects = ["repository:self"]
""",
        encoding="utf-8",
    )

    assert load_commitment(tmp_path, carrier="intent/commitment.toml").id == (
        "change:semantic-kernel"
    )


def test_generic_commitment_loader_ignores_openspec_inventory_and_tasks(tmp_path: Path) -> None:
    _repository_commitment(tmp_path)
    for change_id in ("first", "second"):
        carrier = tmp_path / "openspec" / "changes" / change_id
        carrier.mkdir(parents=True)
        (carrier / "commitment.toml").write_text(
            f"""schema_version = 1
id = "change:{change_id}"
intent = "Change {change_id}."
subjects = ["repository:self"]
""",
            encoding="utf-8",
        )

        (carrier / "tasks.md").write_text("- [x] Historical\n", encoding="utf-8")

    assert load_commitment(tmp_path).id == "repository:test"


def test_native_commitment_selection_treats_unarchived_changes_as_active(
    tmp_path: Path,
) -> None:
    _repository_commitment(tmp_path)
    _enable_openspec_profile(tmp_path)
    for change_id, task in (("active", "- [ ] Continue\n"), ("complete", "- [x] Done\n")):
        carrier = tmp_path / "openspec" / "changes" / change_id
        carrier.mkdir(parents=True)
        (carrier / "commitment.toml").write_text(
            f'schema_version = 1\nid = "change:{change_id}"\nintent = "{change_id}."\n'
            'subjects = ["repository:self"]\n',
            encoding="utf-8",
        )
        (carrier / "tasks.md").write_text(task, encoding="utf-8")

    with pytest.raises(ValueError, match="commitment_ambiguous"):
        load_openspec_commitment(tmp_path)
    assert load_openspec_commitment(tmp_path, change_id="complete").id == "change:complete"


def test_exact_lease_binding_does_not_follow_a_carrier_move(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _repository_commitment(repo)
    _enable_openspec_profile(repo)
    carrier = _change_carrier(repo, "retired", "retired")
    relative = carrier.relative_to(repo).as_posix() + "/commitment.toml"
    bytes_sha256 = hashlib.sha256((repo / relative).read_bytes()).hexdigest()
    digest = load_commitment(repo, carrier=relative).digest()
    git(repo, "add", ".")
    git(
        repo,
        "commit",
        "-m",
        "declare commitment",
    )
    head = git(repo, "rev-parse", "HEAD")
    tree = git(repo, "rev-parse", "HEAD^{tree}")

    lease = {
        "expected_head": head,
        "expected_tree": tree,
        "base_commitment_path": relative,
        "base_commitment_bytes_sha256": bytes_sha256,
        "base_commitment_digest": digest,
    }
    assert (
        load_lease_bound_commitment(
            repo,
            lease=lease,
            change_id="retired",
        ).id
        == "change:retired"
    )

    archived = repo / "openspec/changes/archive/2026-07-31-retired"
    archived.parent.mkdir(parents=True)
    carrier.rename(archived)
    git(repo, "add", ".")
    git(
        repo,
        "commit",
        "-m",
        "archive commitment",
    )

    with pytest.raises(ValueError, match="lease_base_commitment_path_mismatch"):
        load_lease_bound_commitment(
            repo,
            lease=lease
            | {
                "expected_head": git(repo, "rev-parse", "HEAD"),
                "expected_tree": git(repo, "rev-parse", "HEAD^{tree}"),
            },
            change_id="retired",
        )


def test_commitment_missing_fails_closed(tmp_path: Path) -> None:
    _repository_commitment(tmp_path)

    with pytest.raises(ValueError, match="commitment_missing"):
        load_commitment(tmp_path, change_id="terminal-convergence")

    assert load_commitment(tmp_path).id == "repository:test"


def test_unselected_scope_file_does_not_override_commitment(tmp_path: Path) -> None:
    _repository_commitment(tmp_path)
    carrier = tmp_path / "openspec" / "changes" / "terminal-convergence"
    carrier.mkdir(parents=True)
    (carrier / "commitment.toml").write_text(
        """schema_version = 1
id = "change:terminal-convergence"
intent = "Converge the repository."
subjects = ["repository:self"]
scope = ["src/**"]
""",
        encoding="utf-8",
    )
    (carrier / "scope.toml").write_text(
        'schema_version = 1\npaths = ["docs/**"]\n',
        encoding="utf-8",
    )

    commitment = load_commitment(
        tmp_path, carrier="openspec/changes/terminal-convergence/commitment.toml"
    )

    assert commitment.scope == ("src/**",)


def test_repository_commitment_owns_stable_subject_across_worktrees(tmp_path: Path) -> None:
    _repository_commitment(tmp_path)

    commitment = load_repository_commitment(tmp_path)

    assert commitment.id == "repository:test"
    assert commitment.subjects == ("repository:test",)


def test_repository_commitment_requires_id_to_equal_its_single_subject(tmp_path: Path) -> None:
    _repository_commitment(tmp_path, subject="repository:second")

    with pytest.raises(ValueError, match="repository_commitment_identity_mismatch"):
        load_repository_commitment(tmp_path)


def _enable_openspec_profile(root: Path) -> None:
    (root / ".ethos" / "profile.toml").write_text(
        'profile_id = "self"\n\n[openspec]\nmaterial_paths = ["openspec/**"]\n',
        encoding="utf-8",
    )


def _change_carrier(root: Path, relative: str, change_id: str) -> Path:
    carrier = root / "openspec" / "changes" / relative
    carrier.mkdir(parents=True)
    (carrier / "commitment.toml").write_text(
        f'schema_version = 1\nid = "change:{change_id}"\nintent = "Change."\n'
        'subjects = ["repository:self"]\n',
        encoding="utf-8",
    )
    return carrier


def test_carrier_path_and_commitment_identity_must_match(tmp_path: Path) -> None:
    _repository_commitment(tmp_path)
    _enable_openspec_profile(tmp_path)
    _change_carrier(tmp_path, "terminal-convergence", "other-change")

    with pytest.raises(ValueError, match="commitment_identity_mismatch:terminal-convergence"):
        load_openspec_commitment(tmp_path, change_id="terminal-convergence")
