from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.adapters.repo.change_contract import load_change_contract
from ethos.adapters.repo.change_contract import load_proof_contract
from ethos.adapters.repo.change_contract import load_repository_contract

if TYPE_CHECKING:
    from pathlib import Path


def test_change_contract_loads_from_active_openspec_carrier(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "contract.toml").write_text(
        """schema_version = 1
id = "repository:test"
intent = "Govern the repository."
subjects = ["repository:test"]
""",
        encoding="utf-8",
    )
    carrier = tmp_path / "openspec" / "changes" / "terminal-convergence"
    carrier.mkdir(parents=True)
    (carrier / "contract.toml").write_text(
        """schema_version = 1
id = "change:terminal-convergence"
intent = "Converge the repository."
subjects = ["repository:self"]
scope = ["src/**"]
acceptance = ["terminal_state_proven"]
authority_refs = ["user_instruction"]
permissions = ["repository.read"]
dependencies = []
campaign = "change:terminal-convergence"
collaboration = "cooperative"
compatibility = "none"
publication = "dual"
""",
        encoding="utf-8",
    )

    contract = load_change_contract(tmp_path, change_id="terminal-convergence")

    assert contract.id == "change:terminal-convergence"
    assert contract.subjects == ("repository:test",)
    assert contract.scope == ("src/**",)


def test_single_active_change_contract_is_selected_without_branch_name_inference(
    tmp_path: Path,
) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "contract.toml").write_text(
        """schema_version = 1
id = "repository:test"
intent = "Govern the repository."
subjects = ["repository:test"]
""",
        encoding="utf-8",
    )
    carrier = tmp_path / "openspec" / "changes" / "semantic-kernel"
    carrier.mkdir(parents=True)
    (carrier / "contract.toml").write_text(
        """schema_version = 1
id = "change:semantic-kernel"
intent = "Converge the kernel."
subjects = ["repository:self"]
""",
        encoding="utf-8",
    )

    assert load_change_contract(tmp_path).id == "change:semantic-kernel"


def test_multiple_active_change_contracts_require_explicit_selection(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "contract.toml").write_text(
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
        (carrier / "contract.toml").write_text(
            f"""schema_version = 1
id = "change:{change_id}"
intent = "Change {change_id}."
subjects = ["repository:self"]
""",
            encoding="utf-8",
        )

    with pytest.raises(ValueError, match="change_contract_ambiguous"):
        load_change_contract(tmp_path)

    with pytest.raises(ValueError, match="change_contract_ambiguous"):
        load_proof_contract(tmp_path)


def test_complete_change_does_not_make_active_contract_selection_ambiguous(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "contract.toml").write_text(
        'schema_version = 1\nid = "repository:test"\nintent = "Govern."\n'
        'subjects = ["repository:test"]\n',
        encoding="utf-8",
    )
    for change_id, task in (("active", "- [ ] Continue\n"), ("complete", "- [x] Done\n")):
        carrier = tmp_path / "openspec" / "changes" / change_id
        carrier.mkdir(parents=True)
        (carrier / "contract.toml").write_text(
            f'schema_version = 1\nid = "change:{change_id}"\nintent = "{change_id}."\n'
            'subjects = ["repository:self"]\n',
            encoding="utf-8",
        )
        (carrier / "tasks.md").write_text(task, encoding="utf-8")

    assert load_change_contract(tmp_path).id == "change:active"
    with pytest.raises(ValueError, match="change_contract_complete:complete"):
        load_change_contract(tmp_path, change_id="complete")


def test_change_contract_missing_fails_closed(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "contract.toml").write_text(
        """schema_version = 1
id = "repository:test"
intent = "Govern the repository."
subjects = ["repository:test"]
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="change_contract_missing"):
        load_change_contract(tmp_path, change_id="terminal-convergence")


def test_change_contract_ignores_legacy_scope_companion(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "contract.toml").write_text(
        """schema_version = 1
id = "repository:test"
intent = "Govern the repository."
subjects = ["repository:test"]
""",
        encoding="utf-8",
    )
    carrier = tmp_path / "openspec" / "changes" / "terminal-convergence"
    carrier.mkdir(parents=True)
    (carrier / "contract.toml").write_text(
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

    contract = load_change_contract(tmp_path, change_id="terminal-convergence")

    assert contract.scope == ("src/**",)


def test_repository_contract_owns_stable_subject_across_worktrees(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "contract.toml").write_text(
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
    (tmp_path / ".ethos" / "contract.toml").write_text(
        """schema_version = 1
id = "repository:first"
intent = "Govern the repository."
subjects = ["repository:second"]
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="repository_contract_identity_mismatch"):
        load_repository_contract(tmp_path)
