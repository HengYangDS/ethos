"""Load repository and OpenSpec ChangeContract carriers from files or Git trees."""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

from ethos.adapters.repo.git import committed_file_text
from ethos.adapters.repo.git import git_stdout
from ethos.contracts.semantic import ChangeContract
from ethos.contracts.semantic import load_change_contract_file
from ethos.normalization.coercion import object_sequence
from ethos.repository.openspec.audit import tasks_complete
from ethos.repository.openspec.identifiers import archive_name_parts
from ethos.repository.openspec.identifiers import logical_change_identifier_issue

_ARCHIVE_CARRIER_PATH_PARTS = 2

if TYPE_CHECKING:
    from pathlib import Path


def _payload(
    path: Path,
    *,
    missing_gap: str,
    root: Path | None = None,
    tree_ref: str | None = None,
) -> dict[str, object]:
    try:
        text = (
            committed_file_text(root, tree_ref, path.relative_to(root).as_posix())
            if root is not None and tree_ref is not None
            else path.read_text(encoding="utf-8")
        )
        if not text:
            raise FileNotFoundError(path)
        return tomllib.loads(text)
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise ValueError(missing_gap) from exc


def _normalized(payload: dict[str, object]) -> dict[str, object]:
    tuple_fields = {
        "subjects",
        "scope",
        "invariants",
        "acceptance",
        "risks",
        "authority_refs",
        "permissions",
        "hypotheses",
        "dependencies",
    }
    return {
        key: tuple(value) if key in tuple_fields and isinstance(value, list) else value
        for key, value in payload.items()
    }


def load_repository_contract(repo: Path, *, tree_ref: str | None = None) -> ChangeContract:
    """Load the stable repository identity and default governance contract."""
    path = repo / ".ethos" / "contract.toml"
    if tree_ref is None:
        try:
            contract = load_change_contract_file(path)
        except (OSError, UnicodeError, tomllib.TOMLDecodeError, ValueError) as exc:
            message = "repository_contract_missing:.ethos/contract.toml"
            raise ValueError(message) from exc
    else:
        contract = ChangeContract.model_validate(
            _normalized(
                _payload(
                    path,
                    missing_gap="repository_contract_missing:.ethos/contract.toml",
                    root=repo,
                    tree_ref=tree_ref,
                )
            )
        )
    if contract.subjects != (contract.id,):
        message = "repository_contract_identity_mismatch"
        raise ValueError(message)
    return contract


def load_change_contract(
    repo: Path,
    *,
    change_id: str | None = None,
    tree_ref: str | None = None,
    expected_digest: str | None = None,
    require_active: bool = True,
) -> ChangeContract:
    """Resolve one exact active or archived ChangeContract carrier."""
    if require_active and change_id:
        if _archive_directory_exists(repo, change_id, tree_ref=tree_ref):
            message = f"openspec_active_change_identifier_is_archive_directory:{change_id}"
            raise ValueError(message)
        if logical_change_identifier_issue(change_id):
            message = f"openspec_active_change_identifier_invalid:{change_id}"
            raise ValueError(message)
    repository_contract = load_repository_contract(repo, tree_ref=tree_ref)
    carriers, invalid_archives = _carrier_inventory(repo, tree_ref=tree_ref)
    if invalid_archives:
        invalid = invalid_archives[0]
        message = f"change_contract_archive_invalid:{invalid}"
        raise ValueError(message)
    selected = _select_carriers(
        repo,
        carriers,
        change_id=change_id,
        tree_ref=tree_ref,
        require_active=require_active,
        expected_digest=expected_digest,
    )

    loaded = [
        (
            carrier,
            _load_carrier(
                repo,
                carrier[1],
                repository_id=repository_contract.id,
                tree_ref=tree_ref,
                logical_id=carrier[0],
            ),
        )
        for carrier in selected
    ]
    if expected_digest is not None:
        matches = [
            (carrier, contract)
            for carrier, contract in loaded
            if contract.digest() == expected_digest
        ]
        if len(matches) != 1:
            if len(matches) > 1:
                message = "change_contract_ambiguous"
                raise ValueError(message)
            message = "change_contract_digest_mismatch"
            raise ValueError(message)
        carrier, contract = matches[0]
        if contract.id != f"change:{carrier[0]}":
            message = f"change_contract_identity_mismatch:{carrier[0]}"
            raise ValueError(message)
        return contract
    contract = loaded[0][1]
    logical_id = selected[0][0]
    if contract.id != f"change:{logical_id}":
        message = f"change_contract_identity_mismatch:{logical_id}"
        raise ValueError(message)
    return contract


def load_lease_bound_change_contract(
    repo: Path,
    *,
    expected_head: str,
    base_change_contract_digest: str,
    change_id: str | None = None,
) -> ChangeContract:
    """Resolve one base contract and require exact Lease/current-tree equality."""
    if not base_change_contract_digest:
        message = "lease_base_change_contract_digest_missing"
        raise ValueError(message)
    try:
        committed = load_change_contract(
            repo,
            change_id=change_id,
            tree_ref=expected_head,
            expected_digest=base_change_contract_digest,
            require_active=False,
        )
        current = load_change_contract(
            repo,
            change_id=change_id,
            expected_digest=base_change_contract_digest,
            require_active=False,
        )
    except ValueError as exc:
        if str(exc) != "change_contract_digest_mismatch":
            raise
        message = "lease_base_change_contract_digest_mismatch"
        raise ValueError(message) from exc
    if (
        committed.digest() != base_change_contract_digest
        or current.digest() != base_change_contract_digest
    ):
        message = "lease_base_change_contract_digest_mismatch"
        raise ValueError(message)
    return committed


