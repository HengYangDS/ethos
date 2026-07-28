from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.adapters.openspec.commitment import load_openspec_commitment
from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.commitment import load_repository_contract

if TYPE_CHECKING:
    from pathlib import Path


def test_generic_commitment_loader_uses_profile_selected_carrier(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "commitment.toml").write_text(
        """schema_version = 1
id = "repository:test"
intent = "Govern the repository."
subjects = ["repository:test"]
""",
        encoding="utf-8",
    )
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

    contract = load_commitment(tmp_path)

    assert contract.id == "change:terminal-convergence"
    assert contract.subjects == ("repository:test",)
    assert contract.scope == ("src/**",)


def test_explicit_commitment_carrier_does_not_require_openspec(
    tmp_path: Path,
) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "commitment.toml").write_text(
        """schema_version = 1
id = "repository:test"
intent = "Govern the repository."
subjects = ["repository:test"]
""",
        encoding="utf-8",
    )
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
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "commitment.toml").write_text(
        """schema_version = 1
id = "repository:test"
intent = "Govern the repository."
subjects = ["repository:test"]
""",
        encoding="utf-8",
    )
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


def test_complete_change_does_not_make_active_contract_selection_ambiguous(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "commitment.toml").write_text(
        'schema_version = 1\nid = "repository:test"\nintent = "Govern."\n'
        'subjects = ["repository:test"]\n',
        encoding="utf-8",
    )
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

    assert load_openspec_commitment(tmp_path).id == "change:active"
    with pytest.raises(ValueError, match="commitment_complete:complete"):
        load_openspec_commitment(tmp_path, change_id="complete")


def test_commitment_missing_fails_closed(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "commitment.toml").write_text(
        """schema_version = 1
id = "repository:test"
intent = "Govern the repository."
subjects = ["repository:test"]
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="commitment_missing"):
        load_commitment(tmp_path, change_id="terminal-convergence")

    assert load_commitment(tmp_path).id == "repository:test"


def test_commitment_ignores_legacy_scope_companion(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "commitment.toml").write_text(
        """schema_version = 1
id = "repository:test"
intent = "Govern the repository."
subjects = ["repository:test"]
""",
        encoding="utf-8",
    )
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

    contract = load_commitment(
        tmp_path, carrier="openspec/changes/terminal-convergence/commitment.toml"
    )

    assert contract.scope == ("src/**",)


def test_repository_contract_owns_stable_subject_across_worktrees(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "commitment.toml").write_text(
        """schema_version = 1
id = "repository:test"
intent = "Govern the repository."
subjects = ["repository:test"]
""",
        encoding="utf-8",
    )

    contract = load_repository_contract(tmp_path)

    assert contract.id == "repository:test"
    assert contract.subjects == ("repository:test",)


def test_repository_contract_requires_id_to_equal_its_single_subject(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "commitment.toml").write_text(
        """schema_version = 1
id = "repository:first"
intent = "Govern the repository."
subjects = ["repository:second"]
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="repository_commitment_identity_mismatch"):
        load_repository_contract(tmp_path)


def _repository_contract(root: Path) -> None:
    (root / ".ethos").mkdir()
    (root / ".ethos" / "commitment.toml").write_text(
        'schema_version = 1\nid = "repository:test"\nintent = "Govern."\n'
        'subjects = ["repository:test"]\n',
        encoding="utf-8",
    )


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


def test_carrier_path_and_contract_identity_must_match(tmp_path: Path) -> None:
    _repository_contract(tmp_path)
    _enable_openspec_profile(tmp_path)
    _change_carrier(tmp_path, "terminal-convergence", "other-change")

    with pytest.raises(ValueError, match="commitment_identity_mismatch:terminal-convergence"):
        load_openspec_commitment(tmp_path, change_id="terminal-convergence")