def _select_carriers(
    repo: Path,
    carriers: list[tuple[str, str, str]],
    *,
    change_id: str | None,
    tree_ref: str | None,
    require_active: bool,
    expected_digest: str | None,
) -> list[tuple[str, str, str]]:
    """Select one carrier without allowing duplicate logical identities."""
    duplicate_ids = sorted(
        logical_id
        for logical_id in {carrier[0] for carrier in carriers}
        if sum(carrier[0] == logical_id for carrier in carriers) > 1
    )
    if duplicate_ids:
        message = "change_contract_ambiguous"
        raise ValueError(message)

    active = [carrier for carrier in carriers if carrier[2] == "active"]
    archives = [carrier for carrier in carriers if carrier[2] == "archive"]
    complete_active = {
        logical_id
        for logical_id, _path, _kind in active
        if _change_complete(repo, logical_id, tree_ref=tree_ref)
    }
    selected = [
        carrier
        for carrier in (active if require_active else (*active, *archives))
        if (not require_active or carrier[0] not in complete_active)
        and (change_id is None or carrier[0] == change_id)
    ]
    if change_id is not None and not selected:
        if require_active and change_id in complete_active:
            message = f"change_contract_complete:{change_id}"
            raise ValueError(message)
        if require_active and any(carrier[0] == change_id for carrier in archives):
            message = f"change_contract_archived:{change_id}"
            raise ValueError(message)
        message = f"change_contract_missing:{change_id}"
        raise ValueError(message)
    if not selected:
        message = (
            "change_contract_digest_mismatch"
            if expected_digest is not None and carriers
            else "change_contract_missing"
        )
        raise ValueError(message)
    if expected_digest is None and len(selected) != 1:
        message = "change_contract_ambiguous"
        raise ValueError(message)
    return selected


def _carrier_inventory(
    repo: Path, *, tree_ref: str | None
) -> tuple[list[tuple[str, str, str]], list[str]]:
    """Inventory only canonical active and archived contract carriers."""
    paths = (
        sorted(
            path.relative_to(repo).as_posix()
            for path in (repo / "openspec" / "changes").rglob("contract.toml")
        )
        if tree_ref is None
        else git_stdout(
            repo, "ls-tree", "-r", "--name-only", tree_ref, "--", "openspec/changes"
        ).splitlines()
    )
    carriers: list[tuple[str, str, str]] = []
    invalid_archives: list[str] = []
    prefix = "openspec/changes/"
    for path in paths:
        if not path.startswith(prefix) or not path.endswith("/contract.toml"):
            continue
        relative = path.removeprefix(prefix).removesuffix("/contract.toml")
        parts = relative.split("/")
        if len(parts) == 1 and parts[0]:
            if parts[0] == "archive" or logical_change_identifier_issue(parts[0]):
                invalid_archives.append(parts[0])
            else:
                carriers.append((parts[0], path, "active"))
        elif len(parts) == _ARCHIVE_CARRIER_PATH_PARTS and parts[0] == "archive":
            archive_parts = archive_name_parts(parts[1])
            if archive_parts is None:
                invalid_archives.append(parts[1])
            else:
                carriers.append((archive_parts[1], path, "archive"))
        elif parts and parts[0] == "archive":
            invalid_archives.append(relative)
    return carriers, sorted(invalid_archives)


def _archive_directory_exists(repo: Path, identifier: str, *, tree_ref: str | None) -> bool:
    relative = f"openspec/changes/archive/{identifier}"
    if tree_ref is None:
        return (repo / relative).is_dir()
    return bool(git_stdout(repo, "ls-tree", "-d", "--name-only", tree_ref, "--", relative))


def _load_carrier(
    repo: Path,
    relative_path: str,
    *,
    repository_id: str,
    tree_ref: str | None,
    logical_id: str,
) -> ChangeContract:
    message = f"change_contract_invalid:{logical_id}"
    try:
        if tree_ref is None:
            return load_change_contract_file(repo / relative_path, repository_id=repository_id)
        normalized = _normalized(
            _payload(
                repo / relative_path,
                missing_gap=message,
                root=repo,
                tree_ref=tree_ref,
            )
        )
        normalized["subjects"] = tuple(
            repository_id if subject == "repository:self" else str(subject)
            for subject in object_sequence(normalized.get("subjects"))
        )
        return ChangeContract.model_validate(normalized)
    except (OSError, UnicodeError, tomllib.TOMLDecodeError, TypeError, ValueError) as exc:
        raise ValueError(message) from exc


def _change_complete(repo: Path, change_id: str, *, tree_ref: str | None) -> bool:
    relative = f"openspec/changes/{change_id}/tasks.md"
    try:
        text = (
            committed_file_text(repo, tree_ref, relative)
            if tree_ref is not None
            else (repo / relative).read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError):
        return False
    return tasks_complete(text)
